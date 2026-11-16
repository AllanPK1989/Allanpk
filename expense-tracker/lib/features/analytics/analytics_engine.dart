import 'dart:math' as math;

import '../../core/utils/date_utils.dart';
import '../../models/models.dart';

/// Totals for a period.
class PeriodSummary {
  const PeriodSummary({
    required this.income,
    required this.expense,
    required this.transactionCount,
    required this.days,
    this.largestExpense,
  });

  final double income;
  final double expense;
  final int transactionCount;
  final int days;
  final Transaction? largestExpense;

  double get net => roundMoney(income - expense);
  double get savingsRate => income <= 0 ? 0 : ((income - expense) / income).clamp(-1, 1).toDouble();
  double get averageDailySpend => days <= 0 ? 0 : expense / days;

  static const empty = PeriodSummary(income: 0, expense: 0, transactionCount: 0, days: 0);
}

class CategorySpend {
  const CategorySpend({
    required this.categoryId,
    required this.name,
    required this.color,
    required this.iconKey,
    required this.amount,
    required this.count,
    required this.share,
  });

  final String? categoryId;
  final String name;
  final int color;
  final String iconKey;
  final double amount;
  final int count;

  /// Fraction of the total (0-1).
  final double share;
}

class DailyPoint {
  const DailyPoint(this.date, this.expense, this.income);
  final DateTime date;
  final double expense;
  final double income;
  double get net => income - expense;
}

class MonthPoint {
  const MonthPoint(this.month, this.expense, this.income);
  final DateTime month;
  final double expense;
  final double income;
  double get net => income - expense;
}

class Comparison {
  const Comparison({required this.current, required this.previous});
  final double current;
  final double previous;
  double get delta => current - previous;

  /// Null when there is nothing to compare against.
  double? get percent => previous == 0 ? null : delta / previous;
}

class PayeeSpend {
  const PayeeSpend(this.payee, this.amount, this.count);
  final String payee;
  final double amount;
  final int count;
}

class MemberSpend {
  const MemberSpend({
    required this.uid,
    required this.name,
    required this.color,
    required this.expense,
    required this.income,
    required this.count,
  });
  final String uid;
  final String name;
  final int color;
  final double expense;
  final double income;
  final int count;
}

enum BudgetStatus { onTrack, warning, over }

class BudgetProgress {
  const BudgetProgress({
    required this.budget,
    required this.range,
    required this.spent,
    required this.limit,
    required this.daysLeft,
    required this.elapsedFraction,
    required this.transactions,
  });

  final Budget budget;
  final DateRange range;
  final double spent;

  /// Effective limit including rollover from the previous period.
  final double limit;
  final int daysLeft;
  final double elapsedFraction;
  final List<Transaction> transactions;

  double get remaining => limit - spent;
  double get fraction => limit <= 0 ? 0 : (spent / limit).clamp(0, 1.5).toDouble();
  double get dailyAllowance => daysLeft <= 0 ? 0 : math.max(0, remaining) / daysLeft;

  /// Spend expected at this point if spending were perfectly even.
  double get expectedByNow => limit * elapsedFraction;
  double get projectedTotal => elapsedFraction <= 0 ? spent : spent / elapsedFraction;

  BudgetStatus get status {
    if (limit <= 0) return BudgetStatus.onTrack;
    if (spent > limit) return BudgetStatus.over;
    if (spent / limit >= budget.alertThreshold) return BudgetStatus.warning;
    return BudgetStatus.onTrack;
  }
}

class AccountBalance {
  const AccountBalance(this.account, this.balance, this.transactionCount);
  final Account account;
  final double balance;
  final int transactionCount;
}

class Forecast {
  const Forecast({
    required this.spentSoFar,
    required this.projectedTotal,
    required this.averageDaily,
    required this.daysRemaining,
  });
  final double spentSoFar;
  final double projectedTotal;
  final double averageDaily;
  final int daysRemaining;
}

enum InsightTone { positive, neutral, warning }

class Insight {
  const Insight(this.title, this.body, this.tone, {this.iconKey = 'star'});
  final String title;
  final String body;
  final InsightTone tone;
  final String iconKey;
}

/// Pure functions over transaction lists. No Flutter, no Firebase.
class AnalyticsEngine {
  AnalyticsEngine._();

  static List<Transaction> inRange(Iterable<Transaction> txs, DateRange range) =>
      txs.where((t) => range.contains(t.date)).toList();

