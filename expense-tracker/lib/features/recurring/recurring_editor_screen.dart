import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:material_ui/material_ui.dart';

import '../../core/utils/date_utils.dart';
import '../../core/utils/extensions.dart';
import '../../core/utils/money.dart';
import '../../core/widgets/widgets.dart';
import '../../models/models.dart';
import '../household/household_providers.dart';
import '../transactions/widgets/pickers.dart';

class RecurringEditorScreen extends ConsumerStatefulWidget {
  const RecurringEditorScreen({super.key, this.editId});
  final String? editId;

  @override
  ConsumerState<RecurringEditorScreen> createState() => _RecurringEditorScreenState();
}

class _RecurringEditorScreenState extends ConsumerState<RecurringEditorScreen> {
  final _amount = TextEditingController();
  final _payee = TextEditingController();
  final _note = TextEditingController();
  final _interval = TextEditingController(text: '1');
  TransactionType _type = TransactionType.expense;
  String? _categoryId;
  String? _accountId;
  String? _toAccountId;
  RecurrenceFrequency _frequency = RecurrenceFrequency.monthly;
  DateTime _nextDue = DateTime.now().add(const Duration(days: 1));
  DateTime? _endDate;
  bool _autoAdd = true;
  bool _isPrivate = false;
  RecurringRule? _editing;
  bool _loaded = false;

