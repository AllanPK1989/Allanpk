import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/utils/date_utils.dart';
import '../../data/ledger_repository.dart';
import '../../models/models.dart';
import '../../services/currency_service.dart';
import '../analytics/analytics_engine.dart';
import '../auth/auth_providers.dart';
import 'membership_guard.dart';

final userProfileProvider = StreamProvider<UserProfile?>((ref) {
  final uid = ref.watch(currentUidProvider);
  if (uid == null) return Stream.value(null);
  return ref.watch(userRepositoryProvider).watchProfile(uid);
});

/// The active household id alone, so household-scoped providers rebuild when
/// it changes rather than on every profile update.
final activeHouseholdIdProvider = Provider<String?>((ref) {
  return ref.watch(userProfileProvider.select((p) => p.value?.activeHouseholdId));
});

final activeHouseholdProvider = StreamProvider<Household?>((ref) {
  final hid = ref.watch(activeHouseholdIdProvider);
  if (hid == null) return Stream.value(null);
  final guard = ref.watch(membershipGuardProvider);
  final household = ref.watch(userRepositoryProvider).watchHousehold(hid).map((h) {
    guard.observeHousehold(hid, h);
    return h;
  });
  return whileMember(guard, hid, household);
});

final householdsProvider = StreamProvider<List<Household>>((ref) {
  final uid = ref.watch(currentUidProvider);
  if (uid == null) return Stream.value(const []);
  return ref.watch(userRepositoryProvider).watchHouseholdsFor(uid);
});

/// Notices when the owner removed the user from their active household and
/// moves them to another household, or to onboarding.
final membershipGuardProvider = Provider<MembershipGuard>((ref) {
  final uid = ref.watch(currentUidProvider);
  final users = ref.watch(userRepositoryProvider);
  final guard = MembershipGuard(
    uid: uid,
    fetchMembership: users.fetchMembership,
    setActiveHousehold: users.switchHousehold,
    activeHouseholdId: () => ref.mounted ? ref.read(activeHouseholdIdProvider) : null,
    households: () => ref.mounted ? ref.read(householdsProvider.future) : Future.value(const []),
  );
  // Keeps the household list warm so a removed user is switched at once.
  ref.listen(
    householdsProvider,
    (_, next) => guard.observeHouseholds(next.value ?? const []),
    fireImmediately: true,
  );
  ref.listen(activeHouseholdIdProvider, (_, _) => guard.activeHouseholdChanged());
  ref.onDispose(guard.dispose);
  return guard;
});

/// One event per removal, for the snackbar.
final removalNoticeProvider = StreamProvider<RemovalNotice>((ref) {
  return ref.watch(membershipGuardProvider).notices;
});

/// The caller's role in the active household.
final myRoleProvider = Provider<MemberRole>((ref) {
  final uid = ref.watch(currentUidProvider);
  final household = ref.watch(activeHouseholdProvider).value;
  if (uid == null || household == null) return MemberRole.child;
  return household.roleOf(uid);
});

final baseCurrencyProvider = Provider<String>((ref) {
  return ref.watch(activeHouseholdProvider).value?.baseCurrency ?? 'INR';
});

final ledgerProvider = Provider<LedgerRepository?>((ref) {
  final hid = ref.watch(activeHouseholdIdProvider);
  if (hid == null) return null;
  return LedgerRepository(ref.watch(firestoreRefsProvider), hid);
});

/// Ledger streams lose access the moment the owner removes the user; see
/// [whileMember] for how that is kept from surfacing as an error.
Stream<T> _whileMember<T>(Ref ref, LedgerRepository ledger, Stream<T> source) {
  return whileMember(ref.watch(membershipGuardProvider), ledger.householdId, source);
}

final accountsProvider = StreamProvider<List<Account>>((ref) {
  final ledger = ref.watch(ledgerProvider);
  if (ledger == null) return Stream.value(const []);
  return _whileMember(ref, ledger, ledger.watchAccounts());
});

final categoriesProvider = StreamProvider<List<Category>>((ref) {
  final ledger = ref.watch(ledgerProvider);
  if (ledger == null) return Stream.value(const []);
  return _whileMember(ref, ledger, ledger.watchCategories());
});

final categoryMapProvider = Provider<Map<String, Category>>((ref) {
  final list = ref.watch(categoriesProvider).value ?? const [];
  return {for (final c in list) c.id: c};
});

final accountMapProvider = Provider<Map<String, Account>>((ref) {
  final list = ref.watch(accountsProvider).value ?? const [];
  return {for (final a in list) a.id: a};
});

final budgetsProvider = StreamProvider<List<Budget>>((ref) {
  final ledger = ref.watch(ledgerProvider);
  if (ledger == null) return Stream.value(const []);
  return _whileMember(ref, ledger, ledger.watchBudgets());
});

