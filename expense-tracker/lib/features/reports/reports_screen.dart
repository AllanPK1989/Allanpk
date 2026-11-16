import 'dart:convert';
import 'dart:typed_data';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:material_ui/material_ui.dart';
import 'package:printing/printing.dart';

import '../../core/utils/date_utils.dart';
import '../../core/utils/extensions.dart';
import '../../core/utils/money.dart';
import '../../core/widgets/widgets.dart';
import '../../services/platform/file_saver.dart';
import '../analytics/analytics_engine.dart';
import '../household/household_providers.dart';
import 'csv_service.dart';
import 'excel_report.dart';
import 'pdf_report.dart';

/// Choose a period and export it as PDF, Excel or CSV.
class ReportsScreen extends ConsumerStatefulWidget {
  const ReportsScreen({super.key});

  @override
  ConsumerState<ReportsScreen> createState() => _ReportsScreenState();
}

class _ReportsScreenState extends ConsumerState<ReportsScreen> {
  late DateRange _range = ref.read(selectedPeriodProvider);
  bool _includeTransactions = true;
  bool _includeBudgets = true;
  bool _includeMembers = true;
  bool _includeAccounts = true;
  String? _busy;

  ReportData? _buildData() {
    final household = ref.read(activeHouseholdProvider).value;
    final profile = ref.read(userProfileProvider).value;
    if (household == null || profile == null) return null;
    final all = ref.read(allTransactionsProvider).value ?? const [];
    final categories = ref.read(categoryMapProvider);
    final startDay = household.monthStartDay;
    final budgets = (ref.read(budgetsProvider).value ?? const [])
        .where((b) => !b.isArchived)
        .map((b) => AnalyticsEngine.budgetProgress(b, all, _range.end, monthStartDay: startDay, categories: categories))
        .toList();
    return ReportData(
      household: household,
      range: _range,
      transactions: AnalyticsEngine.inRange(all, _range),
      allTransactions: all,
      categories: categories,
      accounts: ref.read(accountMapProvider),
      budgets: budgets,
      preparedBy: profile.displayName,
      includeTransactions: _includeTransactions,
      includeBudgets: _includeBudgets,
      includeMembers: _includeMembers,
      includeAccounts: _includeAccounts,
    );
  }

  String get _stamp => '${AppDates.iso.format(_range.start)}_${AppDates.iso.format(_range.end)}';

  Future<void> _run(String label, Future<void> Function(ReportData) action) async {
    final data = _buildData();
    if (data == null) return;
    setState(() => _busy = label);
    try {
      await action(data);
    } catch (e) {
      if (mounted) context.showSnack('Export failed: $e', error: true);
    } finally {
      if (mounted) setState(() => _busy = null);
    }
  }

  Future<void> _downloadPdf() => _run('pdf', (data) async {
        final bytes = await PdfReportBuilder(data).build();
        await saveFile(bytes: bytes, filename: 'expense-report_$_stamp.pdf', mimeType: 'application/pdf');
        if (mounted) context.showSnack('PDF ready');
      });

  Future<void> _printPdf() => _run('print', (data) async {
        await Printing.layoutPdf(
          onLayout: (_) => PdfReportBuilder(data).build(),
          name: 'expense-report_$_stamp',
        );
      });

  Future<void> _previewPdf() => _run('preview', (data) async {
        final bytes = await PdfReportBuilder(data).build();
        if (!mounted) return;
        await Navigator.of(context).push(
          MaterialPageRoute<void>(builder: (_) => PdfPreviewScreen(bytes: bytes, filename: 'expense-report_$_stamp.pdf')),
        );
      });

  Future<void> _downloadExcel() => _run('xlsx', (data) async {
        final bytes = ExcelReportBuilder(data).build();
        await saveFile(
          bytes: bytes,
          filename: 'expense-report_$_stamp.xlsx',
          mimeType: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        );
        if (mounted) context.showSnack('Excel workbook ready');
      });

  Future<void> _downloadCsv() => _run('csv', (data) async {
        final csv = CsvService.export(
          data.transactions,
          categories: data.categories,
          accounts: data.accounts,
          household: data.household,
        );
        await saveFile(
          bytes: Uint8List.fromList(utf8.encode('﻿$csv')),
          filename: 'transactions_$_stamp.csv',
          mimeType: 'text/csv',
        );
        if (mounted) context.showSnack('CSV ready');
      });

