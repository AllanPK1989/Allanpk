import 'dart:typed_data';

import 'package:excel/excel.dart';

import '../../core/utils/date_utils.dart';
import '../../models/models.dart';
import '../analytics/analytics_engine.dart';
import 'pdf_report.dart';

/// Builds a multi-sheet .xlsx workbook: Summary, Transactions, Categories,
/// Budgets, Accounts and (for families) Members.
class ExcelReportBuilder {
  ExcelReportBuilder(this.data);

  final ReportData data;

  Uint8List build() {
    final excel = Excel.createExcel();
    final defaultSheet = excel.getDefaultSheet();

    _summarySheet(excel['Summary']);
    _transactionsSheet(excel['Transactions']);
    _categoriesSheet(excel['Categories']);
    if (data.budgets.isNotEmpty) _budgetsSheet(excel['Budgets']);
    _accountsSheet(excel['Accounts']);
    if (data.household.isShared) _membersSheet(excel['Members']);

    if (defaultSheet != null && defaultSheet != 'Summary') excel.delete(defaultSheet);
    excel.setDefaultSheet('Summary');
    final bytes = excel.encode();
    if (bytes == null) throw StateError('Could not encode workbook');
    return Uint8List.fromList(bytes);
  }

  CellStyle get _header => CellStyle(
        bold: true,
        backgroundColorHex: ExcelColor.fromHexString('#4F46E5'),
        fontColorHex: ExcelColor.white,
        horizontalAlign: HorizontalAlign.Left,
      );

  CellStyle get _title => CellStyle(bold: true, fontSize: 14);

  CellStyle get _money => CellStyle(numberFormat: NumFormat.custom(formatCode: '#,##0.00'));

  void _headerRow(Sheet sheet, List<String> headers) {
    sheet.appendRow([for (final h in headers) TextCellValue(h)]);
    final rowIndex = sheet.maxRows - 1;
    for (var c = 0; c < headers.length; c++) {
      sheet.cell(CellIndex.indexByColumnRow(columnIndex: c, rowIndex: rowIndex)).cellStyle = _header;
    }
  }

  void _summarySheet(Sheet sheet) {
    final s = AnalyticsEngine.summarize(data.transactions, data.range);
    final prev = AnalyticsEngine.summarize(data.allTransactions, data.range.previous());
    sheet.appendRow([TextCellValue('Expense & Budget Report')]);
    sheet.cell(CellIndex.indexByColumnRow(columnIndex: 0, rowIndex: 0)).cellStyle = _title;
    sheet.appendRow([TextCellValue('Household'), TextCellValue(data.household.name)]);
    sheet.appendRow([TextCellValue('Period'), TextCellValue(data.range.label())]);
    sheet.appendRow([TextCellValue('Currency'), TextCellValue(data.currency)]);
    sheet.appendRow([TextCellValue('Prepared by'), TextCellValue(data.preparedBy)]);
    sheet.appendRow([TextCellValue('Generated'), TextCellValue(DateTime.now().toIso8601String().substring(0, 16))]);
    sheet.appendRow([]);
    _headerRow(sheet, ['Metric', 'This period', 'Previous period', 'Change']);
    void metric(String label, double cur, double p) {
      final change = p == 0 ? null : (cur - p) / p;
      sheet.appendRow([
        TextCellValue(label),
        DoubleCellValue(cur),
        DoubleCellValue(p),
        change == null ? TextCellValue('') : TextCellValue('${(change * 100).toStringAsFixed(1)}%'),
      ]);
      final r = sheet.maxRows - 1;
      sheet.cell(CellIndex.indexByColumnRow(columnIndex: 1, rowIndex: r)).cellStyle = _money;
      sheet.cell(CellIndex.indexByColumnRow(columnIndex: 2, rowIndex: r)).cellStyle = _money;
    }

    metric('Income', s.income, prev.income);
    metric('Expenses', s.expense, prev.expense);
    metric('Net', s.net, prev.net);
    sheet.appendRow([TextCellValue('Savings rate'), TextCellValue('${(s.savingsRate * 100).toStringAsFixed(1)}%'), TextCellValue('${(prev.savingsRate * 100).toStringAsFixed(1)}%')]);
    sheet.appendRow([TextCellValue('Transactions'), IntCellValue(s.transactionCount), IntCellValue(prev.transactionCount)]);
    sheet.appendRow([TextCellValue('Average daily spend'), DoubleCellValue(s.averageDailySpend), DoubleCellValue(prev.averageDailySpend)]);
    sheet.appendRow([]);

    final insights = AnalyticsEngine.insights(
      txs: data.allTransactions,
      range: data.range,
      categories: data.categories,
      budgets: data.budgets,
      money: (v) => '${data.currency} ${v.toStringAsFixed(0)}',
    );
    _headerRow(sheet, ['Observation', 'Detail']);
    for (final i in insights) {
      sheet.appendRow([TextCellValue(i.title), TextCellValue(i.body)]);
    }
    sheet.setColumnWidth(0, 28);
    sheet.setColumnWidth(1, 60);
    sheet.setColumnWidth(2, 18);
  }

