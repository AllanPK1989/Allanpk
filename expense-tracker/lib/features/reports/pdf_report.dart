import 'dart:typed_data';

import 'package:flutter/services.dart' show rootBundle;
import 'package:intl/intl.dart';
import 'package:pdf/pdf.dart';
import 'package:pdf/widgets.dart' as pw;

import '../../core/utils/date_utils.dart';
import '../../core/utils/money.dart';
import '../../models/models.dart';
import '../analytics/analytics_engine.dart';

/// Everything the PDF needs, pre-computed by the caller.
class ReportData {
  const ReportData({
    required this.household,
    required this.range,
    required this.transactions,
    required this.allTransactions,
    required this.categories,
    required this.accounts,
    required this.budgets,
    required this.preparedBy,
    this.includeTransactions = true,
    this.includeBudgets = true,
    this.includeMembers = true,
    this.includeAccounts = true,
  });

  final Household household;
  final DateRange range;

  /// Transactions inside [range].
  final List<Transaction> transactions;

  /// Full history, for balances and comparisons.
  final List<Transaction> allTransactions;
  final Map<String, Category> categories;
  final Map<String, Account> accounts;
  final List<BudgetProgress> budgets;
  final String preparedBy;
  final bool includeTransactions;
  final bool includeBudgets;
  final bool includeMembers;
  final bool includeAccounts;

  String get currency => household.baseCurrency;
}

/// Builds a multi-page, chart-rich PDF report.
class PdfReportBuilder {
  PdfReportBuilder(this.data);

  final ReportData data;

  static const _ink = PdfColor.fromInt(0xFF111827);
  static const _muted = PdfColor.fromInt(0xFF6B7280);
  static const _line = PdfColor.fromInt(0xFFE5E7EB);
  static const _soft = PdfColor.fromInt(0xFFF3F4F6);
  static const _income = PdfColor.fromInt(0xFF16A34A);
  static const _expense = PdfColor.fromInt(0xFFDC2626);
  static const _primary = PdfColor.fromInt(0xFF4F46E5);

  String _m(double v, {bool compact = false}) => Money.format(v, data.currency, compact: compact);