  @override
  void dispose() {
    _amount.dispose();
    _payee.dispose();
    _note.dispose();
    _interval.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final currency = ref.watch(baseCurrencyProvider);
    final rules = ref.watch(recurringProvider).value ?? const [];
    if (!_loaded && widget.editId != null) {
      final r = rules.where((r) => r.id == widget.editId).firstOrNull;
      if (r != null) {
        _editing = r;
        _type = r.type;
        _amount.text = Money.plain(r.amount, currency);
        _payee.text = r.payee;
        _note.text = r.note;
        _interval.text = '${r.interval}';
        _categoryId = r.categoryId;
        _accountId = r.accountId;
        _toAccountId = r.toAccountId;
        _frequency = r.frequency;
        _nextDue = r.nextDue;
        _endDate = r.endDate;
        _autoAdd = r.autoAdd;
        _isPrivate = r.isPrivate;
        _loaded = true;
      }
    } else {
      _loaded = true;
    }

    final accounts = (ref.watch(accountsProvider).value ?? const []).where((a) => !a.isArchived).toList();
    final kind = _type == TransactionType.income ? CategoryKind.income : CategoryKind.expense;
    final categories = (ref.watch(categoriesProvider).value ?? const []).where((c) => c.kind == kind && !c.isArchived).toList();
    _accountId ??= accounts.isNotEmpty ? accounts.first.id : null;
    final category = categories.where((c) => c.id == _categoryId).firstOrNull;
    final account = accounts.where((a) => a.id == _accountId).firstOrNull;
    final toAccount = accounts.where((a) => a.id == _toAccountId).firstOrNull;
    final household = ref.watch(activeHouseholdProvider).value;

    return Scaffold(
      appBar: AppBar(
        title: Text(_editing == null ? 'New recurring' : 'Edit recurring'),
        actions: [
          if (_editing != null)
            IconButton(
              icon: const Icon(Icons.delete_outline_rounded),
              onPressed: () async {
                final ok = await confirmDialog(context, title: 'Delete rule?', message: 'Already created transactions are kept.');
                if (!ok || !mounted) return;
                await ref.read(ledgerProvider)?.deleteRecurring(_editing!.id);
                if (context.mounted) context.pop();
              },
            ),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(16, 8, 16, 120),
        children: [
          SegmentedButton<TransactionType>(
            segments: const [
              ButtonSegment(value: TransactionType.expense, label: Text('Expense')),
              ButtonSegment(value: TransactionType.income, label: Text('Income')),
              ButtonSegment(value: TransactionType.transfer, label: Text('Transfer')),
            ],
            selected: {_type},
            showSelectedIcon: false,
            onSelectionChanged: (s) => setState(() {
              _type = s.first;
              _categoryId = null;
            }),
          ),
          const SizedBox(height: 16),
          TextField(
            controller: _amount,
            keyboardType: const TextInputType.numberWithOptions(decimal: true),
            decoration: InputDecoration(labelText: 'Amount', prefixText: '${Money.symbol(currency)} '),
          ),
          const SizedBox(height: 12),
          if (_type != TransactionType.transfer)
            ListTile(
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14), side: BorderSide(color: context.colors.outlineVariant)),
              leading: IconBadge(iconKey: category?.iconKey ?? 'category', color: category?.color ?? 0xFF78909C, size: 36),
              title: Text(category?.name ?? 'Choose a category'),
              trailing: const Icon(Icons.expand_more_rounded),
              onTap: () async {
                final picked = await showCategoryPicker(context, categories: categories, selected: _categoryId);
                if (picked != null) setState(() => _categoryId = picked);
              },
            ),
          const SizedBox(height: 10),
          ListTile(
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14), side: BorderSide(color: context.colors.outlineVariant)),
            leading: IconBadge(iconKey: account?.resolvedIconKey ?? 'wallet', color: account?.color ?? 0xFF78909C, size: 36),
            title: Text(account?.name ?? 'Choose an account'),
            subtitle: Text(_type == TransactionType.transfer ? 'From' : 'Account'),
            trailing: const Icon(Icons.expand_more_rounded),
            onTap: () async {
              final picked = await showAccountPicker(context, accounts: accounts, selected: _accountId);
              if (picked != null) setState(() => _accountId = picked);
            },
          ),
          if (_type == TransactionType.transfer) ...[
            const SizedBox(height: 10),
            ListTile(
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14), side: BorderSide(color: context.colors.outlineVariant)),
              leading: IconBadge(iconKey: toAccount?.resolvedIconKey ?? 'wallet', color: toAccount?.color ?? 0xFF78909C, size: 36),
              title: Text(toAccount?.name ?? 'Choose an account'),
              subtitle: const Text('To'),
              trailing: const Icon(Icons.expand_more_rounded),
              onTap: () async {
                final picked = await showAccountPicker(context, accounts: accounts.where((a) => a.id != _accountId).toList(), selected: _toAccountId);
                if (picked != null) setState(() => _toAccountId = picked);
              },
            ),
          ],
          const SizedBox(height: 16),
          TextField(
            controller: _payee,
            textCapitalization: TextCapitalization.words,
            decoration: const InputDecoration(labelText: 'Payee / description', prefixIcon: Icon(Icons.storefront_outlined)),
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _note,
            decoration: const InputDecoration(labelText: 'Note (optional)', prefixIcon: Icon(Icons.notes_rounded)),
          ),
          const SizedBox(height: 20),
          Text('Schedule', style: context.text.titleSmall),
          const SizedBox(height: 8),
          Row(
            children: [
              Text('Every', style: context.text.bodyLarge),
              const SizedBox(width: 10),
              SizedBox(
                width: 64,
                child: TextField(
                  controller: _interval,
                  keyboardType: TextInputType.number,
                  textAlign: TextAlign.center,
                  decoration: const InputDecoration(contentPadding: EdgeInsets.symmetric(vertical: 12)),
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Wrap(
                  spacing: 6,
                  children: [
                    for (final f in RecurrenceFrequency.values)
                      ChoiceChip(
                        label: Text(f.label.replaceAll('ly', '').replaceAll('Dai', 'Day').replaceAll('Week', 'Week').replaceAll('Month', 'Month').replaceAll('Year', 'Year')),
                        selected: _frequency == f,
                        onSelected: (_) => setState(() => _frequency = f),
                      ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Row(
            children: [
              Expanded(
                child: OutlinedButton.icon(
                  onPressed: () async {
                    final d = await pickDate(context, initial: _nextDue);
                    if (d != null) setState(() => _nextDue = DateTime(d.year, d.month, d.day, 9));
                  },
                  icon: const Icon(Icons.play_arrow_rounded, size: 18),
                  label: Text('Next: ${AppDates.dayMonthYear.format(_nextDue)}'),
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: OutlinedButton.icon(
                  onPressed: () async {
                    final d = await pickDate(context, initial: _endDate ?? _nextDue.add(const Duration(days: 365)));
                    if (d != null) setState(() => _endDate = d);
                  },
                  icon: const Icon(Icons.stop_rounded, size: 18),
                  label: Text(_endDate == null ? 'No end date' : 'Ends ${AppDates.dayMonthYear.format(_endDate!)}'),
                ),
              ),
            ],
          ),
          if (_endDate != null) TextButton(onPressed: () => setState(() => _endDate = null), child: const Text('Remove end date')),
          SwitchListTile(
            contentPadding: EdgeInsets.zero,
            title: const Text('Add automatically'),
            subtitle: const Text('Off: only show as upcoming so you confirm manually'),
            value: _autoAdd,
            onChanged: (v) => setState(() => _autoAdd = v),
          ),
          if (household != null && household.isShared)
            SwitchListTile(
              contentPadding: EdgeInsets.zero,
              title: const Text('Private'),
              value: _isPrivate,
              onChanged: (v) => setState(() => _isPrivate = v),
            ),
        ],
      ),
      bottomNavigationBar: SafeArea(
        minimum: const EdgeInsets.fromLTRB(16, 8, 16, 16),
        child: FilledButton(onPressed: _save, child: Text(_editing == null ? 'Create rule' : 'Save changes')),
      ),
    );
  }

  Future<void> _save() async {
    final amount = Money.parse(_amount.text);
    final interval = int.tryParse(_interval.text) ?? 1;
    if (amount == null || amount <= 0) {
      context.showSnack('Enter a valid amount', error: true);
      return;
    }
    if (_accountId == null || (_type == TransactionType.transfer && (_toAccountId == null || _toAccountId == _accountId))) {
      context.showSnack('Choose the accounts', error: true);
      return;
    }
    if (_type != TransactionType.transfer && _categoryId == null) {
      context.showSnack('Choose a category', error: true);
      return;
    }
    final ledger = ref.read(ledgerProvider);
    final profile = ref.read(userProfileProvider).value;
    if (ledger == null || profile == null) return;
    final rule = RecurringRule(
      id: _editing?.id ?? ledger.newId('recurring'),
      type: _type,
      amount: amount,
      currency: ref.read(baseCurrencyProvider),
      accountId: _accountId!,
      toAccountId: _type == TransactionType.transfer ? _toAccountId : null,
      categoryId: _type == TransactionType.transfer ? null : _categoryId,
      payee: _payee.text.trim(),
      note: _note.text.trim(),
      frequency: _frequency,
      interval: interval.clamp(1, 365),
      nextDue: _nextDue,
      endDate: _endDate,
      autoAdd: _autoAdd,
      isActive: _editing?.isActive ?? true,
      isPrivate: _isPrivate,
      createdBy: _editing?.createdBy ?? profile.uid,
      createdAt: _editing?.createdAt ?? DateTime.now(),
      lastGeneratedAt: _editing?.lastGeneratedAt,
    );
    await ledger.saveRecurring(rule);
    if (mounted) context.pop();
  }
}
