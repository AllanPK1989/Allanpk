import 'dart:async';

import 'package:firebase_core/firebase_core.dart' show FirebaseException;
import 'package:flutter/foundation.dart' show debugPrint;

import '../../models/models.dart';

// When an owner removes a member, the security rules only let the owner drop
// the household from the member's `householdIds`; the member's
// `activeHouseholdId` keeps pointing at a household they can no longer read.
// The member's own client notices (its household listeners fail with
// permission-denied, or a snapshot no longer lists them), confirms it with
// the server and then moves itself to another household or to onboarding.

// ------------------------------------------------------------ decisions

/// Whether [error] is Firestore refusing access under the security rules.
bool isPermissionDenied(Object? error) =>
    error is FirebaseException && error.code == 'permission-denied';

/// Whether a snapshot of household [hid] shows that [uid] is no longer one of
/// its members.
bool householdDropsMember({
  required String uid,
  required String hid,
  required Household household,
}) {
  return household.id == hid && !household.memberIds.contains(uid);
}

/// What the server says about the user's place in a household.
enum MembershipVerdict {
  /// Still a member; whatever failed was transient.
  member,

  /// The server's profile has a different active household, or the user's
  /// own writes to it (creating, joining, switching) have not reached the
  /// server yet. Nothing to do: local state catches up on its own.
  unsettled,

  /// No longer a member: removed by the owner, or the household is gone.
  removed,
}

/// Judges a suspected removal from [hid] using state read from the server:
/// the user's profile ([serverActiveHouseholdId]) and the household itself
/// ([serverHousehold], null when that read was denied).
///
/// The profile must be read before the household. Creating or joining a
/// household writes the active household and the membership in one batch,
/// so once the server profile points at [hid], a later household read
/// reflects that membership too. Server reads still include the client's
/// own pending writes, hence [profileHasPendingWrites]: until that batch is
/// committed the profile proves nothing.
MembershipVerdict membershipVerdict({
  required String uid,
  required String hid,
  required String? serverActiveHouseholdId,
  required bool profileHasPendingWrites,
  required Household? serverHousehold,
}) {
  if (profileHasPendingWrites || serverActiveHouseholdId != hid) {
    return MembershipVerdict.unsettled;
  }
  if (serverHousehold != null && serverHousehold.memberIds.contains(uid)) {
    return MembershipVerdict.member;
  }
  return MembershipVerdict.removed;
}

/// Where a removed user goes next, and what to tell them.
class RemovalPlan {
  const RemovalPlan({required this.next, required this.message});

  /// Household to make active, or null to clear the active household, which
  /// makes the router send the user to onboarding.
  final Household? next;

  final String message;
}

/// Picks what happens after [uid] lost access to [removedId]: switch to the
/// first other household in [households] that still lists them, otherwise
/// clear the active household. [removedName] is the last known name of the
/// household they were removed from.
RemovalPlan planAfterRemoval({
  required String uid,
  required String removedId,
  String? removedName,
  required List<Household> households,
}) {
  final next = households
      .where((h) => h.id != removedId && h.memberIds.contains(uid))
      .firstOrNull;
  final name = removedName?.trim() ?? '';
  final removed = name.isEmpty
      ? 'You no longer have access to that household'
      : 'You were removed from $name';
  return RemovalPlan(
    next: next,
    message: next == null ? removed : '$removed. Switched to ${next.name}.',
  );
}

// ---------------------------------------------------------------- guard

/// Membership facts read from the server (see [membershipVerdict]).
typedef ServerMembership = ({
  String? activeHouseholdId,
  bool profileHasPendingWrites,
  Household? household,
});

/// Shown to the user after they were moved out of a household.
class RemovalNotice {
  RemovalNotice(this.message, {this.switchedTo});

  final String message;

  /// The household they now see, or null when they were sent to onboarding.
  final Household? switchedTo;
}

/// Confirms suspected removals from the active household and moves the user
/// on. One instance per signed-in user.
class MembershipGuard {
  MembershipGuard({
    required this.uid,
    required this._fetchMembership,
    required this._setActiveHousehold,
    required this._activeHouseholdId,
    required this._households,
  });