  void _transactionsSheet(Sheet sheet) {
    _headerRow(sheet, [
      'Date',
      'Time',
      'Type',
      'Category',
      'Sub-category of',
      'Payee',
      'Note',
      'Account',
      'To account',
      'Amount (${data.currency})',
      'Original amount',
      'Currency',
      'Tags',
      'Member',
      'Private',
      'Receipts',
      'ID',
    ]);
    // Oldest first reads better in a spreadsheet.
    final txs = List.of(data.transactions)..sort((a, b) => a.date.compareTo(b.date));
    for (final t in txs) {
      final cat = data.categories[t.categoryId];
      final parent = cat?.parentId == null ? null : data.categories[cat!.parentId];
      sheet.appendRow([
        DateCellValue(year: t.date.year, month: t.date.month, day: t.date.day),
        TextCellValue(AppDates.time.format(t.date)),
        TextCellValue(t.type.label),
        TextCellValue(cat?.name ?? (t.isTransfer ? 'Transfer' : 'Uncategorised')),
        TextCellValue(parent?.name ?? ''),
        TextCellValue(t.payee),
        TextCellValue(t.note),
        TextCellValue(data.accounts[t.accountId]?.name ?? ''),
        TextCellValue(t.toAccountId == null ? '' : data.accounts[t.toAccountId]?.name ?? ''),
        DoubleCellValue(t.isExpense ? -t.amount : t.amount),
        DoubleCellValue(t.originalAmount),
        TextCellValue(t.currency),
        TextCellValue(t.tags.join(', ')),
        TextCellValue(data.household.members[t.createdBy]?.name ?? t.createdByName),
        TextCellValue(t.isPrivate ? 'Yes' : 'No'),
        IntCellValue(t.receiptUrls.length),
        TextCellValue(t.id),
      ]);
      sheet.cell(CellIndex.indexByColumnRow(columnIndex: 9, rowIndex: sheet.maxRows - 1)).cellStyle = _money;
    }
    sheet.setColumnWidth(0, 12);
    sheet.setColumnWidth(3, 20);
    sheet.setColumnWidth(5, 24);
    sheet.setColumnWidth(6, 30);
    sheet.setColumnWidth(7, 18);
  }

  void _categoriesSheet(Sheet sheet) {
    for (final type in [TransactionType.expense, TransactionType.income]) {
      final slices = AnalyticsEngine.byCategory(data.transactions, data.categories, type: type);
      final prev = {
        for (final s in AnalyticsEngine.byCategory(data.allTransactions, data.categories, type: type, range: data.range.previous()))
          s.categoryId: s.amount,
      };
      sheet.appendRow([TextCellValue(type == TransactionType.expense ? 'Expenses by category' : 'Income by category')]);
      sheet.cell(CellIndex.indexByColumnRow(columnIndex: 0, rowIndex: sheet.maxRows - 1)).cellStyle = _title;
      _headerRow(sheet, ['Category', 'Transactions', 'Amount', 'Share', 'Previous period', 'Change']);
      for (final s in slices) {
        final p = prev[s.categoryId] ?? 0;
        sheet.appendRow([
          TextCellValue(s.name),
          IntCellValue(s.count),
          DoubleCellValue(s.amount),
          TextCellValue('${(s.share * 100).toStringAsFixed(1)}%'),
          DoubleCellValue(p),
          TextCellValue(p == 0 ? '' : '${((s.amount - p) / p * 100).toStringAsFixed(1)}%'),
        ]);
      }
      sheet.appendRow([]);
    }
    sheet.setColumnWidth(0, 24);
  }

  void _budgetsSheet(Sheet sheet) {
    _headerRow(sheet, ['Budget', 'Period', 'Window', 'Limit', 'Spent', 'Remaining', 'Used', 'Status', 'Categories', 'Rollover']);
    for (final b in data.budgets) {
      sheet.appendRow([
        TextCellValue(b.budget.name),
        TextCellValue(b.budget.period.label),
        TextCellValue(b.range.label()),
        DoubleCellValue(b.limit),
        DoubleCellValue(b.spent),
        DoubleCellValue(b.remaining),
        TextCellValue('${(b.limit == 0 ? 0 : b.spent / b.limit * 100).toStringAsFixed(0)}%'),
        TextCellValue(b.status.name),
        TextCellValue(b.budget.categoryIds.isEmpty ? 'All' : b.budget.categoryIds.map((id) => data.categories[id]?.name ?? id).join(', ')),
        TextCellValue(b.budget.rollover ? 'Yes' : 'No'),
      ]);
    }
    sheet.setColumnWidth(0, 24);
    sheet.setColumnWidth(2, 22);
    sheet.setColumnWidth(8, 30);
  }

  void _accountsSheet(Sheet sheet) {
    final balances = AnalyticsEngine.balances(data.accounts.values, data.allTransactions, asOf: data.range.end);
    _headerRow(sheet, ['Account', 'Type', 'Opening balance', 'Balance at period end', 'Transactions', 'Shared', 'Archived']);
    for (final b in balances) {
      sheet.appendRow([
        TextCellValue(b.account.name),
        TextCellValue(b.account.type.label),
        DoubleCellValue(b.account.initialBalance),
        DoubleCellValue(b.balance),
        IntCellValue(b.transactionCount),
        TextCellValue(b.account.isShared ? 'Yes' : 'No'),
        TextCellValue(b.account.isArchived ? 'Yes' : 'No'),
      ]);
    }
    sheet.setColumnWidth(0, 24);
  }

  void _membersSheet(Sheet sheet) {
    final members = AnalyticsEngine.byMember(data.transactions, data.household);
    _headerRow(sheet, ['Member', 'Role', 'Expenses', 'Income', 'Transactions']);
    for (final m in members) {
      sheet.appendRow([
        TextCellValue(m.name),
        TextCellValue(data.household.members[m.uid]?.role.label ?? ''),
        DoubleCellValue(m.expense),
        DoubleCellValue(m.income),
        IntCellValue(m.count),
      ]);
    }
    sheet.setColumnWidth(0, 24);
  }
}