  Future<Uint8List> build() async {
    final fontData = await rootBundle.load('assets/fonts/Inter.ttf');
    final font = pw.Font.ttf(fontData);
    final theme = pw.ThemeData.withFont(base: font, bold: font, italic: font, boldItalic: font).copyWith(
      defaultTextStyle: pw.TextStyle(font: font, fontSize: 10, color: _ink),
    );
    final doc = pw.Document(
      title: 'Expense report ${data.range.label()}',
      author: data.preparedBy,
      creator: 'Expense & Budget Manager',
      theme: theme,
    );

    final summary = AnalyticsEngine.summarize(data.transactions, data.range);
    final previous = AnalyticsEngine.summarize(data.allTransactions, data.range.previous());
    final cats = AnalyticsEngine.byCategory(data.transactions, data.categories);
    final incomeCats = AnalyticsEngine.byCategory(data.transactions, data.categories, type: TransactionType.income);
    final daily = AnalyticsEngine.dailySeries(data.transactions, data.range);
    final members = AnalyticsEngine.byMember(data.transactions, data.household);
    final payees = AnalyticsEngine.topPayees(data.transactions, limit: 8);
    final insights = AnalyticsEngine.insights(
      txs: data.allTransactions,
      range: data.range,
      categories: data.categories,
      budgets: data.budgets,
      money: (v) => _m(v, compact: true),
    );
    final balances = AnalyticsEngine.balances(data.accounts.values, data.allTransactions, asOf: data.range.end);

    doc.addPage(
      pw.MultiPage(
        pageFormat: PdfPageFormat.a4,
        margin: const pw.EdgeInsets.fromLTRB(36, 36, 36, 40),
        header: (ctx) => ctx.pageNumber == 1 ? pw.SizedBox() : _runningHeader(),
        footer: _footer,
        build: (ctx) => [
          _titleBlock(),
          pw.SizedBox(height: 18),
          _summaryRow(summary, previous),
          pw.SizedBox(height: 18),
          if (daily.any((d) => d.expense > 0)) ...[
            _sectionTitle('Daily spending'),
            pw.SizedBox(height: 6),
            _dailyChart(daily),
            pw.SizedBox(height: 18),
          ],
          if (cats.isNotEmpty) ...[
            _sectionTitle('Spending by category'),
            pw.SizedBox(height: 8),
            _categorySection(cats, summary.expense),
            pw.SizedBox(height: 18),
          ],
          if (incomeCats.isNotEmpty) ...[
            _sectionTitle('Income sources'),
            pw.SizedBox(height: 6),
            _simpleTable(
              ['Source', 'Amount', 'Share'],
              [for (final c in incomeCats) [c.name, _m(c.amount), Money.percent(c.share)]],
              aligns: [pw.Alignment.centerLeft, pw.Alignment.centerRight, pw.Alignment.centerRight],
            ),
            pw.SizedBox(height: 18),
          ],
          if (data.includeBudgets && data.budgets.isNotEmpty) ...[
            _sectionTitle('Budgets'),
            pw.SizedBox(height: 6),
            _budgetTable(),
            pw.SizedBox(height: 18),
          ],
          if (data.includeMembers && data.household.isShared && members.isNotEmpty) ...[
            _sectionTitle('By family member'),
            pw.SizedBox(height: 6),
            _simpleTable(
              ['Member', 'Expenses', 'Income', 'Transactions', 'Share of spend'],
              [
                for (final m in members)
                  [
                    m.name,
                    _m(m.expense),
                    _m(m.income),
                    '${m.count}',
                    summary.expense == 0 ? '0%' : Money.percent(m.expense / summary.expense),
                  ],
              ],
              aligns: [
                pw.Alignment.centerLeft,
                pw.Alignment.centerRight,
                pw.Alignment.centerRight,
                pw.Alignment.centerRight,
                pw.Alignment.centerRight,
              ],
            ),
            pw.SizedBox(height: 18),
          ],
          if (payees.isNotEmpty) ...[
            _sectionTitle('Top merchants'),
            pw.SizedBox(height: 6),
            _simpleTable(
              ['Merchant', 'Visits', 'Total'],
              [for (final p in payees) [p.payee, '${p.count}', _m(p.amount)]],
              aligns: [pw.Alignment.centerLeft, pw.Alignment.centerRight, pw.Alignment.centerRight],
            ),
            pw.SizedBox(height: 18),
          ],
          _sectionTitle('Observations'),
          pw.SizedBox(height: 6),
          for (final i in insights) _insightRow(i),
          if (data.includeAccounts && balances.isNotEmpty) ...[
            pw.SizedBox(height: 18),
            _sectionTitle('Account balances at ${AppDates.dayMonthYear.format(data.range.end)}'),
            pw.SizedBox(height: 6),
            _simpleTable(
              ['Account', 'Type', 'Balance'],
              [
                for (final b in balances.where((b) => !b.account.isArchived))
                  [b.account.name, b.account.type.label, _m(b.balance)],
              ],
              aligns: [pw.Alignment.centerLeft, pw.Alignment.centerLeft, pw.Alignment.centerRight],
            ),
          ],
          if (data.includeTransactions && data.transactions.isNotEmpty) ...[
            pw.NewPage(),
            _sectionTitle('Transactions (${data.transactions.length})'),
            pw.SizedBox(height: 6),
            _transactionsTable(),
          ],
        ],
      ),
    );
    return doc.save();
  }

  // ------------------------------------------------------------------ blocks

  pw.Widget _titleBlock() {
    final generated = DateFormat('d MMM yyyy, h:mm a').format(DateTime.now());
    return pw.Container(
      padding: const pw.EdgeInsets.all(18),
      decoration: pw.BoxDecoration(
        gradient: const pw.LinearGradient(
          colors: [PdfColor.fromInt(0xFF4F46E5), PdfColor.fromInt(0xFF7C3AED)],
          begin: pw.Alignment.topLeft,
          end: pw.Alignment.bottomRight,
        ),
        borderRadius: pw.BorderRadius.circular(12),
      ),
      child: pw.Row(
        crossAxisAlignment: pw.CrossAxisAlignment.start,
        children: [
          pw.Expanded(
            child: pw.Column(
              crossAxisAlignment: pw.CrossAxisAlignment.start,
              children: [
                pw.Text('Expense & Budget Report', style: const pw.TextStyle(color: PdfColors.white, fontSize: 20)),
                pw.SizedBox(height: 4),
                pw.Text(data.range.label(), style: const pw.TextStyle(color: PdfColors.white, fontSize: 13)),
                pw.SizedBox(height: 10),
                pw.Text(
                  '${data.household.name} · ${data.household.memberIds.length} ${data.household.memberIds.length == 1 ? 'member' : 'members'} · ${data.currency}',
                  style: const pw.TextStyle(color: PdfColor.fromInt(0xFFE0E7FF), fontSize: 9),
                ),
              ],
            ),
          ),
          pw.Column(
            crossAxisAlignment: pw.CrossAxisAlignment.end,
            children: [
              pw.Text('Prepared by ${data.preparedBy}', style: const pw.TextStyle(color: PdfColor.fromInt(0xFFE0E7FF), fontSize: 9)),
              pw.Text(generated, style: const pw.TextStyle(color: PdfColor.fromInt(0xFFE0E7FF), fontSize: 9)),
            ],
          ),
        ],
      ),
    );
  }