  static PeriodSummary summarize(Iterable<Transaction> txs, DateRange range) {
    var income = 0.0;
    var expense = 0.0;
    var count = 0;
    Transaction? largest;
    for (final t in txs) {
      if (!range.contains(t.date)) continue;
      count++;
      if (t.isIncome) income += t.amount;
      if (t.isExpense) {
        expense += t.amount;
        if (largest == null || t.amount > largest.amount) largest = t;
      }
    }
    return PeriodSummary(
      income: roundMoney(income),
      expense: roundMoney(expense),
      transactionCount: count,
      days: range.days,
      largestExpense: largest,
    );
  }

  static List<CategorySpend> byCategory(
    Iterable<Transaction> txs,
    Map<String, Category> categories, {
    TransactionType type = TransactionType.expense,
    DateRange? range,
  }) {
    final totals = <String?, double>{};
    final counts = <String?, int>{};
    var grand = 0.0;
    for (final t in txs) {
      if (t.type != type) continue;
      if (range != null && !range.contains(t.date)) continue;
      // Roll sub-categories into their parent for the top-level view.
      final cat = categories[t.categoryId];
      final key = cat?.parentId ?? t.categoryId;
      totals[key] = (totals[key] ?? 0) + t.amount;
      counts[key] = (counts[key] ?? 0) + 1;
      grand += t.amount;
    }
    final list = totals.entries.map((e) {
      final cat = categories[e.key];
      return CategorySpend(
        categoryId: e.key,
        name: cat?.name ?? 'Uncategorised',
        color: cat?.color ?? 0xFF78909C,
        iconKey: cat?.iconKey ?? 'category',
        amount: roundMoney(e.value),
        count: counts[e.key] ?? 0,
        share: grand <= 0 ? 0 : e.value / grand,
      );
    }).toList()
      ..sort((a, b) => b.amount.compareTo(a.amount));
    return list;
  }

  /// Breakdown of one parent category into its sub-categories.
  static List<CategorySpend> bySubcategory(
    Iterable<Transaction> txs,
    Map<String, Category> categories,
    String parentId,
  ) {
    final totals = <String, double>{};
    final counts = <String, int>{};
    var grand = 0.0;
    for (final t in txs) {
      if (!t.isExpense) continue;
      final cat = categories[t.categoryId];
      if (cat == null) continue;
      if (cat.id != parentId && cat.parentId != parentId) continue;
      final key = cat.id;
      totals[key] = (totals[key] ?? 0) + t.amount;
      counts[key] = (counts[key] ?? 0) + 1;
      grand += t.amount;
    }
    return totals.entries.map((e) {
      final cat = categories[e.key]!;
      return CategorySpend(
        categoryId: cat.id,
        name: cat.id == parentId ? '${cat.name} (general)' : cat.name,
        color: cat.color,
        iconKey: cat.iconKey,
        amount: roundMoney(e.value),
        count: counts[e.key] ?? 0,
        share: grand <= 0 ? 0 : e.value / grand,
      );
    }).toList()
      ..sort((a, b) => b.amount.compareTo(a.amount));
  }

  static List<DailyPoint> dailySeries(Iterable<Transaction> txs, DateRange range) {
    final expense = <DateTime, double>{};
    final income = <DateTime, double>{};
    for (final t in txs) {
      if (!range.contains(t.date)) continue;
      final day = AppDates.dateOnly(t.date);
      if (t.isExpense) expense[day] = (expense[day] ?? 0) + t.amount;
      if (t.isIncome) income[day] = (income[day] ?? 0) + t.amount;
    }
    final points = <DailyPoint>[];
    var cursor = AppDates.dateOnly(range.start);
    final last = AppDates.dateOnly(range.end);
    while (!cursor.isAfter(last)) {
      points.add(DailyPoint(cursor, expense[cursor] ?? 0, income[cursor] ?? 0));
      cursor = cursor.add(const Duration(days: 1));
    }
    return points;
  }

  /// Cumulative expense per day, handy for pace-vs-budget lines.
  static List<DailyPoint> cumulativeSeries(List<DailyPoint> daily) {
    var e = 0.0;
    var i = 0.0;
    return daily.map((p) {
      e += p.expense;
      i += p.income;
      return DailyPoint(p.date, e, i);
    }).toList();
  }

  static List<MonthPoint> monthlySeries(
    Iterable<Transaction> txs, {
    required DateTime endMonth,
    int months = 6,
  }) {
    final start = DateTime(endMonth.year, endMonth.month - months + 1, 1);
    final expense = <int, double>{};
    final income = <int, double>{};
    for (final t in txs) {
      if (t.date.isBefore(start)) continue;
      final key = t.date.year * 12 + t.date.month;
      if (t.isExpense) expense[key] = (expense[key] ?? 0) + t.amount;
      if (t.isIncome) income[key] = (income[key] ?? 0) + t.amount;
    }
    return List.generate(months, (i) {
      final m = DateTime(start.year, start.month + i, 1);
      final key = m.year * 12 + m.month;
      return MonthPoint(m, roundMoney(expense[key] ?? 0), roundMoney(income[key] ?? 0));
    });
  }

