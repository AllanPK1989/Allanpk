import 'dart:typed_data';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:image_picker/image_picker.dart';
import 'package:material_ui/material_ui.dart';

import '../../core/theme/app_theme.dart';
import '../../core/utils/date_utils.dart';
import '../../core/utils/expression.dart';
import '../../core/utils/extensions.dart';
import '../../core/utils/money.dart';
import '../../core/widgets/widgets.dart';
import '../../models/models.dart';
import '../analytics/analytics_engine.dart';
import '../auth/auth_providers.dart';
import '../household/household_providers.dart';
import 'widgets/pickers.dart';

/// Add or edit a transaction. Pass [editId] to edit, [duplicateOf] to clone.
class TransactionEditorScreen extends ConsumerStatefulWidget {
  const TransactionEditorScreen({super.key, this.editId, this.initialType, this.duplicateOf});

  final String? editId;
  final String? initialType;
  final String? duplicateOf;

  @override
  ConsumerState<TransactionEditorScreen> createState() => _TransactionEditorScreenState();
}

class _TransactionEditorScreenState extends ConsumerState<TransactionEditorScreen> {
  final _amount = TextEditingController();
  final _payee = TextEditingController();
  final _note = TextEditingController();
  final _tagInput = TextEditingController();
  final _amountFocus = FocusNode();

  TransactionType _type = TransactionType.expense;
  String? _currency;
  String? _categoryId;
  String? _accountId;
  String? _toAccountId;
  DateTime _date = DateTime.now();
  List<String> _tags = [];
  bool _isPrivate = false;
  bool _repeat = false;
  RecurrenceFrequency _frequency = RecurrenceFrequency.monthly;
  final List<Uint8List> _newReceipts = [];
  List<String> _existingReceipts = [];
  Transaction? _editing;
  bool _loaded = false;
  bool _saving = false;

  @override
  void initState() {
    super.initState();
    _type = TransactionType.fromKey(widget.initialType);
    WidgetsBinding.instance.addPostFrameCallback((_) => _amountFocus.requestFocus());
  }

  @override
  void dispose() {
    _amount.dispose();
    _payee.dispose();
    _note.dispose();
    _tagInput.dispose();
    _amountFocus.dispose();
    super.dispose();
  }

  void _loadFrom(Transaction tx, {required bool asEdit}) {
    _editing = asEdit ? tx : null;
    _type = tx.type;
    _currency = tx.currency;
    _amount.text = Money.plain(tx.originalAmount, tx.currency);
    _categoryId = tx.categoryId;
    _accountId = tx.accountId;
    _toAccountId = tx.toAccountId;
    _date = asEdit ? tx.date : DateTime.now();
    _payee.text = tx.payee;
    _note.text = tx.note;
    _tags = List.of(tx.tags);
    _isPrivate = tx.isPrivate;
    _existingReceipts = asEdit ? List.of(tx.receiptUrls) : [];
  }