  pw.Widget _runningHeader() => pw.Container(
        padding: const pw.EdgeInsets.only(bottom: 6),
        margin: const pw.EdgeInsets.only(bottom: 10),
        decoration: const pw.BoxDecoration(border: pw.Border(bottom: pw.BorderSide(color: _line))),
        child: pw.Row(
          mainAxisAlignment: pw.MainAxisAlignment.spaceBetween,
          children: [
            pw.Text('${data.household.name} · Expense & Budget Report', style: const pw.TextStyle(color: _muted, fontSize: 8)),
            pw.Text(data.range.label(), style: const pw.TextStyle(color: _muted, fontSize: 8)),
          ],
        ),
      );

  pw.Widget _footer(pw.Context ctx) => pw.Container(
        margin: const pw.EdgeInsets.only(top: 10),
        child: pw.Row(
          mainAxisAlignment: pw.MainAxisAlignment.spaceBetween,
          children: [
            pw.Text('Generated with Expense & Budget Manager', style: const pw.TextStyle(color: _muted, fontSize: 8)),
            pw.Text('Page ${ctx.pageNumber} of ${ctx.pagesCount}', style: const pw.TextStyle(color: _muted, fontSize: 8)),
          ],
        ),
      );

  pw.Widget _sectionTitle(String text) => pw.Text(text, style: const pw.TextStyle(fontSize: 13, color: _ink));

  pw.Widget _summaryRow(PeriodSummary s, PeriodSummary prev) {
    String change(double cur, double p) {
      if (p == 0) return '';
      final pct = (cur - p) / p * 100;
      return '${pct >= 0 ? '+' : ''}${pct.round()}% vs previous';
    }

    pw.Widget card(String label, String value, PdfColor color, String sub) => pw.Expanded(
          child: pw.Container(
            margin: const pw.EdgeInsets.only(right: 8),
            padding: const pw.EdgeInsets.all(10),
            decoration: pw.BoxDecoration(color: _soft, borderRadius: pw.BorderRadius.circular(8)),
            child: pw.Column(
              crossAxisAlignment: pw.CrossAxisAlignment.start,
              children: [
                pw.Text(label, style: const pw.TextStyle(color: _muted, fontSize: 8)),
                pw.SizedBox(height: 3),
                pw.Text(value, style: pw.TextStyle(color: color, fontSize: 13)),
                pw.SizedBox(height: 2),
                pw.Text(sub, style: const pw.TextStyle(color: _muted, fontSize: 7.5)),
              ],
            ),
          ),
        );

    return pw.Row(
      children: [
        card('Income', _m(s.income), _income, change(s.income, prev.income)),
        card('Expenses', _m(s.expense), _expense, change(s.expense, prev.expense)),
        card('Net', _m(s.net), s.net >= 0 ? _income : _expense,
            s.income > 0 ? '${Money.percent(s.savingsRate)} savings rate' : ''),
        card('Avg / day', _m(s.averageDailySpend), _primary, '${s.transactionCount} transactions'),
      ],
    );
  }

  pw.Widget _dailyChart(List<DailyPoint> daily) {
    final maxY = daily.fold<double>(0, (m, p) => p.expense > m ? p.expense : m);
    final step = _niceStep(maxY);
    final yValues = <double>[for (var v = 0.0; v <= maxY + step; v += step) v];
    final xStep = daily.length > 16 ? (daily.length / 8).ceil() : 1;
    final xValues = <double>[for (var i = 0; i < daily.length; i += xStep) i.toDouble()];
    return pw.Container(
      height: 150,
      child: pw.Chart(
        grid: pw.CartesianGrid(
          xAxis: pw.FixedAxis(
            xValues,
            format: (v) {
              final i = v.round();
              return i >= 0 && i < daily.length ? DateFormat('d/M').format(daily[i].date) : '';
            },
            textStyle: const pw.TextStyle(fontSize: 7, color: _muted),
            divisions: false,
          ),
          yAxis: pw.FixedAxis(
            yValues,
            format: (v) => _m(v.toDouble(), compact: true),
            textStyle: const pw.TextStyle(fontSize: 7, color: _muted),
            divisions: true,
            divisionsColor: _line,
          ),
        ),
        datasets: [
          pw.BarDataSet(
            color: _primary,
            width: daily.length > 40 ? 3 : 8,
            borderColor: _primary,
            data: [for (var i = 0; i < daily.length; i++) pw.PointChartValue(i.toDouble(), daily[i].expense)],
          ),
        ],
      ),
    );
  }

