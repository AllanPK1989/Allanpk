import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:material_ui/material_ui.dart';

import '../../core/utils/date_utils.dart';
import '../../core/utils/extensions.dart';
import '../../core/utils/money.dart';
import '../../core/widgets/widgets.dart';
import '../../models/models.dart';
import '../household/household_providers.dart';

class GoalEditorScreen extends ConsumerStatefulWidget {
  const GoalEditorScreen({super.key, this.editId});
  final String? editId;

  @override
  ConsumerState<GoalEditorScreen> createState() => _GoalEditorScreenState();
}

class _GoalEditorScreenState extends ConsumerState<GoalEditorScreen> {
  final _name = TextEditingController();
  final _target = TextEditingController();
  final _saved = TextEditingController();
  final _note = TextEditingController();
  DateTime? _deadline;
  String _icon = 'savings';
  int _color = 0xFF00897B;
  bool _isShared = true;
  Goal? _editing;
  bool _loaded = false;

  @override
  void dispose() {
    _name.dispose();
    _target.dispose();
    _saved.dispose();
    _note.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final currency = ref.watch(baseCurrencyProvider);
    final goals = ref.watch(goalsProvider).value ?? const [];
    if (!_loaded && widget.editId != null) {
      final g = goals.where((g) => g.id == widget.editId).firstOrNull;
      if (g != null) {
        _editing = g;
        _name.text = g.name;
        _target.text = Money.plain(g.targetAmount, currency);
        _saved.text = Money.plain(g.savedAmount, currency);
        _note.text = g.note;
        _deadline = g.deadline;
        _icon = g.iconKey;
        _color = g.color;
        _isShared = g.isShared;
        _loaded = true;
      }
    } else {
      _loaded = true;
    }
    final household = ref.watch(activeHouseholdProvider).value;

    return Scaffold(
      appBar: AppBar(
        title: Text(_editing == null ? 'New goal' : 'Edit goal'),
        actions: [
          if (_editing != null)
            IconButton(
              icon: const Icon(Icons.delete_outline_rounded),
              onPressed: () async {
                final ok = await confirmDialog(context, title: 'Delete goal?', message: 'Linked transfers are kept.');
                if (!ok || !mounted) return;
                await ref.read(ledgerProvider)?.deleteGoal(_editing!);
                if (context.mounted) context.pop();
              },
            ),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(16, 8, 16, 120),
        children: [
          Center(child: IconBadge(iconKey: _icon, color: _color, size: 72)),
          const SizedBox(height: 16),
          TextField(
            controller: _name,
            textCapitalization: TextCapitalization.sentences,
            decoration: const InputDecoration(labelText: 'Goal name', hintText: 'e.g. Emergency fund', prefixIcon: Icon(Icons.flag_outlined)),
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _target,
            keyboardType: const TextInputType.numberWithOptions(decimal: true),
            decoration: InputDecoration(labelText: 'Target amount', prefixText: '${Money.symbol(currency)} '),
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _saved,
            keyboardType: const TextInputType.numberWithOptions(decimal: true),
            decoration: InputDecoration(labelText: 'Already saved', prefixText: '${Money.symbol(currency)} '),
          ),
          const SizedBox(height: 12),
          OutlinedButton.icon(
            onPressed: () async {
              final d = await pickDate(context, initial: _deadline ?? DateTime.now().add(const Duration(days: 180)), first: DateTime.now());
              if (d != null) setState(() => _deadline = d);
            },
            icon: const Icon(Icons.event_rounded, size: 18),
            label: Text(_deadline == null ? 'Target date (optional)' : 'By ${AppDates.dayMonthYear.format(_deadline!)}'),
          ),
          if (_deadline != null)
            TextButton(onPressed: () => setState(() => _deadline = null), child: const Text('Remove date')),
          const SizedBox(height: 12),
          TextField(
            controller: _note,
            decoration: const InputDecoration(labelText: 'Note (optional)', prefixIcon: Icon(Icons.notes_rounded)),
          ),
          if (household != null && household.isShared)
            SwitchListTile(
              contentPadding: EdgeInsets.zero,
              title: const Text('Shared with household'),
              value: _isShared,
              onChanged: (v) => setState(() => _isShared = v),
            ),
          const SizedBox(height: 12),
          Text('Colour', style: context.text.titleSmall),
          const SizedBox(height: 8),
          ColorPicker(selected: _color, onChanged: (c) => setState(() => _color = c)),
          const SizedBox(height: 16),
          Text('Icon', style: context.text.titleSmall),
          const SizedBox(height: 8),
          IconPicker(selected: _icon, color: _color, onChanged: (k) => setState(() => _icon = k)),
        ],
      ),
      bottomNavigationBar: SafeArea(
        minimum: const EdgeInsets.fromLTRB(16, 8, 16, 16),
        child: FilledButton(onPressed: _save, child: Text(_editing == null ? 'Create goal' : 'Save changes')),
      ),
    );
  }

  Future<void> _save() async {
    final target = Money.parse(_target.text);
    final saved = Money.parse(_saved.text) ?? 0;
    if (_name.text.trim().isEmpty || target == null || target <= 0) {
      context.showSnack('Enter a name and target amount', error: true);
      return;
    }
    final ledger = ref.read(ledgerProvider);
    final profile = ref.read(userProfileProvider).value;
    if (ledger == null || profile == null) return;
    final goal = Goal(
      id: _editing?.id ?? ledger.newId('goals'),
      name: _name.text.trim(),
      targetAmount: target,
      savedAmount: saved,
      deadline: _deadline,
      iconKey: _icon,
      color: _color,
      note: _note.text.trim(),
      isShared: _isShared,
      isCompleted: saved >= target,
      createdBy: _editing?.createdBy ?? profile.uid,
      createdAt: _editing?.createdAt ?? DateTime.now(),
    );
    await ledger.saveGoal(goal, actor: profile, isNew: _editing == null);
    if (mounted) context.pop();
  }
}