final goalsProvider = StreamProvider<List<Goal>>((ref) {
  final ledger = ref.watch(ledgerProvider);
  if (ledger == null) return Stream.value(const []);
  return _whileMember(ref, ledger, ledger.watchGoals());
});

final recurringProvider = StreamProvider<List<RecurringRule>>((ref) {
  final ledger = ref.watch(ledgerProvider);
  if (ledger == null) return Stream.value(const []);
  return _whileMember(ref, ledger, ledger.watchRecurring());
});

final activityProvider = StreamProvider<List<ActivityEntry>>((ref) {
  final ledger = ref.watch(ledgerProvider);
  if (ledger == null) return Stream.value(const []);
  return _whileMember(ref, ledger, ledger.watchActivity());
});

/// Every transaction the current user may see in the active household.
/// Firestore keeps it in the offline cache, so derived providers below are
/// cheap in-memory computations.
final allTransactionsProvider = StreamProvider<List<Transaction>>((ref) {
  final ledger = ref.watch(ledgerProvider);
  final uid = ref.watch(currentUidProvider);
  if (ledger == null || uid == null) return Stream.value(const []);
  return _whileMember(ref, ledger, ledger.watchAllTransactions(uid));
});

/// Period shown on the dashboard and transaction list.
class SelectedPeriodNotifier extends Notifier<DateRange> {
  @override
  DateRange build() {
    final startDay = ref.watch(activeHouseholdProvider).value?.monthStartDay ?? 1;
    return DateRange.month(DateTime.now(), startDay: startDay);
  }

  int get _startDay => ref.read(activeHouseholdProvider).value?.monthStartDay ?? 1;

  void set(DateRange range) => state = range;

  void nextMonth() {
    final anchor = AppDates.addMonths(state.start, 1);
    state = DateRange.month(anchor, startDay: _startDay);
  }

  void previousMonth() {
    final anchor = AppDates.addMonths(state.start, -1);
    state = DateRange.month(anchor, startDay: _startDay);
  }

  void thisMonth() => state = DateRange.month(DateTime.now(), startDay: _startDay);
}

final selectedPeriodProvider =
    NotifierProvider<SelectedPeriodNotifier, DateRange>(SelectedPeriodNotifier.new);

final periodTransactionsProvider = Provider<List<Transaction>>((ref) {
  final all = ref.watch(allTransactionsProvider).value ?? const [];
  final range = ref.watch(selectedPeriodProvider);
  return AnalyticsEngine.inRange(all, range);
});

final periodSummaryProvider = Provider<PeriodSummary>((ref) {
  final all = ref.watch(allTransactionsProvider).value ?? const [];
  return AnalyticsEngine.summarize(all, ref.watch(selectedPeriodProvider));
});

final balancesProvider = Provider<List<AccountBalance>>((ref) {
  final accounts = ref.watch(accountsProvider).value ?? const [];
  final all = ref.watch(allTransactionsProvider).value ?? const [];
  return AnalyticsEngine.balances(accounts, all);
});

final netWorthProvider = Provider<double>((ref) {
  return AnalyticsEngine.netWorth(ref.watch(balancesProvider));
});

final budgetProgressProvider = Provider<List<BudgetProgress>>((ref) {
  final budgets = ref.watch(budgetsProvider).value ?? const [];
  final all = ref.watch(allTransactionsProvider).value ?? const [];
  final startDay = ref.watch(activeHouseholdProvider).value?.monthStartDay ?? 1;
  final categories = ref.watch(categoryMapProvider);
  final now = DateTime.now();
  return budgets
      .where((b) => !b.isArchived)
      .map(
        (b) => AnalyticsEngine.budgetProgress(
          b,
          all,
          now,
          monthStartDay: startDay,
          categories: categories,
        ),
      )
      .toList()
    ..sort((a, b) => b.fraction.compareTo(a.fraction));
});

/// Exchange rates for the household base currency.
final ratesProvider = FutureProvider<RateTable>((ref) {
  final base = ref.watch(baseCurrencyProvider);
  return ref.watch(currencyServiceProvider).rates(base);
});

/// Distinct payees and tags for autocomplete.
final payeeSuggestionsProvider = Provider<List<String>>((ref) {
  final all = ref.watch(allTransactionsProvider).value ?? const [];
  final counts = <String, int>{};
  for (final t in all) {
    final p = t.payee.trim();
    if (p.isEmpty) continue;
    counts[p] = (counts[p] ?? 0) + 1;
  }
  final list = counts.keys.toList()..sort((a, b) => counts[b]!.compareTo(counts[a]!));
  return list;
});

final tagSuggestionsProvider = Provider<List<String>>((ref) {
  final all = ref.watch(allTransactionsProvider).value ?? const [];
  final set = <String>{};
  for (final t in all) {
    set.addAll(t.tags);
  }
  return set.toList()..sort();
});