  pw.Widget _categorySection(List<CategorySpend> cats, double total) {
    final top = cats.take(8).toList();
    final rest = cats.skip(8).fold<double>(0, (s, c) => s + c.amount);
    return pw.Row(
      crossAxisAlignment: pw.CrossAxisAlignment.start,
      children: [
        pw.SizedBox(
          width: 170,
          height: 170,
          child: pw.Chart(
            grid: pw.PieGrid(),
            datasets: [
              for (final c in top)
                pw.PieDataSet(
                  value: c.amount,
                  color: PdfColor.fromInt(c.color),
                  legend: '${(c.share * 100).round()}%',
                  legendStyle: const pw.TextStyle(fontSize: 7, color: _ink),
                  legendPosition: pw.PieLegendPosition.outside,
                  legendOffset: 10,
                  innerRadius: 28,
                ),
              if (rest > 0)
                pw.PieDataSet(
                  value: rest,
                  color: const PdfColor.fromInt(0xFF9CA3AF),
                  legend: 'Other',
                  legendStyle: const pw.TextStyle(fontSize: 7, color: _ink),
                  legendPosition: pw.PieLegendPosition.outside,
                  innerRadius: 28,
                ),
            ],
          ),
        ),
        pw.SizedBox(width: 14),
        pw.Expanded(
          child: _simpleTable(
            ['Category', 'Transactions', 'Amount', 'Share'],
            [
              for (final c in cats) [c.name, '${c.count}', _m(c.amount), Money.percent(c.share)],
              ['Total', '${cats.fold<int>(0, (s, c) => s + c.count)}', _m(total), '100%'],
            ],
            aligns: [pw.Alignment.centerLeft, pw.Alignment.centerRight, pw.Alignment.centerRight, pw.Alignment.centerRight],
            swatches: [for (final c in cats) PdfColor.fromInt(c.color), null],
          ),
        ),
      ],
    );
  }

  pw.Widget _budgetTable() {
    return _simpleTable(
      ['Budget', 'Period', 'Limit', 'Spent', 'Remaining', 'Status'],
      [
        for (final b in data.budgets)
          [
            b.budget.name,
            b.budget.period.label,
            _m(b.limit),
            _m(b.spent),
            _m(b.remaining),
            switch (b.status) {
              BudgetStatus.onTrack => 'On track',
              BudgetStatus.warning => '${(b.fraction * 100).round()}% used',
              BudgetStatus.over => 'Over by ${_m(b.spent - b.limit, compact: true)}',
            },
          ],
      ],
      aligns: [
        pw.Alignment.centerLeft,
        pw.Alignment.centerLeft,
        pw.Alignment.centerRight,
        pw.Alignment.centerRight,
        pw.Alignment.centerRight,
        pw.Alignment.centerLeft,
      ],
      rowColors: [
        for (final b in data.budgets)
          switch (b.status) {
            BudgetStatus.onTrack => null,
            BudgetStatus.warning => const PdfColor.fromInt(0xFFFEF3C7),
            BudgetStatus.over => const PdfColor.fromInt(0xFFFEE2E2),
          },
      ],
    );
  }

  pw.Widget _insightRow(Insight i) {
    final color = switch (i.tone) {
      InsightTone.positive => _income,
      InsightTone.warning => const PdfColor.fromInt(0xFFF59E0B),
      InsightTone.neutral => _primary,
    };
    return pw.Container(
      margin: const pw.EdgeInsets.only(bottom: 5),
      padding: const pw.EdgeInsets.fromLTRB(10, 7, 10, 7),
      decoration: pw.BoxDecoration(
        color: _soft,
        borderRadius: pw.BorderRadius.circular(6),
        border: pw.Border(left: pw.BorderSide(color: color, width: 3)),
      ),
      child: pw.Column(
        crossAxisAlignment: pw.CrossAxisAlignment.start,
        children: [
          pw.Text(i.title, style: const pw.TextStyle(fontSize: 9.5)),
          pw.SizedBox(height: 1.5),
          pw.Text(i.body, style: const pw.TextStyle(fontSize: 8.5, color: _muted)),
        ],
      ),
    );
  }