  @override
  Widget build(BuildContext context) {
    final all = ref.watch(allTransactionsProvider).value ?? const [];
    final sourceId = widget.editId ?? widget.duplicateOf;
    if (!_loaded && sourceId != null) {
      final tx = all.where((t) => t.id == sourceId).firstOrNull;
      if (tx != null) {
        _loadFrom(tx, asEdit: widget.editId != null);
        _loaded = true;
      }
    } else if (!_loaded) {
      _loaded = true;
    }

    final accounts = (ref.watch(accountsProvider).value ?? const []).where((a) => !a.isArchived).toList();
    final categories = (ref.watch(categoriesProvider).value ?? const []).where((c) => !c.isArchived).toList();
    final baseCurrency = ref.watch(baseCurrencyProvider);
    final rates = ref.watch(ratesProvider).value;
    final currency = _currency ?? baseCurrency;
    final household = ref.watch(activeHouseholdProvider).value;
    final role = ref.watch(myRoleProvider);

    _accountId ??= accounts.isNotEmpty ? accounts.first.id : null;
    final kind = _type == TransactionType.income ? CategoryKind.income : CategoryKind.expense;
    final typeCategories = categories.where((c) => c.kind == kind).toList();
    final selectedCategory = typeCategories.where((c) => c.id == _categoryId).firstOrNull;
    final account = accounts.where((a) => a.id == _accountId).firstOrNull;
    final toAccount = accounts.where((a) => a.id == _toAccountId).firstOrNull;

    final typed = evaluateExpression(_amount.text);
    final converted = typed == null || currency == baseCurrency || rates == null
        ? null
        : rates.convertToBase(typed, currency);
    final typeColor = switch (_type) {
      TransactionType.expense => AppTheme.expense,
      TransactionType.income => AppTheme.income,
      TransactionType.transfer => AppTheme.transfer,
    };

    final canEditOthers = role.canEditOthersTransactions;
    final uid = ref.watch(currentUidProvider);
    final locked = _editing != null && _editing!.createdBy != uid && !canEditOthers;

    return Scaffold(
      appBar: AppBar(
        title: Text(_editing == null ? 'New transaction' : 'Edit transaction'),
        actions: [
          if (_editing != null && !locked)
            IconButton(
              tooltip: 'Delete',
              icon: const Icon(Icons.delete_outline_rounded),
              onPressed: _delete,
            ),
        ],
      ),
      body: locked
          ? const EmptyState(
              icon: Icons.lock_outline_rounded,
              title: 'View only',
              message: 'Only adults in the household can edit transactions added by others.',
            )
          : ListView(
              padding: const EdgeInsets.fromLTRB(16, 8, 16, 120),
              children: [
                SegmentedButton<TransactionType>(
                  segments: const [
                    ButtonSegment(value: TransactionType.expense, label: Text('Expense'), icon: Icon(Icons.arrow_upward_rounded)),
                    ButtonSegment(value: TransactionType.income, label: Text('Income'), icon: Icon(Icons.arrow_downward_rounded)),
                    ButtonSegment(value: TransactionType.transfer, label: Text('Transfer'), icon: Icon(Icons.swap_horiz_rounded)),
                  ],
                  selected: {_type},
                  showSelectedIcon: false,
                  onSelectionChanged: (s) => setState(() {
                    _type = s.first;
                    _categoryId = null;
                  }),
                ),
                const SizedBox(height: 20),
                // Amount
                AppCard(
                  padding: const EdgeInsets.fromLTRB(16, 12, 16, 12),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Text('Amount', style: context.text.labelMedium?.copyWith(color: context.colors.onSurfaceVariant)),
                          const Spacer(),
                          ActionChip(
                            avatar: Text(Money.symbol(currency), style: const TextStyle(fontWeight: FontWeight.w700)),
                            label: Text(currency),
                            onPressed: () async {
                              final picked = await showCurrencyPicker(context, selected: currency);
                              if (picked != null) setState(() => _currency = picked);
                            },
                          ),
                        ],
                      ),
                      TextField(
                        controller: _amount,
                        focusNode: _amountFocus,
                        keyboardType: const TextInputType.numberWithOptions(decimal: true),
                        style: context.text.displaySmall?.copyWith(color: typeColor),
                        decoration: InputDecoration(
                          hintText: '0',
                          filled: false,
                          border: InputBorder.none,
                          enabledBorder: InputBorder.none,
                          focusedBorder: InputBorder.none,
                          contentPadding: EdgeInsets.zero,
                          prefixText: '${Money.symbol(currency)} ',
                          prefixStyle: context.text.displaySmall?.copyWith(color: typeColor.withValues(alpha: 0.6)),
                        ),
                        onChanged: (_) => setState(() {}),
                      ),
                      if (_amount.text.contains(RegExp(r'[+\-*/x×÷]')) && typed != null)
                        Text('= ${Money.plain(typed, currency)}', style: context.text.bodySmall?.copyWith(color: context.colors.onSurfaceVariant)),
                      if (converted != null)
                        Text(
                          '≈ ${Money.format(converted, baseCurrency)}'
                          '${rates != null && rates.isOffline ? ' (rates unavailable, using 1:1)' : ''}',
                          style: context.text.bodySmall?.copyWith(color: context.colors.onSurfaceVariant),
                        ),
                    ],
                  ),
                ),
                const SizedBox(height: 12),
                if (_type != TransactionType.transfer)
                  _PickerTile(
                    label: 'Category',
                    value: selectedCategory?.name ?? 'Choose a category',
                    iconKey: selectedCategory?.iconKey ?? 'category',
                    color: selectedCategory?.color ?? 0xFF78909C,
                    onTap: () async {
                      final picked = await showCategoryPicker(context, categories: typeCategories, selected: _categoryId);
                      if (picked != null) setState(() => _categoryId = picked);
                    },
                  ),
                if (_type != TransactionType.transfer) const SizedBox(height: 10),
                _PickerTile(
                  label: _type == TransactionType.transfer ? 'From account' : 'Account',
                  value: account?.name ?? 'Choose an account',
                  iconKey: account?.resolvedIconKey ?? 'wallet',
                  color: account?.color ?? 0xFF78909C,
                  onTap: () async {
                    final picked = await showAccountPicker(context, accounts: accounts, selected: _accountId);
                    if (picked != null) setState(() => _accountId = picked);
                  },
                ),
                if (_type == TransactionType.transfer) ...[
                  const SizedBox(height: 10),
                  _PickerTile(
                    label: 'To account',
                    value: toAccount?.name ?? 'Choose an account',
                    iconKey: toAccount?.resolvedIconKey ?? 'wallet',
                    color: toAccount?.color ?? 0xFF78909C,
                    onTap: () async {
                      final picked = await showAccountPicker(
                        context,
                        accounts: accounts.where((a) => a.id != _accountId).toList(),
                        selected: _toAccountId,
                      );
                      if (picked != null) setState(() => _toAccountId = picked);
                    },
                  ),
                ],
                const SizedBox(height: 10),
                Row(
                  children: [
                    Expanded(
                      child: _PickerTile(
                        label: 'Date',
                        value: AppDates.relativeDay(_date),
                        icon: Icons.calendar_today_rounded,
                        onTap: () async {
                          final picked = await pickDate(context, initial: _date);
                          if (picked != null) {
                            setState(() => _date = DateTime(picked.year, picked.month, picked.day, _date.hour, _date.minute));
                          }
                        },
                      ),
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: _PickerTile(
                        label: 'Time',
                        value: AppDates.time.format(_date),
                        icon: Icons.schedule_rounded,
                        onTap: () async {
                          final picked = await showTimePicker(context: context, initialTime: TimeOfDay.fromDateTime(_date));
                          if (picked != null) {
                            setState(() => _date = DateTime(_date.year, _date.month, _date.day, picked.hour, picked.minute));
                          }
                        },
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 16),
                PayeeField(controller: _payee, label: _type == TransactionType.income ? 'Source (optional)' : 'Payee / merchant (optional)'),
                const SizedBox(height: 12),
                TextField(
                  controller: _note,
                  textCapitalization: TextCapitalization.sentences,
                  maxLines: 2,
                  decoration: const InputDecoration(labelText: 'Note (optional)', prefixIcon: Icon(Icons.notes_rounded)),
                ),
                const SizedBox(height: 12),
                TagEditor(
                  tags: _tags,
                  controller: _tagInput,
                  onChanged: (t) => setState(() => _tags = t),
                ),
                const SizedBox(height: 16),
                ReceiptPicker(
                  existing: _existingReceipts,
                  pending: _newReceipts,
                  onAdd: _pickReceipt,
                  onRemoveExisting: (url) => setState(() => _existingReceipts.remove(url)),
                  onRemovePending: (i) => setState(() => _newReceipts.removeAt(i)),
                ),
                const SizedBox(height: 8),
                if (household != null && household.isShared)
                  SwitchListTile(
                    contentPadding: EdgeInsets.zero,
                    secondary: const Icon(Icons.lock_outline_rounded),
                    title: const Text('Private'),
                    subtitle: const Text('Only you can see this entry'),
                    value: _isPrivate,
                    onChanged: (v) => setState(() => _isPrivate = v),
                  ),
                if (_editing == null)
                  SwitchListTile(
                    contentPadding: EdgeInsets.zero,
                    secondary: const Icon(Icons.repeat_rounded),
                    title: const Text('Repeat'),
                    subtitle: Text(_repeat ? 'Creates a recurring rule starting next ${_frequency.label.toLowerCase()} period' : 'Rent, salary, subscriptions…'),
                    value: _repeat,
                    onChanged: (v) => setState(() => _repeat = v),
                  ),
                if (_repeat && _editing == null)
                  Padding(
                    padding: const EdgeInsets.only(left: 56, bottom: 8),
                    child: Wrap(
                      spacing: 8,
                      children: [
                        for (final f in RecurrenceFrequency.values)
                          ChoiceChip(
                            label: Text(f.label),
                            selected: _frequency == f,
                            onSelected: (_) => setState(() => _frequency = f),
                          ),
                      ],
                    ),
                  ),
              ],
            ),
      bottomNavigationBar: locked
          ? null
          : SafeArea(
              minimum: const EdgeInsets.fromLTRB(16, 8, 16, 16),
              child: FilledButton(
                onPressed: _saving ? null : _save,
                style: FilledButton.styleFrom(backgroundColor: typeColor),
                child: _saving
                    ? const SizedBox(width: 22, height: 22, child: CircularProgressIndicator(strokeWidth: 2.5, color: Colors.white))
                    : Text(_editing == null ? 'Save ${_type.label.toLowerCase()}' : 'Save changes'),
              ),
            ),
    );
  }

  Future<void> _pickReceipt(ImageSource source) async {
    try {
      final file = await ImagePicker().pickImage(source: source, maxWidth: 1600, imageQuality: 80);
      if (file == null) return;
      final bytes = await file.readAsBytes();
      setState(() => _newReceipts.add(bytes));
    } catch (e) {
      if (mounted) context.showSnack('Could not pick image: $e', error: true);
    }
  }

  Future<void> _save() async {
    final ledger = ref.read(ledgerProvider);
    final profile = ref.read(userProfileProvider).value;
    final baseCurrency = ref.read(baseCurrencyProvider);
    if (ledger == null || profile == null) return;

    final typed = evaluateExpression(_amount.text);
    if (typed == null || typed <= 0) {
      context.showSnack('Enter a valid amount', error: true);
      return;
    }
    if (_accountId == null) {
      context.showSnack('Choose an account', error: true);
      return;
    }
    if (_type == TransactionType.transfer && (_toAccountId == null || _toAccountId == _accountId)) {
      context.showSnack('Choose a different destination account', error: true);
      return;
    }
    if (_type != TransactionType.transfer && _categoryId == null) {
      context.showSnack('Choose a category', error: true);
      return;
    }

    final currency = _currency ?? baseCurrency;
    final rates = ref.read(ratesProvider).value;
    final rate = currency == baseCurrency ? 1.0 : (rates?.rateToBase(currency) ?? 1.0);
    final amountInBase = roundMoney(typed * rate);
    final now = DateTime.now();
    final id = _editing?.id ?? ledger.newId('transactions');

    setState(() => _saving = true);
    try {
      final receiptUrls = List<String>.of(_existingReceipts);
      if (_newReceipts.isNotEmpty) {
        final storage = ref.read(storageServiceProvider);
        for (final bytes in _newReceipts) {
          receiptUrls.add(await storage.uploadReceipt(householdId: ledger.householdId, transactionId: id, bytes: bytes));
        }
      }
      final categoryName = ref.read(categoryMapProvider)[_categoryId]?.name;
      final tx = Transaction(
        id: id,
        type: _type,
        amount: amountInBase,
        currency: currency,
        originalAmount: roundMoney(typed),
        exchangeRate: rate,
        accountId: _accountId!,
        toAccountId: _type == TransactionType.transfer ? _toAccountId : null,
        categoryId: _type == TransactionType.transfer ? null : _categoryId,
        date: _date,
        payee: _payee.text.trim(),
        note: _note.text.trim(),
        tags: _tags,
        receiptUrls: receiptUrls,
        isPrivate: _isPrivate,
        createdBy: _editing?.createdBy ?? profile.uid,
        createdByName: _editing?.createdByName ?? profile.displayName,
        createdAt: _editing?.createdAt ?? now,
        updatedAt: now,
        recurringId: _editing?.recurringId,
        goalId: _editing?.goalId,
      );
      if (_editing == null) {
        await ledger.addTransaction(tx, actor: profile, categoryName: categoryName);
        if (_repeat) {
          final ruleId = ledger.newId('recurring');
          final rule = RecurringRule(
            id: ruleId,
            type: _type,
            amount: amountInBase,
            currency: baseCurrency,
            accountId: _accountId!,
            toAccountId: tx.toAccountId,
            categoryId: tx.categoryId,
            payee: tx.payee,
            note: tx.note,
            tags: tx.tags,
            frequency: _frequency,
            nextDue: DateTime.now(),
            isPrivate: _isPrivate,
            createdBy: profile.uid,
            createdAt: now,
          );
          await ledger.saveRecurring(rule.copyWith(nextDue: rule.nextAfter(_date)));
        }
        // Budget alert check after adding an expense.
        _maybeWarnBudget(tx);
      } else {
        await ledger.updateTransaction(tx, actor: profile, categoryName: categoryName, previous: _editing);
      }
      if (!mounted) return;
      context.showSnack(_editing == null ? '${_type.label} saved' : 'Changes saved');
      context.pop();
    } catch (e) {
      if (mounted) context.showSnack('Could not save: $e', error: true);
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  void _maybeWarnBudget(Transaction tx) {
    if (!tx.isExpense) return;
    final settings = ref.read(appSettingsProvider);
    if (!settings.budgetAlerts) return;
    final progress = ref.read(budgetProgressProvider);
    final currency = ref.read(baseCurrencyProvider);
    final categories = ref.read(categoryMapProvider);
    for (final p in progress) {
      if (!p.range.contains(tx.date)) continue;
      if (!AnalyticsEngine.budgetMatches(p.budget, tx) &&
          !(p.budget.categoryIds.isNotEmpty &&
              categories[tx.categoryId]?.parentId != null &&
              p.budget.categoryIds.contains(categories[tx.categoryId]!.parentId))) {
        continue;
      }
      final newSpent = p.spent + tx.amount;
      String? title;
      String? body;
      if (newSpent > p.limit && p.spent <= p.limit) {
        title = 'Budget exceeded: ${p.budget.name}';
        body = 'You are ${Money.format(newSpent - p.limit, currency)} over the limit.';
      } else if (p.limit > 0 &&
          newSpent / p.limit >= p.budget.alertThreshold &&
          p.spent / p.limit < p.budget.alertThreshold) {
        title = 'Budget alert: ${p.budget.name}';
        body = '${(newSpent / p.limit * 100).round()}% used with ${p.daysLeft} days left.';
      }
      if (title != null && body != null) {
        final messenger = ScaffoldMessenger.maybeOf(context);
        messenger?.showSnackBar(
          SnackBar(
            content: Text('$title — $body'),
            duration: const Duration(seconds: 5),
            backgroundColor: AppTheme.warning,
          ),
        );
        if (settings.browserNotifications) {
          ref.read(notifierProvider).show(title, body);
        }
        break;
      }
    }
  }

  Future<void> _delete() async {
    final tx = _editing;
    if (tx == null) return;
    final ok = await confirmDialog(context, title: 'Delete transaction?', message: 'This cannot be undone.');
    if (!ok || !mounted) return;
    final ledger = ref.read(ledgerProvider);
    final profile = ref.read(userProfileProvider).value;
    await ledger?.deleteTransaction(tx, actor: profile, categoryName: ref.read(categoryMapProvider)[tx.categoryId]?.name);
    if (!mounted) return;
    context.showSnack('Transaction deleted');
    // Pop the editor and the detail page beneath it.
    context.pop();
    if (context.canPop()) context.pop();
  }
}

class _PickerTile extends StatelessWidget {
  const _PickerTile({
    required this.label,
    required this.value,
    required this.onTap,
    this.iconKey,
    this.color,
    this.icon,
  });

  final String label;
  final String value;
  final VoidCallback onTap;
  final String? iconKey;
  final int? color;
  final IconData? icon;

  @override
  Widget build(BuildContext context) {
    return AppCard(
      onTap: onTap,
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      child: Row(
        children: [
          if (icon != null)
            IconBadge(iconKey: null, icon: icon, color: context.colors.primary.argb, size: 38)
          else
            IconBadge(iconKey: iconKey, color: color ?? 0xFF78909C, size: 38),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(label, style: context.text.labelSmall?.copyWith(color: context.colors.onSurfaceVariant)),
                Text(value, style: context.text.titleSmall, maxLines: 1, overflow: TextOverflow.ellipsis),
              ],
            ),
          ),
          Icon(Icons.expand_more_rounded, color: context.colors.onSurfaceVariant),
        ],
      ),
    );
  }
}

