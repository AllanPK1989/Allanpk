import 'package:file_picker/file_picker.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:material_ui/material_ui.dart';

import '../../core/utils/date_utils.dart';
import '../../core/utils/extensions.dart';
import '../../core/widgets/widgets.dart';
import '../../models/models.dart';
import '../household/household_providers.dart';
import '../transactions/widgets/pickers.dart';
import 'csv_service.dart';

/// Three-step CSV import: pick file → map columns → review & import.
class ImportCsvScreen extends ConsumerStatefulWidget {
  const ImportCsvScreen({super.key});

  @override
  ConsumerState<ImportCsvScreen> createState() => _ImportCsvScreenState();
}

class _ImportCsvScreenState extends ConsumerState<ImportCsvScreen> {
  ParsedCsv? _csv;
  CsvMapping _map = const CsvMapping();
  String? _fileName;
  String? _accountId;
  String? _fallbackCategoryId;
  bool _skipDuplicates = true;
  bool _importing = false;

  Future<void> _pick() async {
    final files = await FilePicker.pickFiles(
      type: FileType.custom,
      allowedExtensions: ['csv', 'txt'],
    );
    final file = files.firstOrNull;
    if (file == null) return;
    final bytes = await file.readAsBytes();
    final parsed = CsvService.parse(CsvService.decodeBytes(bytes));
    if (parsed.headers.isEmpty) {
      if (mounted) context.showSnack('That file looks empty', error: true);
      return;
    }
    setState(() {
      _csv = parsed;
      _fileName = file.name;
      _map = CsvService.guessMapping(parsed.headers);
    });
  }

