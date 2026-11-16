import 'package:expense_budget_manager/core/utils/date_utils.dart';
import 'package:expense_budget_manager/features/analytics/analytics_engine.dart';
import 'package:expense_budget_manager/models/models.dart';
import 'package:flutter_test/flutter_test.dart';

import 'helpers.dart';

void main() {
  final range = DateRange.month(now);
  final categories = {
    'food': cat('food', 'Food'),
    'groceries': cat('groceries', 'Groceries', parentId: 'food'),
    'rent': cat('rent', 'Rent'),
    'salary': cat('salary', 'Salary', kind: CategoryKind.income),
  };

  final txs = [
    tx(id: '1', amount: 500, date: DateTime(2026, 11, 2), categoryId: 'food', payee: 'Cafe'),
    tx(id: '2', amount: 1200, date: DateTime(2026, 11, 5), categoryId: 'groceries', payee: 'Mart'),
    tx(id: '3', amount: 15000, date: DateTime(2026, 11, 1), categoryId: 'rent', payee: 'Landlord'),
    tx(id: '4', type: TransactionType.income, amount: 50000, date: DateTime(2026, 11, 1), categoryId: 'salary'),
    tx(id: '5', type: TransactionType.transfer, amount: 2000, date: DateTime(2026, 11, 3), accountId: 'cash', toAccountId: 'bank'),
    // previous month
    tx(id: '6', amount: 10000, date: DateTime(2026, 10, 10), categoryId: 'rent'),
    tx(id: '7', amount: 300, date: DateTime(2026, 10, 12), categoryId: 'food', createdBy: 'u2'),
  ];

  group('summarize', () {
    test('totals income, expense and net for the range only', () {
      final s = AnalyticsEngine.summarize(txs, range);
      expect(s.income, 50000);
      expect(s.expense, 16700);
      expect(s.net, 33300);
      expect(s.transactionCount, 5);
      expect(s.largestExpense?.id, '3');
      expect(s.savingsRate, closeTo(0.666, 0.001));
    });

    test('handles empty input', () {
      final s = AnalyticsEngine.summarize(const [], range);
      expect(s.expense, 0);
      expect(s.savingsRate, 0);
      expect(s.averageDailySpend, 0);
    });
  });

  group('byCategory', () {
    test('rolls sub-categories into parents and sorts by amount', () {
      final slices = AnalyticsEngine.byCategory(AnalyticsEngine.inRange(txs, range), categories);
      expect(slices.map((s) => s.name).toList(), ['Rent', 'Food']);
      expect(slices[1].amount, 1700); // 500 cafe + 1200 groceries
      expect(slices[1].count, 2);
      expect(slices[0].share, closeTo(15000 / 16700, 1e-9));
    });

    test('bySubcategory splits a parent', () {
      final subs = AnalyticsEngine.bySubcategory(AnalyticsEngine.inRange(txs, range), categories, 'food');
      expect(subs.first.name, 'Groceries');
      expect(subs.last.name, 'Food (general)');
    });

    test('income categories', () {
      final slices = AnalyticsEngine.byCategory(txs, categories, type: TransactionType.income, range: range);
      expect(slices.single.name, 'Salary');
      expect(slices.single.share, 1);
    });
  });

  test('dailySeries zero-fills every day of the range', () {
    final daily = AnalyticsEngine.dailySeries(txs, range);
    expect(daily.length, 30);
    expect(daily[0].expense, 15000);
    expect(daily[0].income, 50000);
    expect(daily[1].expense, 500);
    expect(daily[10].expense, 0);
    final cumulative = AnalyticsEngine.cumulativeSeries(daily);
    expect(cumulative.last.expense, 16700);
  });

  test('monthlySeries covers the requested months oldest first', () {
    final months = AnalyticsEngine.monthlySeries(txs, endMonth: DateTime(2026, 11, 1), months: 3);
    expect(months.map((m) => m.month.month).toList(), [9, 10, 11]);
    expect(months[1].expense, 10300);
    expect(months[2].income, 50000);
  });

  test('compareExpense against previous period', () {
    final c = AnalyticsEngine.compareExpense(txs, range);
    expect(c.current, 16700);
    expect(c.previous, 10300);
    expect(c.percent, closeTo(0.621, 0.001));
  });

  test('topPayees aggregates and limits', () {
    final payees = AnalyticsEngine.topPayees(txs, range: range, limit: 2);
    expect(payees.map((p) => p.payee).toList(), ['Landlord', 'Mart']);
  });

  test('weekdayAverages divides by number of weekdays in range', () {
    final avg = AnalyticsEngine.weekdayAverages(txs, range);
    // 1 Nov 2026 is a Sunday: 15000 over 5 Sundays in November.
    expect(avg[6], closeTo(3000, 0.01));
    expect(avg.length, 7);
  });

  test('byMember attributes spending to creators', () {
    final members = AnalyticsEngine.byMember(txs, household());
    expect(members.first.uid, 'u1');
    expect(members.first.expense, 26700);
    expect(members.first.income, 50000);
    expect(members.last.uid, 'u2');
    expect(members.last.expense, 300);
  });

  group('budgets', () {
    final budget = Budget(
      id: 'b',
      name: 'Food',
      amount: 2000,
      period: BudgetPeriod.monthly,
      startDate: DateTime(2026, 1, 1),
      categoryIds: const ['food'],
      createdBy: 'u1',
      createdAt: now,
    );

    test('progress counts parent and sub-category spend', () {
      final p = AnalyticsEngine.budgetProgress(budget, txs, now, categories: categories);
      expect(p.spent, 1700);
      expect(p.limit, 2000);
      expect(p.remaining, 300);
      expect(p.status, BudgetStatus.warning);
      expect(p.daysLeft, 15);
      expect(p.dailyAllowance, 20);
      expect(p.transactions.length, 2);
    });

    test('over budget status and rollover', () {
      final small = budget.copyWith(amount: 1000);
      expect(AnalyticsEngine.budgetProgress(small, txs, now, categories: categories).status, BudgetStatus.over);

      final rolling = budget.copyWith(rollover: true);
      // October food spend was 300, so 1700 unspent rolls into November.
      final p = AnalyticsEngine.budgetProgress(rolling, txs, now, categories: categories);
      expect(p.limit, 3700);
      expect(p.status, BudgetStatus.onTrack);
    });

    test('overall budget matches every expense', () {
      final overall = budget.copyWith(categoryIds: const []);
      final p = AnalyticsEngine.budgetProgress(overall, txs, now, categories: categories);
      expect(p.spent, 16700);
    });

    test('custom month start day shifts the window', () {
      final range25 = AnalyticsEngine.budgetRange(budget, DateTime(2026, 11, 15), monthStartDay: 25);
      expect(range25.start, DateTime(2026, 10, 25));
      expect(range25.end.day, 24);
      expect(range25.end.month, 11);
    });
  });

  test('balances apply income, expenses and both sides of transfers', () {
    final balances = AnalyticsEngine.balances([acc('cash', initial: 1000), acc('bank', initial: 5000)], txs);
    final cash = balances.firstWhere((b) => b.account.id == 'cash');
    final bank = balances.firstWhere((b) => b.account.id == 'bank');
    // cash: 1000 + 50000 - (500+1200+15000+10000+300) - 2000 transfer out
    expect(cash.balance, 22000);
    expect(bank.balance, 7000);
    expect(AnalyticsEngine.netWorth(balances), 29000);
    expect(bank.transactionCount, 1);
  });

  test('forecast projects remaining days at the running average', () {
    final f = AnalyticsEngine.forecast(txs, range, now);
    expect(f.spentSoFar, 16700);
    expect(f.daysRemaining, 15);
    expect(f.averageDaily, closeTo(16700 / 15, 0.01));
    expect(f.projectedTotal, closeTo(33400, 0.5));
  });

  test('insights produce observations with the right tone', () {
    final insights = AnalyticsEngine.insights(
      txs: txs,
      range: range,
      categories: categories,
      budgets: const [],
      money: (v) => v.toStringAsFixed(0),
      now: now,
    );
    expect(insights.any((i) => i.title.contains('Spending is up')), isTrue);
    expect(insights.any((i) => i.title.contains('Biggest category: Rent')), isTrue);
    expect(insights.firstWhere((i) => i.title.contains('savings rate')).tone, InsightTone.positive);
    expect(insights.any((i) => i.title.startsWith('Projected spend')), isTrue);
  });

  test('insights handle no data', () {
    final insights = AnalyticsEngine.insights(
      txs: const [],
      range: range,
      categories: categories,
      budgets: const [],
      money: (v) => '$v',
    );
    expect(insights.single.title, 'No activity yet');
  });
}
