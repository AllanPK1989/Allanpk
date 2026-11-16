import 'dart:math';

import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:firebase_auth/firebase_auth.dart' show FirebaseAuth, User;

import '../core/constants/currencies.dart';
import '../core/constants/default_categories.dart';
import '../models/models.dart';
import 'firestore_refs.dart';

/// Users, households and invitations.
class UserRepository {
  UserRepository(this._refs, this._auth);

  final FirestoreRefs _refs;
  final FirebaseAuth _auth;

  Stream<UserProfile?> watchProfile(String uid) {
    return _refs.user(uid).snapshots().map((snap) {
      final data = snap.data();
      if (data == null) return null;
      return UserProfile.fromMap(snap.id, data);
    });
  }

  /// Creates the profile document on first sign-in. Returns the profile.
  Future<UserProfile> ensureProfile(User signedIn) async {
    // User objects from the auth stream snapshot their fields when created
    // (notably on the web), so a display name set right after sign-up would
    // be missed. Reload and re-read the current user to get fresh values.
    var user = signedIn;
    try {
      await user.reload();
      final fresh = _auth.currentUser;
      if (fresh != null && fresh.uid == user.uid) user = fresh;
    } catch (_) {}
    final ref = _refs.user(user.uid);
    final snap = await ref.get();
    final fallbackName = user.email?.split('@').first ?? 'You';
    final authName = (user.displayName ?? '').trim();
    if (snap.exists) {
      var profile = UserProfile.fromMap(snap.id, snap.data()!);
      // Keep name/photo in sync with the auth provider: on email sign-up the
      // profile can be created a moment before the display name is set.
      final updates = <String, dynamic>{};
      final usingFallback = profile.displayName.isEmpty || profile.displayName == fallbackName;
      if (usingFallback && authName.isNotEmpty && authName != profile.displayName) {
        updates['displayName'] = authName;
        profile = profile.copyWith(displayName: authName);
      }
      if ((profile.photoUrl ?? '').isEmpty && (user.photoURL ?? '').isNotEmpty) {
        updates['photoUrl'] = user.photoURL;
        profile = profile.copyWith(photoUrl: user.photoURL);
      }
      if (updates.isNotEmpty) await ref.set(updates, SetOptions(merge: true));
      return profile;
    }
    final profile = UserProfile(
      uid: user.uid,
      email: user.email ?? '',
      displayName: authName.isNotEmpty ? authName : fallbackName,
      photoUrl: user.photoURL,
      createdAt: DateTime.now(),
    );
    await ref.set(profile.toMap());
    return profile;
  }

  Future<void> updateProfile(String uid, {String? displayName, String? photoUrl}) async {
    await _refs.user(uid).set({
      'displayName': ?displayName,
      'photoUrl': ?photoUrl,
    }, SetOptions(merge: true));
  }

  Stream<Household?> watchHousehold(String hid) {
    return _refs.household(hid).snapshots().map((snap) {
      final data = snap.data();
      if (data == null) return null;
      return Household.fromMap(snap.id, data);
    });
  }

  Stream<List<Household>> watchHouseholdsFor(String uid) {
    return _refs.households
        .where('memberIds', arrayContains: uid)
        .snapshots()
        .map((s) => s.docs.map((d) => Household.fromMap(d.id, d.data())).toList());
  }

