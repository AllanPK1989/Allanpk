import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:material_ui/material_ui.dart';

import '../../core/utils/date_utils.dart';
import '../../core/utils/extensions.dart';
import '../../core/utils/money.dart';
import '../../core/widgets/widgets.dart';
import '../../models/models.dart';
import '../../router.dart';
import '../household/household_providers.dart';

class BudgetEditorScreen extends ConsumerStatefulWidget {
  const BudgetEditorScreen({super.key, this.editId});
  final String? editId;

  @override
  ConsumerState<BudgetEditorScreen> createState() => _BudgetEditorScreenState();
}

class _BudgetEditorScreenState extends ConsumerState<BudgetEditorScreen> {
  final _name = TextEditingController();
  final _amount = TextEditingController();
  BudgetPeriod _period = BudgetPeriod.monthly;
  DateTime _start = DateTime(DateTime.now().year, DateTime.now().month, 1);
  DateTime? _end;
  Set<String> _categoryIds = {};
  Set<String> _accountIds = {};
  Set<String> _memberIds = {};
  bool _rollover = false;
  bool _isShared = true;
  double _threshold = 0.8;
  int _color = 0xFF1E88E5;
  Budget? _editing;
  bool _loaded = false;
  bool _saving = false;

  @override
  void dispose() {
    _name.dispose();
    _amount.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final budgets = ref.watch(budgetsProvider).value ?? const [];
    if (!_loaded && widget.editId != null) {
      final b = budgets.where((b) => b.id == widget.editId).firstOrNull;
      if (b != null) {
        _editing = b;
        _name.text = b.name;
        _amount.text = Money.plain(b.amount, ref.read(baseCurrencyProvider));
        _period = b.period;
        _start = b.startDate;
        _end = b.endDate;
        _categoryIds = {...b.categoryIds};
        _accountIds = {...b.accountIds};
        _memberIds = {...b.memberIds};
        _rollover = b.rollover;
        _isShared = b.isShared;
        _threshold = b.alertThreshold;
        _color = b.color;
        _loaded = true;
      }
    } else {
      _loaded = true;
    }

    final categories = (ref.watch(categoriesProvider).value ?? const [])
        .where((c) => c.kind == CategoryKind.expense && !c.isArchived && c.parentId == null)
        .toList();
    final accounts = (ref.watch(accountsProvider).value ?? const []).where((a) => !a.isArchived).toList();
    final household = ref.watch(activeHouseholdProvider).value;
    final currency = ref.watch(baseCurrencyProvider);

    return Scaffold(
      appBar: AppBar(
        title: Text(_editing == null ? 'New budget' : 'Edit budget'),
        actions: [
          if (_editing != null)
            IconButton(icon: const Icon(Icons.delete_outline_rounded), onPressed: _delete),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(16, 8, 16, 120),
        children: [
          TextField(
            controller: _name,
            textCapitalization: TextCapitalization.sentences,
            decoration: const InputDecoration(labelText: 'Name', hintText: 'e.g. Groceries, Monthly spending', prefixIcon: Icon(Icons.label_outline_rounded)),
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _amount,
            keyboardType: const TextInputType.numberWithOptions(decimal: true),
            decoration: InputDecoration(labelText: 'Limit', prefixText: '${Money.symbol(currency)} '),
          ),
          const SizedBox(height: 18),
          Text('Period', style: context.text.titleSmall),
          const SizedBox(height: 8),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              for (final p in BudgetPeriod.values)
                ChoiceChip(label: Text(p.label), selected: _period == p, onSelected: (_) => setState(() => _period = p)),
            ],
          ),
          if (_period == BudgetPeriod.custom) ...[
            const SizedBox(height: 12),
            Row(
              children: [
                Expanded(
                  child: OutlinedButton.icon(
                    onPressed: () async {
                      final d = await pickDate(context, initial: _start);
                      if (d != null) setState(() => _start = d);
                    },
                    icon: const Icon(Icons.calendar_today_rounded, size: 18),
                    label: Text(AppDates.dayMonthYear.format(_start)),
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: OutlinedButton.icon(
                    onPressed: () async {
                      final d = await pickDate(context, initial: _end ?? _start.add(const Duration(days: 30)));
                      if (d != null) setState(() => _end = d);
                    },
                    icon: const Icon(Icons.event_rounded, size: 18),
                    label: Text(_end == null ? 'End date' : AppDates.dayMonthYear.format(_end!)),
                  ),
                ),
              ],
            ),
          ],
          const SizedBox(height: 18),
          Text('Categories', style: context.text.titleSmall),
          Text(
            _categoryIds.isEmpty ? 'All expense categories (overall budget)' : '${_categoryIds.length} selected',
            style: context.text.bodySmall?.copyWith(color: context.colors.onSurfaceVariant),
          ),
          const SizedBox(height: 8),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              for (final c in categories)
                FilterChip(
                  avatar: Icon(Icons.circle, size: 10, color: Color(c.color)),
                  label: Text(c.name),
                  selected: _categoryIds.contains(c.id),
                  onSelected: (v) => setState(() => v ? _categoryIds.add(c.id) : _categoryIds.remove(c.id)),
                ),
            ],
          ),
          const SizedBox(height: 18),
          ExpansionTile(
            tilePadding: EdgeInsets.zero,
            title: Text('Advanced', style: context.text.titleSmall),
            subtitle: const Text('Accounts, members, rollover, alerts'),
            children: [
              if (accounts.length > 1) ...[
                Align(alignment: Alignment.centerLeft, child: Text('Accounts', style: context.text.labelLarge)),
                const SizedBox(height: 6),
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: [
                    for (final a in accounts)
                      FilterChip(
                        label: Text(a.name),
                        selected: _accountIds.contains(a.id),
                        onSelected: (v) => setState(() => v ? _accountIds.add(a.id) : _accountIds.remove(a.id)),
                      ),
                  ],
                ),
                const SizedBox(height: 12),
              ],
              if (household != null && household.isShared) ...[
                Align(alignment: Alignment.centerLeft, child: Text('Members', style: context.text.labelLarge)),
                const SizedBox(height: 6),
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: [
                    for (final m in household.sortedMembers)
                      FilterChip(
                        avatar: MemberAvatar(initials: m.initials, color: m.color, size: 20),
                        label: Text(m.name),
                        selected: _memberIds.contains(m.uid),
                        onSelected: (v) => setState(() => v ? _memberIds.add(m.uid) : _memberIds.remove(m.uid)),
                      ),
                  ],
                ),
                const SizedBox(height: 12),
                SwitchListTile(
                  contentPadding: EdgeInsets.zero,
                  title: const Text('Shared with household'),
                  subtitle: const Text('Everyone can see this budget'),
                  value: _isShared,
                  onChanged: (v) => setState(() => _isShared = v),
                ),
              ],
              SwitchListTile(
                contentPadding: EdgeInsets.zero,
                title: const Text('Roll over unspent amount'),
                subtitle: const Text('Carry leftovers (or overspend) into the next period'),
                value: _rollover,
                onChanged: (v) => setState(() => _rollover = v),
              ),
              ListTile(
                contentPadding: EdgeInsets.zero,
                title: Text('Alert me at ${(_threshold * 100).round()}%'),
                subtitle: Slider(
                  value: _threshold,
                  min: 0.5,
                  max: 1,
                  divisions: 10,
                  label: '${(_threshold * 100).round()}%',
                  onChanged: (v) => setState(() => _threshold = v),
                ),
              ),
              Align(alignment: Alignment.centerLeft, child: Text('Colour', style: context.text.labelLarge)),
              const SizedBox(height: 8),
              ColorPicker(selected: _color, onChanged: (c) => setState(() => _color = c)),
              const SizedBox(height: 8),
            ],
          ),
        ],
      ),
      bottomNavigationBar: SafeArea(
        minimum: const EdgeInsets.fromLTRB(16, 8, 16, 16),
        child: FilledButton(
          onPressed: _saving ? null : _save,
          child: Text(_editing == null ? 'Create budget' : 'Save changes'),
        ),
      ),
    );
  }

  Future<void> _save() async {
    final amount = Money.parse(_amount.text);
    if (amount == null || amount <= 0) {
      context.showSnack('Enter a valid limit', error: true);
      return;
    }
    if (_period == BudgetPeriod.custom && (_end == null || _end!.isBefore(_start))) {
      context.showSnack('Choose a valid end date', error: true);
      return;
    }
    final ledger = ref.read(ledgerProvider);
    final profile = ref.read(userProfileProvider).value;
    if (ledger == null || profile == null) return;
    final name = _name.text.trim().isEmpty
        ? (_categoryIds.isEmpty ? 'Overall budget' : '${_period.label} budget')
        : _name.text.trim();
    setState(() => _saving = true);
    try {
      final budget = Budget(
        id: _editing?.id ?? ledger.newId('budgets'),
        name: name,
        amount: amount,
        period: _period,
        startDate: _period == BudgetPeriod.custom ? _start : (_editing?.startDate ?? DateTime.now()),
        endDate: _period == BudgetPeriod.custom ? _end : null,
        categoryIds: _categoryIds.toList(),
        accountIds: _accountIds.toList(),
        memberIds: _memberIds.toList(),
        rollover: _rollover,
        alertThreshold: _threshold,
        isShared: _isShared,
        createdBy: _editing?.createdBy ?? profile.uid,
        createdAt: _editing?.createdAt ?? DateTime.now(),
        color: _color,
      );
      await ledger.saveBudget(budget, actor: profile, isNew: _editing == null);
      if (mounted) context.popOrHome();
    } catch (e) {
      if (mounted) context.showSnack('Could not save: $e', error: true);
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  Future<void> _delete() async {
    final b = _editing;
    if (b == null) return;
    final ok = await confirmDialog(context, title: 'Delete budget?', message: 'Transactions are kept; only the limit is removed.');
    if (!ok || !mounted) return;
    await ref.read(ledgerProvider)?.deleteBudget(b, actor: ref.read(userProfileProvider).value);
    if (!mounted) return;
    context.popOrHome();
    if (context.canPop()) context.popOrHome();
  }
}