  final String? uid;
  final Future<ServerMembership> Function(String uid, String hid) _fetchMembership;
  final Future<void> Function(String uid, String? hid) _setActiveHousehold;
  final String? Function() _activeHouseholdId;
  final Future<List<Household>> Function() _households;

  final _names = <String, String>{};
  final _checks = <String, Future<bool>>{};
  final _notices = StreamController<RemovalNotice>.broadcast();
  bool _disposed = false;

  /// One event each time the user is moved out of a household.
  Stream<RemovalNotice> get notices => _notices.stream;

  /// Feed snapshots of household [hid] through here: remembers its name for
  /// the notice, and starts a check when it no longer lists the user.
  void observeHousehold(String hid, Household? household) {
    if (household == null) return;
    _names[household.id] = household.name;
    final uid = this.uid;
    if (uid != null && householdDropsMember(uid: uid, hid: hid, household: household)) {
      unawaited(lostAccessTo(hid));
    }
  }

  void observeHouseholds(List<Household> households) {
    for (final h in households) {
      _names[h.id] = h.name;
    }
  }

  /// Call whenever the active household id changes, so a household the user
  /// rejoins later is checked afresh.
  void activeHouseholdChanged() => _checks.clear();

  /// Resolves to true when the user has lost access to [hid], after moving
  /// them to another household (or clearing the active one) if [hid] is still
  /// active. Resolves to false when they are still a member or the server
  /// could not be asked; callers then surface their error as usual.
  ///
  /// Concurrent calls for one household share a single check.
  Future<bool> lostAccessTo(String hid) {
    if (_disposed) return Future.value(true);
    final existing = _checks[hid];
    if (existing != null) return existing;
    late final Future<bool> check;
    check = _confirmAndMove(hid).catchError((Object _) => false).then((lost) {
      // Only a confirmed removal is final; anything else may be retried.
      if (!lost && identical(_checks[hid], check)) _checks.remove(hid);
      return lost;
    });
    return _checks[hid] = check;
  }

  Future<bool> _confirmAndMove(String hid) async {
    final uid = this.uid;
    if (uid == null) return false;
    final ServerMembership server;
    try {
      server = await _fetchMembership(uid, hid);
    } catch (_) {
      // Offline or similar: nothing confirmed.
      return false;
    }
    final household = server.household;
    if (household != null) _names[hid] = household.name;
    final verdict = membershipVerdict(
      uid: uid,
      hid: hid,
      serverActiveHouseholdId: server.activeHouseholdId,
      profileHasPendingWrites: server.profileHasPendingWrites,
      serverHousehold: household,
    );
    if (verdict != MembershipVerdict.removed) return false;
    // Access is gone. Move the user only if they are still on [hid] here:
    // leaving on purpose switches the active household in the same write.
    if (_disposed || _activeHouseholdId() != hid) return true;

    List<Household> households;
    try {
      households = await _households().timeout(const Duration(seconds: 10));
    } catch (_) {
      households = const [];
    }
    if (_disposed || _activeHouseholdId() != hid) return true;

    final plan = planAfterRemoval(
      uid: uid,
      removedId: hid,
      removedName: _names[hid],
      households: households,
    );
    // Not awaited: the local snapshot updates at once, while the server
    // acknowledgement can take a while (or wait until the user is online).
    unawaited(
      _setActiveHousehold(uid, plan.next?.id).catchError((Object e) {
        debugPrint('Could not leave household $hid after removal: $e');
        _checks.remove(hid);
      }),
    );
    _notices.add(RemovalNotice(plan.message, switchedTo: plan.next));
    return true;
  }

  void dispose() {
    _disposed = true;
    _notices.close();
  }
}

/// Passes [source], a stream scoped to household [hid], straight through,
/// except for permission-denied errors: Firestore raises those the moment an
/// owner removes the user. Such an error is checked with [guard] first. If
/// the user really lost access, the guard moves them on and this stream just
/// ends, so providers keep their last value until they rebuild for the next
/// household instead of showing a raw permission error. Otherwise the error
/// is passed on and Riverpod retries the provider as usual.
Stream<T> whileMember<T>(MembershipGuard guard, String hid, Stream<T> source) async* {
  try {
    await for (final event in source) {
      yield event;
    }
  } catch (error) {
    if (!isPermissionDenied(error) || !await guard.lostAccessTo(hid)) rethrow;
  }
}