  /// Creates a household with default categories and a cash account, then
  /// makes it the user's active household.
  Future<Household> createHousehold({
    required UserProfile profile,
    required String name,
    required String currency,
    int memberColor = 0xFF4F46E5,
  }) async {
    final hid = _refs.households.doc().id;
    final code = await _uniqueInviteCode();
    final now = DateTime.now();
    final member = HouseholdMember(
      uid: profile.uid,
      name: profile.displayName,
      role: MemberRole.owner,
      joinedAt: now,
      photoUrl: profile.photoUrl,
      color: memberColor,
    );
    final household = Household(
      id: hid,
      name: name.trim().isEmpty ? 'My Household' : name.trim(),
      ownerId: profile.uid,
      baseCurrency: currency.isEmpty ? kDefaultCurrency : currency,
      memberIds: [profile.uid],
      members: {profile.uid: member},
      inviteCode: code,
      createdAt: now,
    );

    final batch = _refs.db.batch();
    batch.set(_refs.household(hid), household.toMap());
    batch.set(_refs.invites.doc(code), {
      'householdId': hid,
      'createdBy': profile.uid,
      'createdAt': now,
    });

    var order = 0;
    for (final spec in kDefaultCategories) {
      final ref = _refs.categories(hid).doc();
      batch.set(
        ref,
        Category(
          id: ref.id,
          name: spec.name,
          kind: spec.kind,
          iconKey: spec.iconKey,
          color: spec.color,
          sortOrder: order++,
          isDefault: true,
        ).toMap(),
      );
    }

    final cashRef = _refs.accounts(hid).doc();
    batch.set(
      cashRef,
      Account(
        id: cashRef.id,
        name: 'Cash',
        type: AccountType.cash,
        currency: household.baseCurrency,
        color: 0xFF43A047,
        createdBy: profile.uid,
        createdAt: now,
      ).toMap(),
    );
    final bankRef = _refs.accounts(hid).doc();
    batch.set(
      bankRef,
      Account(
        id: bankRef.id,
        name: 'Bank account',
        type: AccountType.bank,
        currency: household.baseCurrency,
        color: 0xFF1E88E5,
        createdBy: profile.uid,
        createdAt: now,
        sortOrder: 1,
      ).toMap(),
    );

    batch.set(
      _refs.user(profile.uid),
      {
        'activeHouseholdId': hid,
        'householdIds': FieldValue.arrayUnion([hid]),
        'onboardingComplete': true,
      },
      SetOptions(merge: true),
    );
    await batch.commit();
    return household;
  }

  /// Joins the household behind [code]. Throws [StateError] when invalid.
  Future<Household> joinHousehold({
    required UserProfile profile,
    required String code,
    int memberColor = 0xFF0284C7,
  }) async {
    final normalized = code.trim().toUpperCase().replaceAll('-', '');
    final invite = await _refs.invites.doc(normalized).get();
    final hid = invite.data()?['householdId'] as String?;
    if (hid == null) {
      throw StateError('That invite code is not valid. Ask your family for a new one.');
    }
    final now = DateTime.now();
    final member = HouseholdMember(
      uid: profile.uid,
      name: profile.displayName,
      role: MemberRole.adult,
      joinedAt: now,
      photoUrl: profile.photoUrl,
      color: memberColor,
      inviteCode: normalized,
    );
    final batch = _refs.db.batch();
    batch.update(_refs.household(hid), {
      'memberIds': FieldValue.arrayUnion([profile.uid]),
      'members.${profile.uid}': member.toMap(),
    });
    batch.set(
      _refs.user(profile.uid),
      {
        'activeHouseholdId': hid,
        'householdIds': FieldValue.arrayUnion([hid]),
        'onboardingComplete': true,
      },
      SetOptions(merge: true),
    );
    final act = _refs.activity(hid).doc();
    batch.set(
      act,
      ActivityEntry(
        id: act.id,
        actorId: profile.uid,
        actorName: profile.displayName,
        action: ActivityAction.joined,
        entityType: 'household',
        entityId: hid,
        summary: '${profile.displayName} joined the household',
        at: now,
      ).toMap(),
    );
    await batch.commit();
    final snap = await _refs.household(hid).get();
    return Household.fromMap(snap.id, snap.data()!);
  }

  /// Makes [hid] the active household; null clears it, which sends the user
  /// to onboarding.
  Future<void> switchHousehold(String uid, String? hid) {
    return _refs.user(uid).set({'activeHouseholdId': hid}, SetOptions(merge: true));
  }