  @override
  Widget build(BuildContext context) {
    final all = ref.watch(allTransactionsProvider).value ?? const [];
    final currency = ref.watch(baseCurrencyProvider);
    final household = ref.watch(activeHouseholdProvider).value;
    final inRange = AnalyticsEngine.inRange(all, _range);
    final summary = AnalyticsEngine.summarize(inRange, _range);
    final now = DateTime.now();

    return Scaffold(
      appBar: AppBar(title: const Text('Reports')),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(16, 4, 16, 40),
        children: [
          const SectionHeader(title: 'Period'),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              _chip('This month', DateRange.month(now, startDay: household?.monthStartDay ?? 1)),
              _chip('Last month', DateRange.month(AppDates.addMonths(now, -1), startDay: household?.monthStartDay ?? 1)),
              _chip('This quarter', DateRange.quarter(now)),
              _chip('Last 90 days', DateRange.lastDays(90)),
              _chip('This year', DateRange.year(now)),
              _chip('Last year', DateRange.year(DateTime(now.year - 1))),
              ActionChip(
                avatar: const Icon(Icons.date_range_rounded, size: 16),
                label: const Text('Custom…'),
                onPressed: () async {
                  final picked = await showDateRangePicker(
                    context: context,
                    firstDate: DateTime(2000),
                    lastDate: DateTime(2100),
                    initialDateRange: DateTimeRange(start: _range.start, end: _range.end),
                  );
                  if (picked != null) setState(() => _range = DateRange.custom(picked.start, picked.end));
                },
              ),
            ],
          ),
          const SizedBox(height: 14),
          AppCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(_range.label(), style: context.text.titleMedium),
                const SizedBox(height: 4),
                Text(
                  '${inRange.length} transactions · income ${Money.format(summary.income, currency, compact: true)} · '
                  'expenses ${Money.format(summary.expense, currency, compact: true)} · net ${Money.format(summary.net, currency, compact: true)}',
                  style: context.text.bodySmall?.copyWith(color: context.colors.onSurfaceVariant),
                ),
              ],
            ),
          ),
          const SectionHeader(title: 'Include in PDF / Excel'),
          AppCard(
            padding: const EdgeInsets.symmetric(vertical: 4),
            child: Column(
              children: [
                SwitchListTile(title: const Text('Transaction list'), value: _includeTransactions, onChanged: (v) => setState(() => _includeTransactions = v)),
                SwitchListTile(title: const Text('Budgets'), value: _includeBudgets, onChanged: (v) => setState(() => _includeBudgets = v)),
                if (household != null && household.isShared)
                  SwitchListTile(title: const Text('Family member breakdown'), value: _includeMembers, onChanged: (v) => setState(() => _includeMembers = v)),
                SwitchListTile(title: const Text('Account balances'), value: _includeAccounts, onChanged: (v) => setState(() => _includeAccounts = v)),
              ],
            ),
          ),
          const SectionHeader(title: 'Export'),
          _ExportTile(
            icon: Icons.picture_as_pdf_rounded,
            color: const Color(0xFFE53935),
            title: 'PDF report',
            subtitle: 'Summary, charts, category and budget tables, insights, transactions',
            busy: _busy == 'pdf' || _busy == 'preview' || _busy == 'print',
            actions: [
              TextButton.icon(onPressed: _busy != null || inRange.isEmpty ? null : _previewPdf, icon: const Icon(Icons.visibility_outlined, size: 18), label: const Text('Preview')),
              TextButton.icon(onPressed: _busy != null || inRange.isEmpty ? null : _printPdf, icon: const Icon(Icons.print_outlined, size: 18), label: const Text('Print')),
              FilledButton.tonalIcon(
                style: FilledButton.styleFrom(minimumSize: const Size(0, 40)),
                onPressed: _busy != null || inRange.isEmpty ? null : _downloadPdf,
                icon: const Icon(Icons.download_rounded, size: 18),
                label: const Text('Download'),
              ),
            ],
          ),
          const SizedBox(height: 10),
          _ExportTile(
            icon: Icons.table_chart_rounded,
            color: const Color(0xFF1D6F42),
            title: 'Excel workbook (.xlsx)',
            subtitle: 'Summary, Transactions, Categories, Budgets, Accounts and Members sheets',
            busy: _busy == 'xlsx',
            actions: [
              FilledButton.tonalIcon(
                style: FilledButton.styleFrom(minimumSize: const Size(0, 40)),
                onPressed: _busy != null || inRange.isEmpty ? null : _downloadExcel,
                icon: const Icon(Icons.download_rounded, size: 18),
                label: const Text('Download'),
              ),
            ],
          ),
          const SizedBox(height: 10),
          _ExportTile(
            icon: Icons.description_rounded,
            color: const Color(0xFF546E7A),
            title: 'CSV (transactions only)',
            subtitle: 'Plain text, opens anywhere. Re-importable into this app.',
            busy: _busy == 'csv',
            actions: [
              FilledButton.tonalIcon(
                style: FilledButton.styleFrom(minimumSize: const Size(0, 40)),
                onPressed: _busy != null || inRange.isEmpty ? null : _downloadCsv,
                icon: const Icon(Icons.download_rounded, size: 18),
                label: const Text('Download'),
              ),
            ],
          ),
          const SectionHeader(title: 'Import'),
          AppCard(
            onTap: () => context.push('/reports/import'),
            child: Row(
              children: [
                IconBadge(iconKey: null, icon: Icons.upload_file_rounded, color: const Color(0xFF43A047).argb, size: 44),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('Import from CSV', style: context.text.titleSmall),
                      Text('Bank statements or exports from other apps', style: context.text.bodySmall?.copyWith(color: context.colors.onSurfaceVariant)),
                    ],
                  ),
                ),
                const Icon(Icons.chevron_right_rounded),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _chip(String label, DateRange range) => ChoiceChip(
        label: Text(label),
        selected: _range == range,
        onSelected: (_) => setState(() => _range = range),
      );
}

