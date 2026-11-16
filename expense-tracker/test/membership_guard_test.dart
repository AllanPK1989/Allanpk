import 'dart:async';

import 'package:expense_budget_manager/data/ledger_repository.dart';
import 'package:expense_budget_manager/features/auth/auth_providers.dart';
import 'package:expense_budget_manager/features/household/household_providers.dart';
import 'package:expense_budget_manager/features/household/membership_guard.dart';
import 'package:expense_budget_manager/models/models.dart';
import 'package:firebase_core/firebase_core.dart' show FirebaseException;
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'helpers.dart';

Household home(String id, String name, List<String> memberIds) => Household(
      id: id,
      name: name,
      ownerId: memberIds.first,
      baseCurrency: 'INR',
      memberIds: memberIds,
      members: {
        for (final m in memberIds) m: HouseholdMember(uid: m, name: m, role: MemberRole.adult, joinedAt: now),
      },
      inviteCode: 'ABCD2345',
      createdAt: now,
    );

final denied = FirebaseException(plugin: 'cloud_firestore', code: 'permission-denied');

/// A guard for user `me` whose server calls are scripted by the test.
class GuardHarness {
  GuardHarness({
    this.active = 'family',
    ServerMembership? server,
    List<Household>? households,
  })  : server = server ?? (activeHouseholdId: 'family', profileHasPendingWrites: false, household: null),
        households = households ?? [home('personal', 'Personal', ['me'])];

  String? active;
  ServerMembership server;
  Object? fetchError;
  List<Household> households;
  final fetches = <String>[];
  final writes = <String?>[];
  final notices = <RemovalNotice>[];

  late final guard = MembershipGuard(
    uid: 'me',
    fetchMembership: (uid, hid) async {
      fetches.add(hid);
      await Future<void>.delayed(Duration.zero);
      if (fetchError != null) throw fetchError!;
      return server;
    },
    setActiveHousehold: (uid, hid) async {
      writes.add(hid);
      active = hid;
    },
    activeHouseholdId: () => active,
    households: () async => households,
  )..notices.listen(notices.add);
}

class _FakeLedger extends Fake implements LedgerRepository {
  _FakeLedger(this.transactions);

  final Stream<List<Transaction>> transactions;

  @override
  String get householdId => 'family';

  @override
  Stream<List<Transaction>> watchAllTransactions(String uid) => transactions;
}