  static Comparison compareExpense(Iterable<Transaction> txs, DateRange current) {
    final prev = current.previous();
    return Comparison(
      current: summarize(txs, current).expense,
      previous: summarize(txs, prev).expense,
    );
  }

  static List<PayeeSpend> topPayees(Iterable<Transaction> txs, {int limit = 5, DateRange? range}) {
    final totals = <String, double>{};
    final counts = <String, int>{};
    for (final t in txs) {
      if (!t.isExpense || t.payee.trim().isEmpty) continue;
      if (range != null && !range.contains(t.date)) continue;
      final key = t.payee.trim();
      totals[key] = (totals[key] ?? 0) + t.amount;
      counts[key] = (counts[key] ?? 0) + 1;
    }
    final list = totals.entries
        .map((e) => PayeeSpend(e.key, roundMoney(e.value), counts[e.key] ?? 0))
        .toList()
      ..sort((a, b) => b.amount.compareTo(a.amount));
    return list.take(limit).toList();
  }

  /// Average expense per weekday, index 0 = Monday.
  static List<double> weekdayAverages(Iterable<Transaction> txs, DateRange range) {
    final totals = List<double>.filled(7, 0);
    final dayCounts = List<int>.filled(7, 0);
    var cursor = AppDates.dateOnly(range.start);
    final last = AppDates.dateOnly(range.end);
    while (!cursor.isAfter(last)) {
      dayCounts[cursor.weekday - 1]++;
      cursor = cursor.add(const Duration(days: 1));
    }
    for (final t in txs) {
      if (!t.isExpense || !range.contains(t.date)) continue;
      totals[t.date.weekday - 1] += t.amount;
    }
    return List.generate(7, (i) => dayCounts[i] == 0 ? 0 : totals[i] / dayCounts[i]);
  }

  static List<MemberSpend> byMember(
    Iterable<Transaction> txs,
    Household household, {
    DateRange? range,
  }) {
    final expense = <String, double>{};
    final income = <String, double>{};
    final counts = <String, int>{};
    for (final t in txs) {
      if (range != null && !range.contains(t.date)) continue;
      if (t.isTransfer) continue;
      final uid = t.createdBy;
      counts[uid] = (counts[uid] ?? 0) + 1;
      if (t.isExpense) expense[uid] = (expense[uid] ?? 0) + t.amount;
      if (t.isIncome) income[uid] = (income[uid] ?? 0) + t.amount;
    }
    final ids = {...expense.keys, ...income.keys};
    final list = ids.map((uid) {
      final m = household.members[uid];
      return MemberSpend(
        uid: uid,
        name: m?.name ?? 'Former member',
        color: m?.color ?? 0xFF78909C,
        expense: roundMoney(expense[uid] ?? 0),
        income: roundMoney(income[uid] ?? 0),
        count: counts[uid] ?? 0,
      );
    }).toList()
      ..sort((a, b) => b.expense.compareTo(a.expense));
    return list;
  }

  /// The active window of a budget containing [now].
  static DateRange budgetRange(Budget budget, DateTime now, {int monthStartDay = 1}) {
    switch (budget.period) {
      case BudgetPeriod.weekly:
        return DateRange.week(now);
      case BudgetPeriod.monthly:
        return DateRange.month(now, startDay: monthStartDay);
      case BudgetPeriod.quarterly:
        return DateRange.quarter(now);
      case BudgetPeriod.yearly:
        return DateRange.year(now);
      case BudgetPeriod.custom:
        return DateRange.custom(budget.startDate, budget.endDate ?? budget.startDate);
    }
  }

  static bool budgetMatches(Budget budget, Transaction t) {
    if (!t.isExpense) return false;
    if (budget.categoryIds.isNotEmpty &&
        !budget.categoryIds.contains(t.categoryId)) {
      return false;
    }
    if (budget.accountIds.isNotEmpty && !budget.accountIds.contains(t.accountId)) return false;
    if (budget.memberIds.isNotEmpty && !budget.memberIds.contains(t.createdBy)) return false;
    return true;
  }