class _ExportTile extends StatelessWidget {
  const _ExportTile({
    required this.icon,
    required this.color,
    required this.title,
    required this.subtitle,
    required this.actions,
    required this.busy,
  });

  final IconData icon;
  final Color color;
  final String title;
  final String subtitle;
  final List<Widget> actions;
  final bool busy;

  @override
  Widget build(BuildContext context) {
    return AppCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              IconBadge(iconKey: null, icon: icon, color: color.argb, size: 44),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(title, style: context.text.titleSmall),
                    Text(subtitle, style: context.text.bodySmall?.copyWith(color: context.colors.onSurfaceVariant)),
                  ],
                ),
              ),
              if (busy) const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2)),
            ],
          ),
          const SizedBox(height: 10),
          Wrap(alignment: WrapAlignment.end, spacing: 6, runSpacing: 6, children: actions),
        ],
      ),
    );
  }
}

/// Renders PDF pages as images so users can check the report before saving.
class PdfPreviewScreen extends StatelessWidget {
  const PdfPreviewScreen({super.key, required this.bytes, required this.filename});
  final Uint8List bytes;
  final String filename;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Report preview'),
        actions: [
          IconButton(
            tooltip: 'Print',
            icon: const Icon(Icons.print_outlined),
            onPressed: () => Printing.layoutPdf(onLayout: (_) async => bytes, name: filename),
          ),
          IconButton(
            tooltip: 'Download',
            icon: const Icon(Icons.download_rounded),
            onPressed: () => saveFile(bytes: bytes, filename: filename, mimeType: 'application/pdf'),
          ),
          const SizedBox(width: 4),
        ],
      ),
      backgroundColor: context.colors.surfaceContainerHighest,
      body: FutureBuilder<List<Uint8List>>(
        future: _raster(),
        builder: (context, snap) {
          if (snap.connectionState != ConnectionState.done) return const LoadingState();
          final pages = snap.data ?? const [];
          if (pages.isEmpty) {
            return EmptyState(
              icon: Icons.picture_as_pdf_outlined,
              title: 'Preview unavailable in this browser',
              message: 'Download or print the PDF instead.',
              actionLabel: 'Download',
              onAction: () => saveFile(bytes: bytes, filename: filename, mimeType: 'application/pdf'),
            );
          }
          return ListView.separated(
            padding: const EdgeInsets.all(16),
            itemCount: pages.length,
            separatorBuilder: (_, _) => const SizedBox(height: 16),
            itemBuilder: (context, i) => Center(
              child: ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 820),
                child: Card(
                  clipBehavior: Clip.antiAlias,
                  child: Image.memory(pages[i], fit: BoxFit.fitWidth),
                ),
              ),
            ),
          );
        },
      ),
    );
  }

  Future<List<Uint8List>> _raster() async {
    try {
      final out = <Uint8List>[];
      await for (final page in Printing.raster(bytes, dpi: 110)) {
        out.add(await page.toPng());
      }
      return out;
    } catch (_) {
      return const [];
    }
  }
}