  /// Reads from the server, never the cache: the active household on [uid]'s
  /// profile (and whether this client still has unsent writes to it), then
  /// household [hid] itself (null when the rules deny the read, i.e. [uid] is
  /// not a member, or it no longer exists). The order matters, see
  /// `membershipVerdict`.
  Future<({String? activeHouseholdId, bool profileHasPendingWrites, Household? household})>
      fetchMembership(
    String uid,
    String hid,
  ) async {
    const server = GetOptions(source: Source.server);
    final user = await _refs.user(uid).get(server);
    Household? household;
    try {
      final snap = await _refs.household(hid).get(server);
      final data = snap.data();
      if (data != null) household = Household.fromMap(snap.id, data);
    } on FirebaseException catch (e) {
      if (e.code != 'permission-denied') rethrow;
    }
    return (
      activeHouseholdId: user.data()?['activeHouseholdId'] as String?,
      profileHasPendingWrites: user.metadata.hasPendingWrites,
      household: household,
    );
  }

  Future<void> updateHousehold(
    String hid, {
    String? name,
    String? baseCurrency,
    int? monthStartDay,
  }) {
    return _refs.household(hid).update({
      if (name != null) 'name': name.trim(),
      'baseCurrency': ?baseCurrency,
      'monthStartDay': ?monthStartDay,
    });
  }

  Future<void> updateMember(String hid, HouseholdMember member) {
    return _refs.household(hid).update({'members.${member.uid}': member.toMap()});
  }

  /// Removes [memberId] from [household]. When an owner removes someone else,
  /// the rules only allow dropping the household from that member's
  /// `householdIds`; their own app then notices and moves them on (see
  /// `MembershipGuard`).
  Future<void> removeMember({
    required Household household,
    required String memberId,
    required UserProfile actor,
  }) {
    return _removalBatch(household: household, memberId: memberId, actor: actor).commit();
  }

  /// [profile] leaves [household] and, in the same write, makes
  /// [nextActiveId] their active household (null sends them to onboarding).
  /// One write means the app never sees an active household that no longer
  /// lists them, which it would treat as a removal.
  Future<void> leaveHousehold({
    required Household household,
    required UserProfile profile,
    required String? nextActiveId,
  }) {
    return _removalBatch(
      household: household,
      memberId: profile.uid,
      actor: profile,
      memberProfile: {'activeHouseholdId': nextActiveId},
    ).commit();
  }

  WriteBatch _removalBatch({
    required Household household,
    required String memberId,
    required UserProfile actor,
    Map<String, Object?> memberProfile = const {},
  }) {
    final batch = _refs.db.batch();
    batch.update(_refs.household(household.id), {
      'memberIds': FieldValue.arrayRemove([memberId]),
      'members.$memberId': FieldValue.delete(),
    });
    batch.set(
      _refs.user(memberId),
      {
        'householdIds': FieldValue.arrayRemove([household.id]),
        ...memberProfile,
      },
      SetOptions(merge: true),
    );
    final removedName = household.members[memberId]?.name ?? 'A member';
    final act = _refs.activity(household.id).doc();
    batch.set(
      act,
      ActivityEntry(
        id: act.id,
        actorId: actor.uid,
        actorName: actor.displayName,
        action: ActivityAction.left,
        entityType: 'household',
        entityId: household.id,
        summary: memberId == actor.uid
            ? '${actor.displayName} left the household'
            : '$removedName was removed by ${actor.displayName}',
        at: DateTime.now(),
      ).toMap(),
    );
    return batch;
  }

  Future<String> regenerateInviteCode(Household household) async {
    final code = await _uniqueInviteCode();
    final batch = _refs.db.batch();
    batch.delete(_refs.invites.doc(household.inviteCode));
    batch.set(_refs.invites.doc(code), {
      'householdId': household.id,
      'createdBy': household.ownerId,
      'createdAt': DateTime.now(),
    });
    batch.update(_refs.household(household.id), {'inviteCode': code});
    await batch.commit();
    return code;
  }

  Future<String> _uniqueInviteCode() async {
    const alphabet = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789';
    final rnd = Random.secure();
    for (var attempt = 0; attempt < 5; attempt++) {
      final code = List.generate(8, (_) => alphabet[rnd.nextInt(alphabet.length)]).join();
      final existing = await _refs.invites.doc(code).get();
      if (!existing.exists) return code;
    }
    throw StateError('Could not generate an invite code, please retry.');
  }
}