  static BudgetProgress budgetProgress(
    Budget budget,
    Iterable<Transaction> txs,
    DateTime now, {
    int monthStartDay = 1,
    Map<String, Category> categories = const {},
  }) {
    final range = budgetRange(budget, now, monthStartDay: monthStartDay);
    final matching = <Transaction>[];
    var spent = 0.0;
    for (final t in txs) {
      if (!range.contains(t.date)) continue;
      if (!_matchesWithSubcategories(budget, t, categories)) continue;
      matching.add(t);
      spent += t.amount;
    }
    var limit = budget.amount;
    if (budget.rollover && budget.period != BudgetPeriod.custom) {
      final prev = range.previous();
      var prevSpent = 0.0;
      for (final t in txs) {
        if (prev.contains(t.date) && _matchesWithSubcategories(budget, t, categories)) {
          prevSpent += t.amount;
        }
      }
      if (!prev.end.isBefore(budget.startDate)) {
        limit += budget.amount - prevSpent;
      }
    }
    final elapsed = range.elapsedDays(now);
    final daysLeft = math.max(0, range.days - elapsed);
    return BudgetProgress(
      budget: budget,
      range: range,
      spent: roundMoney(spent),
      limit: roundMoney(math.max(0, limit)),
      daysLeft: daysLeft,
      elapsedFraction: range.days == 0 ? 1 : (elapsed / range.days).clamp(0, 1).toDouble(),
      transactions: matching..sort((a, b) => b.date.compareTo(a.date)),
    );
  }

  static bool _matchesWithSubcategories(
    Budget budget,
    Transaction t,
    Map<String, Category> categories,
  ) {
    if (!t.isExpense) return false;
    if (budget.categoryIds.isNotEmpty) {
      final cat = categories[t.categoryId];
      final matchesSelf = budget.categoryIds.contains(t.categoryId);
      final matchesParent = cat?.parentId != null && budget.categoryIds.contains(cat!.parentId);
      if (!matchesSelf && !matchesParent) return false;
    }
    if (budget.accountIds.isNotEmpty && !budget.accountIds.contains(t.accountId)) return false;
    if (budget.memberIds.isNotEmpty && !budget.memberIds.contains(t.createdBy)) return false;
    return true;
  }

  static List<AccountBalance> balances(
    Iterable<Account> accounts,
    Iterable<Transaction> allTxs, {
    DateTime? asOf,
  }) {
    final delta = <String, double>{};
    final counts = <String, int>{};
    for (final t in allTxs) {
      if (asOf != null && t.date.isAfter(asOf)) continue;
      counts[t.accountId] = (counts[t.accountId] ?? 0) + 1;
      switch (t.type) {
        case TransactionType.income:
          delta[t.accountId] = (delta[t.accountId] ?? 0) + t.amount;
        case TransactionType.expense:
          delta[t.accountId] = (delta[t.accountId] ?? 0) - t.amount;
        case TransactionType.transfer:
          delta[t.accountId] = (delta[t.accountId] ?? 0) - t.amount;
          if (t.toAccountId != null) {
            delta[t.toAccountId!] = (delta[t.toAccountId!] ?? 0) + t.amount;
            counts[t.toAccountId!] = (counts[t.toAccountId!] ?? 0) + 1;
          }
      }
    }
    return accounts
        .map(
          (a) => AccountBalance(
            a,
            roundMoney(a.initialBalance + (delta[a.id] ?? 0)),
            counts[a.id] ?? 0,
          ),
        )
        .toList();
  }

  static double netWorth(List<AccountBalance> balances) => roundMoney(
        balances
            .where((b) => !b.account.isArchived && !b.account.excludeFromTotals)
            .fold(0.0, (sum, b) => sum + b.balance),
      );

  static Forecast forecast(Iterable<Transaction> txs, DateRange range, DateTime now) {
    final elapsed = range.elapsedDays(now);
    final spent = summarize(txs, range).expense;
    final avg = elapsed <= 0 ? 0.0 : spent / elapsed;
    final remaining = math.max(0, range.days - elapsed);
    return Forecast(
      spentSoFar: spent,
      projectedTotal: roundMoney(spent + avg * remaining),
      averageDaily: roundMoney(avg),
      daysRemaining: remaining,
    );
  }

