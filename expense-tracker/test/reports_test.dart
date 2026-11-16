import 'package:excel/excel.dart';
import 'package:expense_budget_manager/core/utils/date_utils.dart';
import 'package:expense_budget_manager/features/analytics/analytics_engine.dart';
import 'package:expense_budget_manager/features/reports/excel_report.dart';
import 'package:expense_budget_manager/features/reports/pdf_report.dart';
import 'package:expense_budget_manager/models/models.dart';
import 'package:flutter_test/flutter_test.dart';

import 'helpers.dart';

ReportData sampleData({bool shared = true}) {
  final range = DateRange.month(now);
  final categories = {
    'food': cat('food', 'Food'),
    'rent': cat('rent', 'Rent'),
    'salary': cat('salary', 'Salary', kind: CategoryKind.income),
  };
  final accounts = {'cash': acc('cash', initial: 1000), 'bank': acc('bank', type: AccountType.bank)};
  final all = [
    tx(id: '1', amount: 500, date: DateTime(2026, 11, 2), categoryId: 'food', payee: 'Cafe'),
    tx(id: '2', amount: 15000, date: DateTime(2026, 11, 1), categoryId: 'rent', payee: 'Landlord', createdBy: 'u2'),
    tx(id: '3', type: TransactionType.income, amount: 50000, date: DateTime(2026, 11, 1), categoryId: 'salary'),
    tx(id: '4', type: TransactionType.transfer, amount: 2000, date: DateTime(2026, 11, 3), toAccountId: 'bank'),
    tx(id: '5', amount: 300, date: DateTime(2026, 10, 12), categoryId: 'food'),
  ];
  final budget = Budget(
    id: 'b',
    name: 'Food',
    amount: 400,
    period: BudgetPeriod.monthly,
    startDate: DateTime(2026, 1, 1),
    categoryIds: const ['food'],
    createdBy: 'u1',
    createdAt: now,
  );
  return ReportData(
    household: household(members: shared ? const ['u1', 'u2'] : const ['u1']),
    range: range,
    transactions: AnalyticsEngine.inRange(all, range),
    allTransactions: all,
    categories: categories,
    accounts: accounts,
    budgets: [AnalyticsEngine.budgetProgress(budget, all, now, categories: categories)],
    preparedBy: 'Tester',
  );
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  test('Excel workbook has every sheet with data rows', () {
    final bytes = ExcelReportBuilder(sampleData()).build();
    expect(bytes.sublist(0, 2), [0x50, 0x4B]); // "PK" zip signature
    final book = Excel.decodeBytes(bytes);
    expect(book.tables.keys, containsAll(['Summary', 'Transactions', 'Categories', 'Budgets', 'Accounts', 'Members']));
    expect(book.tables.keys, isNot(contains('Sheet1')));
    // Header + 4 in-range transactions.
    final tx = book.tables['Transactions']!;
    expect(tx.maxRows, 5);
    expect(tx.row(0)[9]?.value.toString(), 'Amount (INR)');
  });

  test('Excel workbook for a single-member household skips Members', () {
    final book = Excel.decodeBytes(ExcelReportBuilder(sampleData(shared: false)).build());
    expect(book.tables.keys, isNot(contains('Members')));
  });

  test('PDF report renders', () async {
    final bytes = await PdfReportBuilder(sampleData()).build();
    expect(String.fromCharCodes(bytes.sublist(0, 4)), '%PDF');
    expect(bytes.length, greaterThan(5000));
  });
}