void main() {
  group('decision logic', () {
    test('isPermissionDenied only matches the Firestore rules error', () {
      expect(isPermissionDenied(denied), isTrue);
      expect(isPermissionDenied(FirebaseException(plugin: 'cloud_firestore', code: 'unavailable')), isFalse);
      expect(isPermissionDenied(StateError('nope')), isFalse);
      expect(isPermissionDenied(null), isFalse);
    });

    test('householdDropsMember spots a snapshot without the user', () {
      final family = home('family', 'Family', ['owner', 'me']);
      expect(householdDropsMember(uid: 'me', hid: 'family', household: family), isFalse);
      final after = family.copyWith(memberIds: ['owner']);
      expect(householdDropsMember(uid: 'me', hid: 'family', household: after), isTrue);
      // A stale value from the previously active household is not evidence.
      expect(householdDropsMember(uid: 'me', hid: 'other', household: after), isFalse);
    });

    test('membershipVerdict needs the server to agree before calling it a removal', () {
      final listed = home('family', 'Family', ['owner', 'me']);
      final unlisted = home('family', 'Family', ['owner']);
      MembershipVerdict verdict(String? active, Household? h, {bool pending = false}) => membershipVerdict(
            uid: 'me',
            hid: 'family',
            serverActiveHouseholdId: active,
            profileHasPendingWrites: pending,
            serverHousehold: h,
          );

      // Our own join is still in flight: the server profile points elsewhere.
      expect(verdict('personal', null), MembershipVerdict.unsettled);
      expect(verdict(null, null), MembershipVerdict.unsettled);
      // Creating or joining: server reads include our unsent batch, so the
      // profile already points here while the household read is still denied.
      expect(verdict('family', null, pending: true), MembershipVerdict.unsettled);
      expect(verdict('family', listed), MembershipVerdict.member);
      // Read denied (removed, or household deleted) or no longer listed.
      expect(verdict('family', null), MembershipVerdict.removed);
      expect(verdict('family', unlisted), MembershipVerdict.removed);
    });

    test('planAfterRemoval switches to another household the user still belongs to', () {
      final plan = planAfterRemoval(
        uid: 'me',
        removedId: 'family',
        removedName: 'Sharma Family',
        households: [
          // The list can be stale and still hold the household we just lost.
          home('family', 'Sharma Family', ['owner', 'me']),
          home('club', 'Book Club', ['someone']),
          home('personal', 'Personal', ['me']),
        ],
      );
      expect(plan.next?.id, 'personal');
      expect(plan.message, 'You were removed from Sharma Family. Switched to Personal.');
    });

    test('planAfterRemoval clears the active household when nothing is left', () {
      final plan = planAfterRemoval(
        uid: 'me',
        removedId: 'family',
        removedName: 'Sharma Family',
        households: [home('family', 'Sharma Family', ['owner', 'me'])],
      );
      expect(plan.next, isNull);
      expect(plan.message, 'You were removed from Sharma Family');

      final unnamed = planAfterRemoval(uid: 'me', removedId: 'family', households: const []);
      expect(unnamed.next, isNull);
      expect(unnamed.message, 'You no longer have access to that household');
    });
  });

  group('MembershipGuard', () {
    test('a confirmed removal switches household once, even when many streams ask', () async {
      final h = GuardHarness();
      h.guard.observeHousehold('family', home('family', 'Sharma Family', ['owner', 'me']));

      final results = await Future.wait([for (var i = 0; i < 5; i++) h.guard.lostAccessTo('family')]);

      await pumpEventQueue(); // notices arrive asynchronously
      expect(results, everyElement(isTrue));
      expect(h.fetches, ['family']);
      expect(h.writes, ['personal']);
      expect(h.notices.single.message, 'You were removed from Sharma Family. Switched to Personal.');
      expect(h.notices.single.switchedTo?.id, 'personal');
      // Later errors from the same household are answered without asking again.
      expect(await h.guard.lostAccessTo('family'), isTrue);
      expect(h.fetches, ['family']);
    });

    test('with no other household the active household is cleared', () async {
      final h = GuardHarness(households: []);
      expect(await h.guard.lostAccessTo('family'), isTrue);
      await pumpEventQueue();
      expect(h.writes, [null]);
      expect(h.notices.single.switchedTo, isNull);
    });

    test('does nothing while our own household write is still being sent', () async {
      final h = GuardHarness(server: (activeHouseholdId: 'family', profileHasPendingWrites: true, household: null));
      expect(await h.guard.lostAccessTo('family'), isFalse);
      expect(h.writes, isEmpty);
    });

    test('does nothing while the server has not caught up with a join', () async {
      final h = GuardHarness(server: (activeHouseholdId: 'personal', profileHasPendingWrites: false, household: null));
      expect(await h.guard.lostAccessTo('family'), isFalse);
      expect(h.writes, isEmpty);
      expect(h.notices, isEmpty);
    });

    test('does nothing when the server says the user is still a member', () async {
      final h = GuardHarness(server: (activeHouseholdId: 'family', profileHasPendingWrites: false, household: home('family', 'F', ['owner', 'me'])));
      expect(await h.guard.lostAccessTo('family'), isFalse);
      expect(h.writes, isEmpty);
    });

    test('an unreachable server confirms nothing, and the next error asks again', () async {
      final h = GuardHarness()..fetchError = FirebaseException(plugin: 'cloud_firestore', code: 'unavailable');
      expect(await h.guard.lostAccessTo('family'), isFalse);
      h.fetchError = null;
      expect(await h.guard.lostAccessTo('family'), isTrue);
      expect(h.fetches, ['family', 'family']);
      expect(h.writes, ['personal']);
    });

    test('leaves the user alone once they moved on themselves', () async {
      final h = GuardHarness();
      final check = h.guard.lostAccessTo('family');
      h.active = 'personal'; // e.g. they left on purpose, switching in the same write
      expect(await check, isTrue);
      expect(h.writes, isEmpty);
      expect(h.notices, isEmpty);
    });

    test('a snapshot that no longer lists the user starts a check', () async {
      final h = GuardHarness();
      h.guard.observeHousehold('family', home('family', 'Sharma Family', ['owner']));
      await pumpEventQueue();
      expect(h.fetches, ['family']);
      expect(h.notices.single.message, startsWith('You were removed from Sharma Family'));
    });

    test('a household rejoined later is checked afresh', () async {
      final h = GuardHarness();
      expect(await h.guard.lostAccessTo('family'), isTrue);
      h.guard.activeHouseholdChanged();
      h.server = (activeHouseholdId: 'family', profileHasPendingWrites: false, household: home('family', 'F', ['owner', 'me']));
      h.active = 'family';
      expect(await h.guard.lostAccessTo('family'), isFalse);
    });
  });

  group('whileMember', () {
    test('ends quietly when the user lost access', () async {
      final h = GuardHarness();
      final source = Stream<int>.multi((c) => c
        ..add(1)
        ..addError(denied));
      expect(await whileMember(h.guard, 'family', source).toList(), [1]);
      expect(h.writes, ['personal']);
    });

    test('passes the error on when the user is still a member', () async {
      final h = GuardHarness(server: (activeHouseholdId: 'family', profileHasPendingWrites: false, household: home('family', 'F', ['owner', 'me'])));
      final source = Stream<int>.error(denied);
      await expectLater(whileMember(h.guard, 'family', source), emitsError(same(denied)));
    });

    test('passes other errors on without asking the server', () async {
      final h = GuardHarness();
      await expectLater(whileMember(h.guard, 'family', Stream<int>.error(StateError('x'))), emitsError(isStateError));
      expect(h.fetches, isEmpty);
    });
  });

  test('allTransactionsProvider keeps its data instead of a permission error', () async {
    final h = GuardHarness();
    final transactions = StreamController<List<Transaction>>();
    final container = ProviderContainer.test(
      overrides: [
        currentUidProvider.overrideWithValue('me'),
        ledgerProvider.overrideWithValue(_FakeLedger(transactions.stream)),
        membershipGuardProvider.overrideWithValue(h.guard),
      ],
    );
    final states = <AsyncValue<List<Transaction>>>[];
    container.listen(allTransactionsProvider, (_, next) => states.add(next), fireImmediately: true);

    transactions.add([tx(amount: 100, date: now)]);
    await pumpEventQueue();
    transactions.addError(denied);
    await pumpEventQueue();

    expect(states.any((s) => s.hasError), isFalse);
    expect(container.read(allTransactionsProvider).value, hasLength(1));
    expect(h.writes, ['personal']);
    await transactions.close();
  });
}