  @override
  Widget build(BuildContext context) {
    final accounts = (ref.watch(accountsProvider).value ?? const []).where((a) => !a.isArchived).toList();
    final categories = (ref.watch(categoriesProvider).value ?? const []).where((c) => !c.isArchived).toList();
    final currency = ref.watch(baseCurrencyProvider);
    _accountId ??= accounts.firstOrNull?.id;
    final csv = _csv;
    final result = csv == null || !_map.isUsable ? null : CsvService.toDrafts(csv, _map);

    return Scaffold(
      appBar: AppBar(title: const Text('Import CSV')),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(16, 4, 16, 120),
        children: [
          _StepCard(
            step: 1,
            title: 'Choose a file',
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'CSV exported from your bank, another budgeting app, or this app. The first row must contain column names.',
                  style: context.text.bodySmall?.copyWith(color: context.colors.onSurfaceVariant),
                ),
                const SizedBox(height: 10),
                Row(
                  children: [
                    FilledButton.tonalIcon(
                      style: FilledButton.styleFrom(minimumSize: const Size(0, 44)),
                      onPressed: _pick,
                      icon: const Icon(Icons.upload_file_rounded, size: 18),
                      label: Text(csv == null ? 'Select CSV' : 'Choose another'),
                    ),
                    const SizedBox(width: 12),
                    if (_fileName != null)
                      Expanded(child: Text('$_fileName · ${csv!.rows.length} rows', style: context.text.bodySmall, overflow: TextOverflow.ellipsis)),
                  ],
                ),
              ],
            ),
          ),
          if (csv != null) ...[
            const SizedBox(height: 12),
            _StepCard(
              step: 2,
              title: 'Map columns',
              child: Column(
                children: [
                  _mapRow('Date *', _map.date, csv.headers, (v) => setState(() => _map = _map.copyWith(date: v))),
                  _mapRow('Amount (signed)', _map.amount, csv.headers, (v) => setState(() => _map = v == null ? _map.copyWith(clearAmount: true) : _map.copyWith(amount: v))),
                  _mapRow('Debit / expense', _map.debit, csv.headers, (v) => setState(() => _map = v == null ? _map.copyWith(clearDebit: true) : _map.copyWith(debit: v))),
                  _mapRow('Credit / income', _map.credit, csv.headers, (v) => setState(() => _map = v == null ? _map.copyWith(clearCredit: true) : _map.copyWith(credit: v))),
                  _mapRow('Payee / description', _map.description, csv.headers, (v) => setState(() => _map = _map.copyWith(description: v))),
                  _mapRow('Category', _map.category, csv.headers, (v) => setState(() => _map = _map.copyWith(category: v))),
                  _mapRow('Note', _map.note, csv.headers, (v) => setState(() => _map = _map.copyWith(note: v))),
                  _mapRow('Type (income/expense)', _map.type, csv.headers, (v) => setState(() => _map = _map.copyWith(type: v))),
                  if (!_map.isUsable)
                    Padding(
                      padding: const EdgeInsets.only(top: 8),
                      child: Text('Pick a date column and an amount (or debit/credit) column to continue.', style: context.text.bodySmall?.copyWith(color: context.colors.error)),
                    ),
                ],
              ),
            ),
          ],
          if (result != null) ...[
            const SizedBox(height: 12),
            _StepCard(
              step: 3,
              title: 'Review & import',
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  ListTile(
                    contentPadding: EdgeInsets.zero,
                    leading: const Icon(Icons.account_balance_wallet_outlined),
                    title: const Text('Import into account'),
                    subtitle: Text(accounts.where((a) => a.id == _accountId).firstOrNull?.name ?? 'Choose'),
                    trailing: const Icon(Icons.expand_more_rounded),
                    onTap: () async {
                      final picked = await showAccountPicker(context, accounts: accounts, selected: _accountId);
                      if (picked != null) setState(() => _accountId = picked);
                    },
                  ),
                  ListTile(
                    contentPadding: EdgeInsets.zero,
                    leading: const Icon(Icons.category_outlined),
                    title: const Text('Category when none matches'),
                    subtitle: Text(categories.where((c) => c.id == _fallbackCategoryId).firstOrNull?.name ?? 'Other Expense / Other Income'),
                    trailing: const Icon(Icons.expand_more_rounded),
                    onTap: () async {
                      final picked = await showCategoryPicker(context, categories: categories.where((c) => c.kind == CategoryKind.expense).toList(), selected: _fallbackCategoryId);
                      if (picked != null) setState(() => _fallbackCategoryId = picked);
                    },
                  ),
                  SwitchListTile(
                    contentPadding: EdgeInsets.zero,
                    title: const Text('Skip likely duplicates'),
                    subtitle: const Text('Same date, amount and payee already in the ledger'),
                    value: _skipDuplicates,
                    onChanged: (v) => setState(() => _skipDuplicates = v),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    '${result.drafts.length} rows ready'
                    '${result.skipped.isEmpty ? '' : ' · ${result.skipped.length} rows skipped (no date/amount): lines ${result.skipped.take(8).join(', ')}${result.skipped.length > 8 ? '…' : ''}'}',
                    style: context.text.bodySmall?.copyWith(color: context.colors.onSurfaceVariant),
                  ),
                  const SizedBox(height: 8),
                  for (final d in result.drafts.take(6))
                    ListTile(
                      dense: true,
                      contentPadding: EdgeInsets.zero,
                      leading: Icon(d.type == TransactionType.income ? Icons.south_west_rounded : Icons.north_east_rounded, size: 18),
                      title: Text(d.description.isEmpty ? (d.categoryName.isEmpty ? 'Imported' : d.categoryName) : d.description, maxLines: 1, overflow: TextOverflow.ellipsis),
                      subtitle: Text('${AppDates.dayMonthYear.format(d.date)}${d.categoryName.isEmpty ? '' : ' · ${d.categoryName}'}'),
                      trailing: AmountText(d.amount, currency: currency, type: d.type, signed: true, style: context.text.labelLarge),
                    ),
                  if (result.drafts.length > 6)
                    Text('…and ${result.drafts.length - 6} more', style: context.text.bodySmall?.copyWith(color: context.colors.onSurfaceVariant)),
                ],
              ),
            ),
          ],
        ],
      ),
      bottomNavigationBar: result == null || result.drafts.isEmpty
          ? null
          : SafeArea(
              minimum: const EdgeInsets.fromLTRB(16, 8, 16, 16),
              child: FilledButton.icon(
                onPressed: _importing ? null : () => _import(result, categories),
                icon: _importing
                    ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                    : const Icon(Icons.download_done_rounded),
                label: Text('Import ${result.drafts.length} transactions'),
              ),
            ),
    );
  }

  Widget _mapRow(String label, int? value, List<String> headers, ValueChanged<int?> onChanged) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Row(
        children: [
          SizedBox(width: 150, child: Text(label, style: context.text.bodyMedium)),
          Expanded(
            child: DropdownButtonFormField<int?>(
              initialValue: value != null && value < headers.length ? value : null,
              isDense: true,
              decoration: const InputDecoration(contentPadding: EdgeInsets.symmetric(horizontal: 12, vertical: 10)),
              items: [
                const DropdownMenuItem<int?>(value: null, child: Text('— not used —')),
                for (var i = 0; i < headers.length; i++) DropdownMenuItem<int?>(value: i, child: Text(headers[i].isEmpty ? 'Column ${i + 1}' : headers[i], overflow: TextOverflow.ellipsis)),
              ],
              onChanged: onChanged,
            ),
          ),
        ],
      ),
    );
  }

  Future<void> _import(ImportResult result, List<Category> categories) async {
    final ledger = ref.read(ledgerProvider);
    final profile = ref.read(userProfileProvider).value;
    final accountId = _accountId;
    if (ledger == null || profile == null || accountId == null) {
      context.showSnack('Choose an account first', error: true);
      return;
    }
    setState(() => _importing = true);
    try {
      final currency = ref.read(baseCurrencyProvider);
      final existing = ref.read(allTransactionsProvider).value ?? const [];
      final seen = <String>{
        for (final t in existing) '${AppDates.iso.format(t.date)}|${t.amount.toStringAsFixed(2)}|${t.payee.toLowerCase().trim()}',
      };
      final byName = {for (final c in categories) c.name.toLowerCase(): c};
      Category? fallback(TransactionType type) {
        if (type == TransactionType.expense && _fallbackCategoryId != null) {
          return categories.where((c) => c.id == _fallbackCategoryId).firstOrNull;
        }
        final kind = type == TransactionType.income ? CategoryKind.income : CategoryKind.expense;
        return categories.where((c) => c.kind == kind && c.name.toLowerCase().startsWith('other')).firstOrNull ??
            categories.where((c) => c.kind == kind).firstOrNull;
      }

      final now = DateTime.now();
      final txs = <Transaction>[];
      var duplicates = 0;
      for (final d in result.drafts) {
        final key = '${AppDates.iso.format(d.date)}|${d.amount.toStringAsFixed(2)}|${d.description.toLowerCase().trim()}';
        if (_skipDuplicates && seen.contains(key)) {
          duplicates++;
          continue;
        }
        seen.add(key);
        final matched = byName[d.categoryName.toLowerCase()];
        final cat = matched != null && matched.kind == (d.type == TransactionType.income ? CategoryKind.income : CategoryKind.expense)
            ? matched
            : fallback(d.type);
        txs.add(
          Transaction(
            id: ledger.newId('transactions'),
            type: d.type,
            amount: roundMoney(d.amount),
            currency: currency,
            originalAmount: roundMoney(d.amount),
            accountId: accountId,
            categoryId: cat?.id,
            date: d.date,
            payee: d.description,
            note: d.note.isEmpty ? 'Imported from CSV' : d.note,
            tags: const ['imported'],
            createdBy: profile.uid,
            createdByName: profile.displayName,
            createdAt: now,
            updatedAt: now,
          ),
        );
      }
      await ledger.addTransactions(txs);
      if (!mounted) return;
      context.showSnack('Imported ${txs.length} transactions${duplicates > 0 ? ' · $duplicates duplicates skipped' : ''}');
      context.pop();
    } catch (e) {
      if (mounted) context.showSnack('Import failed: $e', error: true);
    } finally {
      if (mounted) setState(() => _importing = false);
    }
  }
}

class _StepCard extends StatelessWidget {
  const _StepCard({required this.step, required this.title, required this.child});
  final int step;
  final String title;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    return AppCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              CircleAvatar(radius: 13, backgroundColor: context.colors.primaryContainer, child: Text('$step', style: context.text.labelLarge)),
              const SizedBox(width: 10),
              Text(title, style: context.text.titleSmall),
            ],
          ),
          const SizedBox(height: 10),
          child,
        ],
      ),
    );
  }
}

