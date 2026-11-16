import 'package:expense_budget_manager/features/reports/csv_service.dart';
import 'package:expense_budget_manager/models/models.dart';
import 'package:flutter_test/flutter_test.dart';

import 'helpers.dart';

void main() {
  test('export then parse round-trips headers and rows', () {
    final txs = [
      tx(id: '1', amount: 500, date: DateTime(2026, 11, 2, 10, 30), categoryId: 'food', payee: 'Cafe, "The" Best'),
      tx(id: '2', type: TransactionType.income, amount: 50000, date: DateTime(2026, 11, 1), categoryId: 'salary'),
    ];
    final csv = CsvService.export(
      txs,
      categories: {'food': cat('food', 'Food'), 'salary': cat('salary', 'Salary', kind: CategoryKind.income)},
      accounts: {'cash': acc('cash')},
      household: household(),
    );
    final parsed = CsvService.parse(csv);
    expect(parsed.headers, CsvService.exportHeaders);
    expect(parsed.rows.length, 2);
    expect(parsed.rows[1][6], 'Cafe, "The" Best');
    final map = CsvService.guessMapping(parsed.headers);
    expect(map.date, 0);
    expect(map.amount, 3);
    expect(map.description, isNotNull);
    final result = CsvService.toDrafts(parsed, map);
    expect(result.drafts.length, 2);
    expect(result.drafts[0].type, TransactionType.income);
    // The explicit type column wins over the unsigned amount.
    expect(result.drafts[1].type, TransactionType.expense);
    expect(result.drafts[1].amount, 500);
  });

  test('bank statement with debit/credit columns and dd/mm/yyyy dates', () {
    const raw = '﻿Txn Date;Narration;Withdrawal Amt;Deposit Amt;Balance\n'
        '03/11/2026;UPI-SWIGGY;"1.250,00";;45.000,00\n'
        '04/11/2026;SALARY NOV;;"50.000,00";95.000,00\n'
        'garbage line;;;;\n';
    final parsed = CsvService.parse(raw);
    expect(parsed.headers.first, 'Txn Date');
    final map = CsvService.guessMapping(parsed.headers);
    expect(map.debit, 2);
    expect(map.credit, 3);
    expect(map.description, 1);
    final result = CsvService.toDrafts(parsed, map);
    expect(result.drafts.length, 2);
    expect(result.drafts[0].amount, 1250);
    expect(result.drafts[0].type, TransactionType.expense);
    expect(result.drafts[0].date, DateTime(2026, 11, 3));
    expect(result.drafts[1].amount, 50000);
    expect(result.drafts[1].type, TransactionType.income);
    expect(result.skipped, [4]);
  });

  test('amount and date parsing edge cases', () {
    expect(CsvService.parseAmount('₹1,234.56'), 1234.56);
    expect(CsvService.parseAmount('(200.00)'), -200);
    expect(CsvService.parseAmount('-75'), -75);
    expect(CsvService.parseAmount('1.234,56'), 1234.56);
    expect(CsvService.parseAmount(''), isNull);
    expect(CsvService.parseDate('2026-11-03'), DateTime(2026, 11, 3));
    expect(CsvService.parseDate('3-Nov-2026'), DateTime(2026, 11, 3));
    expect(CsvService.parseDate('03.11.26'), DateTime(2026, 11, 3));
    expect(CsvService.parseDate('nonsense'), isNull);
  });
}
