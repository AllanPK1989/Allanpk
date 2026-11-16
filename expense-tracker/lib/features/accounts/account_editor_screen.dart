import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:material_ui/material_ui.dart';

import '../../core/utils/extensions.dart';
import '../../core/utils/money.dart';
import '../../core/widgets/widgets.dart';
import '../../models/models.dart';
import '../../router.dart';
import '../household/household_providers.dart';

class AccountEditorScreen extends ConsumerStatefulWidget {
  const AccountEditorScreen({super.key, this.editId});
  final String? editId;

  @override
  ConsumerState<AccountEditorScreen> createState() => _AccountEditorScreenState();
}

class _AccountEditorScreenState extends ConsumerState<AccountEditorScreen> {
  final _name = TextEditingController();
  final _initial = TextEditingController();
  final _creditLimit = TextEditingController();
  AccountType _type = AccountType.bank;
  int _color = 0xFF1E88E5;
  String? _icon;
  bool _isShared = true;
  bool _exclude = false;
  bool _archived = false;
  Account? _editing;
  bool _loaded = false;

  @override
  void dispose() {
    _name.dispose();
    _initial.dispose();
    _creditLimit.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final currency = ref.watch(baseCurrencyProvider);
    final accounts = ref.watch(accountsProvider).value ?? const [];
    if (!_loaded && widget.editId != null) {
      final a = accounts.where((a) => a.id == widget.editId).firstOrNull;
      if (a != null) {
        _editing = a;
        _name.text = a.name;
        _initial.text = Money.plain(a.initialBalance, currency);
        _creditLimit.text = a.creditLimit == null ? '' : Money.plain(a.creditLimit!, currency);
        _type = a.type;
        _color = a.color;
        _icon = a.iconKey;
        _isShared = a.isShared;
        _exclude = a.excludeFromTotals;
        _archived = a.isArchived;
        _loaded = true;
      }
    } else {
      _loaded = true;
    }
    final household = ref.watch(activeHouseholdProvider).value;

    return Scaffold(
      appBar: AppBar(
        title: Text(_editing == null ? 'New account' : 'Edit account'),
        actions: [
          if (_editing != null)
            IconButton(icon: const Icon(Icons.delete_outline_rounded), onPressed: _delete),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(16, 8, 16, 120),
        children: [
          Center(child: IconBadge(iconKey: _icon ?? _type.iconKey, color: _color, size: 72)),
          const SizedBox(height: 16),
          TextField(
            controller: _name,
            textCapitalization: TextCapitalization.words,
            decoration: const InputDecoration(labelText: 'Account name', hintText: 'e.g. HDFC Savings', prefixIcon: Icon(Icons.badge_outlined)),
          ),
          const SizedBox(height: 16),
          Text('Type', style: context.text.titleSmall),
          const SizedBox(height: 8),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              for (final t in AccountType.values)
                ChoiceChip(
                  label: Text(t.label),
                  selected: _type == t,
                  onSelected: (_) => setState(() {
                    _type = t;
                    _icon = null;
                  }),
                ),
            ],
          ),
          const SizedBox(height: 16),
          TextField(
            controller: _initial,
            keyboardType: const TextInputType.numberWithOptions(decimal: true, signed: true),
            decoration: InputDecoration(
              labelText: _type == AccountType.card ? 'Current outstanding (negative)' : 'Opening balance',
              prefixText: '${Money.symbol(currency)} ',
              helperText: 'Balance before any transactions were recorded in the app',
            ),
          ),
          if (_type == AccountType.card) ...[
            const SizedBox(height: 12),
            TextField(
              controller: _creditLimit,
              keyboardType: const TextInputType.numberWithOptions(decimal: true),
              decoration: InputDecoration(labelText: 'Credit limit (optional)', prefixText: '${Money.symbol(currency)} '),
            ),
          ],
          const SizedBox(height: 8),
          if (household != null && household.isShared)
            SwitchListTile(
              contentPadding: EdgeInsets.zero,
              title: const Text('Shared with household'),
              subtitle: const Text('Family members can see and use this account'),
              value: _isShared,
              onChanged: (v) => setState(() => _isShared = v),
            ),
          SwitchListTile(
            contentPadding: EdgeInsets.zero,
            title: const Text('Exclude from net worth'),
            subtitle: const Text('Useful for reimbursable or tracking-only accounts'),
            value: _exclude,
            onChanged: (v) => setState(() => _exclude = v),
          ),
          if (_editing != null)
            SwitchListTile(
              contentPadding: EdgeInsets.zero,
              title: const Text('Archived'),
              subtitle: const Text('Hide from pickers but keep history'),
              value: _archived,
              onChanged: (v) => setState(() => _archived = v),
            ),
          const SizedBox(height: 12),
          Text('Colour', style: context.text.titleSmall),
          const SizedBox(height: 8),
          ColorPicker(selected: _color, onChanged: (c) => setState(() => _color = c)),
          const SizedBox(height: 16),
          Text('Icon', style: context.text.titleSmall),
          const SizedBox(height: 8),
          IconPicker(selected: _icon ?? _type.iconKey, color: _color, onChanged: (k) => setState(() => _icon = k)),
        ],
      ),
      bottomNavigationBar: SafeArea(
        minimum: const EdgeInsets.fromLTRB(16, 8, 16, 16),
        child: FilledButton(onPressed: _save, child: Text(_editing == null ? 'Create account' : 'Save changes')),
      ),
    );
  }

  Future<void> _save() async {
    if (_name.text.trim().isEmpty) {
      context.showSnack('Enter an account name', error: true);
      return;
    }
    final ledger = ref.read(ledgerProvider);
    final profile = ref.read(userProfileProvider).value;
    if (ledger == null || profile == null) return;
    final limit = Money.parse(_creditLimit.text);
    final account = Account(
      id: _editing?.id ?? ledger.newId('accounts'),
      name: _name.text.trim(),
      type: _type,
      currency: ref.read(baseCurrencyProvider),
      initialBalance: Money.parse(_initial.text) ?? 0,
      color: _color,
      iconKey: _icon,
      isArchived: _archived,
      isShared: _isShared,
      excludeFromTotals: _exclude,
      creditLimit: _type == AccountType.card ? limit : null,
      createdBy: _editing?.createdBy ?? profile.uid,
      createdAt: _editing?.createdAt ?? DateTime.now(),
      sortOrder: _editing?.sortOrder ?? (ref.read(accountsProvider).value?.length ?? 0),
    );
    await ledger.saveAccount(account);
    if (mounted) context.popOrHome();
  }

  Future<void> _delete() async {
    final a = _editing;
    if (a == null) return;
    final count = ref.read(balancesProvider).where((b) => b.account.id == a.id).firstOrNull?.transactionCount ?? 0;
    if (count > 0) {
      final archive = await confirmDialog(
        context,
        title: 'Account has transactions',
        message: '$count transactions use this account. Archive it instead so history stays intact?',
        confirmLabel: 'Archive',
        destructive: false,
      );
      if (!archive || !mounted) return;
      await ref.read(ledgerProvider)?.saveAccount(a.copyWith(isArchived: true));
    } else {
      final ok = await confirmDialog(context, title: 'Delete account?', message: 'This cannot be undone.');
      if (!ok || !mounted) return;
      await ref.read(ledgerProvider)?.deleteAccount(a.id);
    }
    if (!mounted) return;
    context.popOrHome();
    if (context.canPop()) context.popOrHome();
  }
}