  /// Human-readable observations for the dashboard and PDF report.
  static List<Insight> insights({
    required Iterable<Transaction> txs,
    required DateRange range,
    required Map<String, Category> categories,
    required List<BudgetProgress> budgets,
    required String Function(double) money,
    DateTime? now,
  }) {
    final result = <Insight>[];
    final current = summarize(txs, range);
    final previous = summarize(txs, range.previous());
    final today = now ?? DateTime.now();

    if (current.transactionCount == 0) {
      return const [
        Insight(
          'No activity yet',
          'Add a few transactions and insights will appear here.',
          InsightTone.neutral,
          iconKey: 'rocket_launch',
        ),
      ];
    }

    if (previous.expense > 0) {
      final change = (current.expense - previous.expense) / previous.expense;
      if (change.abs() >= 0.1) {
        final up = change > 0;
        result.add(
          Insight(
            up ? 'Spending is up' : 'Spending is down',
            '${(change.abs() * 100).round()}% ${up ? 'more' : 'less'} than the previous period '
            '(${money(previous.expense)} → ${money(current.expense)}).',
            up ? InsightTone.warning : InsightTone.positive,
            iconKey: up ? 'trending_up' : 'savings',
          ),
        );
      }
    }

    final cats = byCategory(txs, categories, range: range);
    if (cats.isNotEmpty) {
      final top = cats.first;
      result.add(
        Insight(
          'Biggest category: ${top.name}',
          '${(top.share * 100).round()}% of spending (${money(top.amount)}) across ${top.count} '
          '${top.count == 1 ? 'transaction' : 'transactions'}.',
          top.share > 0.5 ? InsightTone.warning : InsightTone.neutral,
          iconKey: top.iconKey,
        ),
      );
    }

    if (current.income > 0) {
      final rate = current.savingsRate;
      result.add(
        Insight(
          rate >= 0.2
              ? 'Healthy savings rate'
              : rate >= 0
                  ? 'Savings could be higher'
                  : 'Spending exceeds income',
          rate >= 0
              ? 'You kept ${(rate * 100).round()}% of your income (${money(current.net)}).'
              : 'You spent ${money(-current.net)} more than you earned.',
          rate >= 0.2
              ? InsightTone.positive
              : rate >= 0
                  ? InsightTone.neutral
                  : InsightTone.warning,
          iconKey: 'savings',
        ),
      );
    }

    final over = budgets.where((b) => b.status == BudgetStatus.over).toList();
    final warn = budgets.where((b) => b.status == BudgetStatus.warning).toList();
    if (over.isNotEmpty) {
      result.add(
        Insight(
          '${over.length} ${over.length == 1 ? 'budget' : 'budgets'} over limit',
          over.map((b) => '${b.budget.name} (${money(b.spent - b.limit)} over)').join(', '),
          InsightTone.warning,
          iconKey: 'request_quote',
        ),
      );
    } else if (warn.isNotEmpty) {
      result.add(
        Insight(
          'Approaching budget limits',
          warn.map((b) => '${b.budget.name} at ${(b.fraction * 100).round()}%').join(', '),
          InsightTone.warning,
          iconKey: 'request_quote',
        ),
      );
    } else if (budgets.isNotEmpty) {
      result.add(
        const Insight(
          'All budgets on track',
          'Nice work. Every budget is within its limit so far.',
          InsightTone.positive,
          iconKey: 'emoji_events',
        ),
      );
    }

    final weekday = weekdayAverages(txs, range);
    final maxIdx = weekday.indexOf(weekday.reduce(math.max));
    if (weekday[maxIdx] > 0 && current.transactionCount >= 7) {
      const names = ['Mondays', 'Tuesdays', 'Wednesdays', 'Thursdays', 'Fridays', 'Saturdays', 'Sundays'];
      result.add(
        Insight(
          'You spend most on ${names[maxIdx]}',
          'Average ${money(weekday[maxIdx])} per ${names[maxIdx].substring(0, names[maxIdx].length - 1)}.',
          InsightTone.neutral,
          iconKey: 'celebration',
        ),
      );
    }

    final largest = current.largestExpense;
    if (largest != null && current.expense > 0 && largest.amount / current.expense >= 0.25) {
      final cat = categories[largest.categoryId]?.name ?? 'Uncategorised';
      result.add(
        Insight(
          'One large expense stands out',
          '${money(largest.amount)} on $cat'
          '${largest.payee.isNotEmpty ? ' at ${largest.payee}' : ''} is '
          '${(largest.amount / current.expense * 100).round()}% of the period.',
          InsightTone.neutral,
          iconKey: 'receipt_long',
        ),
      );
    }

    if (range.contains(today)) {
      final f = forecast(txs, range, today);
      if (f.daysRemaining > 0 && f.averageDaily > 0) {
        result.add(
          Insight(
            'Projected spend: ${money(f.projectedTotal)}',
            'At ${money(f.averageDaily)} per day you will spend about ${money(f.projectedTotal)} '
            'by the end of the period.',
            InsightTone.neutral,
            iconKey: 'trending_up',
          ),
        );
      }
    }
    return result;
  }
}
