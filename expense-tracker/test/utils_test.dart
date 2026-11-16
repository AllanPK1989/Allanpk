import 'package:expense_budget_manager/core/constants/app_icons.dart';
import 'package:expense_budget_manager/core/utils/date_utils.dart';
import 'package:expense_budget_manager/core/utils/expression.dart';
import 'package:expense_budget_manager/core/utils/money.dart';
import 'package:expense_budget_manager/models/models.dart';
import 'package:flutter_test/flutter_test.dart';

import 'helpers.dart';

void main() {
  group('evaluateExpression', () {
    test('plain numbers and arithmetic', () {
      expect(evaluateExpression('120'), 120);
      expect(evaluateExpression('120+45'), 165);
      expect(evaluateExpression('100 - 25.5'), 74.5);
      expect(evaluateExpression('3*4+2'), 14);
      expect(evaluateExpression('(3+4)*2'), 14);
      expect(evaluateExpression('10/4'), 2.5);
      expect(evaluateExpression('1,250.50'), 1250.5);
      expect(evaluateExpression('2x3'), 6);
    });

    test('rejects garbage', () {
      expect(evaluateExpression(''), isNull);
      expect(evaluateExpression('abc'), isNull);
      expect(evaluateExpression('12+'), isNull);
      expect(evaluateExpression('5/0'), isNull);
      expect(evaluateExpression('(2+3'), isNull);
    });
  });

  group('Money', () {
    test('formats INR with lakh grouping', () {
      expect(Money.format(123456.78, 'INR'), '₹1,23,456.78');
      expect(Money.format(1234.5, 'USD'), r'$1,234.50');
      expect(Money.format(1500, 'JPY'), '¥1,500');
    });

    test('signed and compact', () {
      expect(Money.signed(-500, 'INR'), '-₹500.00');
      expect(Money.signed(500, 'INR'), '+₹500.00');
      expect(Money.format(1500000, 'INR', compact: true), '₹15L');
      expect(Money.format(5830, 'INR', compact: true), '₹5.8K');
      expect(Money.format(2500000, 'USD', compact: true), r'$2.5M');
      expect(Money.format(799, 'INR', compact: true), '₹799');
      expect(Money.percent(0.256), '26%');
    });

    test('parses user input', () {
      expect(Money.parse('₹ 1,250.75'), 1250.75);
      expect(Money.parse('abc'), isNull);
      expect(Money.parse('-42'), -42);
    });
  });

  group('DateRange', () {
    test('month ranges', () {
      final r = DateRange.month(DateTime(2026, 2, 10));
      expect(r.start, DateTime(2026, 2, 1));
      expect(r.end.day, 28);
      expect(r.days, 28);
      expect(r.label(), 'February 2026');
    });

    test('custom month start before and after the start day', () {
      final before = DateRange.month(DateTime(2026, 3, 10), startDay: 25);
      expect(before.start, DateTime(2026, 2, 25));
      expect(before.end, DateTime(2026, 3, 25).subtract(const Duration(milliseconds: 1)));
      final after = DateRange.month(DateTime(2026, 3, 26), startDay: 25);
      expect(after.start, DateTime(2026, 3, 25));
    });

    test('previous() keeps the same length', () {
      final r = DateRange.custom(DateTime(2026, 11, 1), DateTime(2026, 11, 10));
      final p = r.previous();
      expect(p.days, 10);
      expect(p.end.isBefore(r.start), isTrue);
    });

    test('week starts on Monday and quarter covers three months', () {
      final w = DateRange.week(DateTime(2026, 11, 15)); // Sunday
      expect(w.start.weekday, DateTime.monday);
      expect(w.start, DateTime(2026, 11, 9));
      final q = DateRange.quarter(DateTime(2026, 11, 15));
      expect(q.start, DateTime(2026, 10, 1));
      expect(q.end.month, 12);
    });

    test('elapsedDays clamps', () {
      final r = DateRange.month(DateTime(2026, 11, 1));
      expect(r.elapsedDays(DateTime(2026, 11, 15)), 15);
      expect(r.elapsedDays(DateTime(2026, 12, 15)), 30);
      expect(r.elapsedDays(DateTime(2026, 10, 15)), 0);
    });
  });

  group('AppDates', () {
    test('relative day labels', () {
      final today = DateTime(2026, 11, 15, 9);
      expect(AppDates.relativeDay(today, now: today), 'Today');
      expect(AppDates.relativeDay(today.subtract(const Duration(days: 1)), now: today), 'Yesterday');
      expect(AppDates.relativeDay(DateTime(2025, 1, 3), now: today), '3 Jan 2025');
    });

    test('addMonths clamps the day', () {
      expect(AppDates.addMonths(DateTime(2026, 1, 31), 1), DateTime(2026, 2, 28));
      expect(AppDates.addMonths(DateTime(2026, 11, 15), -11), DateTime(2025, 12, 15));
    });
  });

  group('RecurringRule', () {
    final rule = RecurringRule(
      id: 'r',
      type: TransactionType.expense,
      amount: 999,
      currency: 'INR',
      accountId: 'cash',
      frequency: RecurrenceFrequency.monthly,
      nextDue: DateTime(2026, 1, 31),
      createdBy: 'u1',
      createdAt: now,
    );

    test('monthly recurrence keeps end-of-month stable', () {
      expect(rule.nextAfter(DateTime(2026, 1, 31)), DateTime(2026, 2, 28));
      expect(rule.nextAfter(DateTime(2026, 3, 31)), DateTime(2026, 4, 30));
    });

    test('dueOccurrences lists every missed run up to now without drifting', () {
      final due = rule.dueOccurrences(DateTime(2026, 4, 15));
      expect(due, [DateTime(2026, 1, 31), DateTime(2026, 2, 28), DateTime(2026, 3, 31)]);
      // Chaining through February must return to the anchored 31st.
      expect(rule.nextAfter(DateTime(2026, 2, 28)), DateTime(2026, 3, 31));
      expect(RecurringRule.fromMap('r', rule.toMap()).anchorDay, 31);
    });

    test('respects end date and intervals', () {
      final weekly = rule.copyWith(frequency: RecurrenceFrequency.weekly, interval: 2, nextDue: DateTime(2026, 1, 1), endDate: DateTime(2026, 1, 20));
      final due = weekly.dueOccurrences(DateTime(2026, 3, 1));
      expect(due, [DateTime(2026, 1, 1), DateTime(2026, 1, 15)]);
      expect(weekly.frequencyLabel, 'Every 2 weeks');
    });
  });

  test('member colours are vivid and stable', () {
    expect(memberColorFor('abc'), memberColorFor('abc'));
    for (final id in ['a', 'uid-123', 'XyZ987', '']) {
      expect(kMemberPalette, contains(memberColorFor(id)));
    }
  });

  group('models round-trip', () {
    test('transaction toMap/fromMap', () {
      final t = tx(id: 'x', amount: 12.34, date: DateTime(2026, 5, 6, 7, 8), categoryId: 'c', payee: 'P', tags: const ['a']);
      final back = Transaction.fromMap('x', t.toMap());
      expect(back.amount, 12.34);
      expect(back.date, t.date);
      expect(back.tags, ['a']);
      expect(back.type, TransactionType.expense);
      expect(t.toMap()['year'], 2026);
      expect(t.toMap()['month'], 5);
    });

    test('household members and roles', () {
      final h = household();
      final back = Household.fromMap('h', h.toMap());
      expect(back.roleOf('u1'), MemberRole.owner);
      expect(back.roleOf('u2'), MemberRole.adult);
      expect(back.roleOf('stranger'), MemberRole.child);
      expect(back.isShared, isTrue);
      expect(back.sortedMembers.first.uid, 'u1');
    });

    test('parse helpers tolerate odd input', () {
      expect(parseDouble('12.5'), 12.5);
      expect(parseDouble(null, 3), 3);
      expect(parseInt('7'), 7);
      expect(parseBool('true'), isTrue);
      expect(parseDate(1700000000000), DateTime.fromMillisecondsSinceEpoch(1700000000000));
      expect(roundMoney(0.1 + 0.2), 0.3);
    });

    test('goal maths', () {
      final g = Goal(id: 'g', name: 'Trip', targetAmount: 12000, savedAmount: 3000, deadline: DateTime(2027, 5, 1), createdBy: 'u1', createdAt: now);
      expect(g.progress, 0.25);
      expect(g.remaining, 9000);
      expect(g.monthlyNeeded(DateTime(2026, 11, 15)), 1500);
    });
  });
}