  pw.Widget _transactionsTable() {
    final rows = data.transactions.map((t) {
      final cat = data.categories[t.categoryId];
      final acc = data.accounts[t.accountId];
      final sign = t.isIncome ? '+' : (t.isExpense ? '-' : '');
      return [
        AppDates.iso.format(t.date),
        t.type.label,
        t.isTransfer
            ? '${acc?.name ?? ''} → ${data.accounts[t.toAccountId]?.name ?? ''}'
            : (cat?.name ?? 'Uncategorised'),
        t.payee.isNotEmpty ? t.payee : t.note,
        acc?.name ?? '',
        data.household.isShared ? (data.household.members[t.createdBy]?.name ?? t.createdByName) : '',
        '$sign${_m(t.amount)}',
      ];
    }).toList();
    final headers = ['Date', 'Type', 'Category', 'Payee / note', 'Account', if (data.household.isShared) 'Member', 'Amount'];
    if (!data.household.isShared) {
      for (final r in rows) {
        r.removeAt(5);
      }
    }
    return pw.TableHelper.fromTextArray(
      headers: headers,
      data: rows,
      headerStyle: const pw.TextStyle(fontSize: 8, color: PdfColors.white),
      headerDecoration: const pw.BoxDecoration(color: _primary),
      cellStyle: const pw.TextStyle(fontSize: 7.5),
      cellHeight: 16,
      cellPadding: const pw.EdgeInsets.symmetric(horizontal: 4, vertical: 2),
      oddRowDecoration: const pw.BoxDecoration(color: _soft),
      border: null,
      cellAlignments: {headers.length - 1: pw.Alignment.centerRight},
      columnWidths: {
        0: const pw.FixedColumnWidth(52),
        1: const pw.FixedColumnWidth(42),
        headers.length - 1: const pw.FixedColumnWidth(70),
      },
    );
  }

  pw.Widget _simpleTable(
    List<String> headers,
    List<List<String>> rows, {
    required List<pw.Alignment> aligns,
    List<PdfColor?>? swatches,
    List<PdfColor?>? rowColors,
  }) {
    pw.Widget cell(String text, pw.Alignment align, {bool header = false, PdfColor? swatch}) => pw.Container(
          padding: const pw.EdgeInsets.symmetric(horizontal: 6, vertical: 4),
          alignment: align,
          child: pw.Row(
            mainAxisSize: pw.MainAxisSize.min,
            children: [
              if (swatch != null) ...[
                pw.Container(width: 7, height: 7, decoration: pw.BoxDecoration(color: swatch, borderRadius: pw.BorderRadius.circular(2))),
                pw.SizedBox(width: 4),
              ],
              pw.Text(
                text,
                style: pw.TextStyle(fontSize: header ? 8 : 8.5, color: header ? PdfColors.white : _ink),
                maxLines: 1,
                overflow: pw.TextOverflow.clip,
              ),
            ],
          ),
        );
    return pw.Table(
      border: const pw.TableBorder(horizontalInside: pw.BorderSide(color: _line, width: 0.5)),
      children: [
        pw.TableRow(
          decoration: const pw.BoxDecoration(color: _primary),
          children: [for (var i = 0; i < headers.length; i++) cell(headers[i], aligns[i], header: true)],
        ),
        for (var r = 0; r < rows.length; r++)
          pw.TableRow(
            decoration: pw.BoxDecoration(color: rowColors != null && r < rowColors.length ? rowColors[r] : (r.isOdd ? _soft : null)),
            children: [
              for (var i = 0; i < rows[r].length; i++)
                cell(rows[r][i], aligns[i], swatch: i == 0 && swatches != null && r < swatches.length ? swatches[r] : null),
            ],
          ),
      ],
    );
  }

  static double _niceStep(double maxY) {
    if (maxY <= 0) return 100;
    final raw = maxY / 4;
    final magnitude = _pow10(raw.floor().toString().length - 1);
    final normalized = raw / magnitude;
    final double nice = normalized <= 1 ? 1 : normalized <= 2 ? 2 : normalized <= 5 ? 5 : 10;
    return nice * magnitude;
  }

  static double _pow10(int exp) {
    var v = 1.0;
    for (var i = 0; i < exp; i++) {
      v *= 10;
    }
    return v;
  }
}
