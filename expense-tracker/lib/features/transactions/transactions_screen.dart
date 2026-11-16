import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_slidable/flutter_slidable.dart';
import 'package:go_router/go_router.dart';
import 'package:material_ui/material_ui.dart';

import '../../core/theme/app_theme.dart';
import '../../core/utils/extensions.dart';
import '../../core/utils/money.dart';
import '../../core/widgets/widgets.dart';
import '../../models/models.dart';
import '../analytics/analytics_engine.dart';
import '../home/period_selector.dart';
import '../household/household_providers.dart';
import 'widgets/transaction_tile.dart';

/// Filter state for the transaction list (kept local to the tab).
class TransactionFilter {
  const TransactionFilter({
    this.types = const {},
    this.categoryIds = const {},
    this.accountIds = const {},
    this.memberIds = const {},
    this.tags = const {},
    this.onlyWithReceipts = false,
  });

  final Set<TransactionType> types;
  final Set<String> categoryIds;
  final Set<String> accountIds;
  final Set<String> memberIds;
  final Set<String> tags;
  final bool onlyWithReceipts;

  bool get isActive =>
      types.isNotEmpty || categoryIds.isNotEmpty || accountIds.isNotEmpty || memberIds.isNotEmpty || tags.isNotEmpty || onlyWithReceipts;

  int get count =>
      (types.isEmpty ? 0 : 1) +
      (categoryIds.isEmpty ? 0 : 1) +
      (accountIds.isEmpty ? 0 : 1) +
      (memberIds.isEmpty ? 0 : 1) +
      (tags.isEmpty ? 0 : 1) +
      (onlyWithReceipts ? 1 : 0);

  bool matches(Transaction t, Map<String, Category> categories) {
    if (types.isNotEmpty && !types.contains(t.type)) return false;
    if (categoryIds.isNotEmpty) {
      final cat = categories[t.categoryId];
      final parent = cat?.parentId;
      if (!categoryIds.contains(t.categoryId) && (parent == null || !categoryIds.contains(parent))) return false;
    }
    if (accountIds.isNotEmpty && !accountIds.contains(t.accountId) && !accountIds.contains(t.toAccountId)) return false;
    if (memberIds.isNotEmpty && !memberIds.contains(t.createdBy)) return false;
    if (tags.isNotEmpty && !t.tags.any(tags.contains)) return false;
    if (onlyWithReceipts && t.receiptUrls.isEmpty) return false;
    return true;
  }

  TransactionFilter copyWith({
    Set<TransactionType>? types,
    Set<String>? categoryIds,
    Set<String>? accountIds,
    Set<String>? memberIds,
    Set<String>? tags,
    bool? onlyWithReceipts,
  }) {
    return TransactionFilter(
      types: types ?? this.types,
      categoryIds: categoryIds ?? this.categoryIds,
      accountIds: accountIds ?? this.accountIds,
      memberIds: memberIds ?? this.memberIds,
      tags: tags ?? this.tags,
      onlyWithReceipts: onlyWithReceipts ?? this.onlyWithReceipts,
    );
  }
}

class TransactionsScreen extends ConsumerStatefulWidget {
  const TransactionsScreen({super.key});

  @override
  ConsumerState<TransactionsScreen> createState() => _TransactionsScreenState();
}

class _TransactionsScreenState extends ConsumerState<TransactionsScreen> {
  TransactionFilter _filter = const TransactionFilter();

  @override
  Widget build(BuildContext context) {
    final txAsync = ref.watch(allTransactionsProvider);
    final periodTx = ref.watch(periodTransactionsProvider);
    final categories = ref.watch(categoryMapProvider);
    final currency = ref.watch(baseCurrencyProvider);
    final range = ref.watch(selectedPeriodProvider);
    final filtered = periodTx.where((t) => _filter.matches(t, categories)).toList();
    final summary = AnalyticsEngine.summarize(filtered, range);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Transactions'),
        actions: [
          IconButton(
            tooltip: 'Search',
            icon: const Icon(Icons.search_rounded),
            onPressed: () => context.push('/search'),
          ),
          Badge(
            isLabelVisible: _filter.isActive,
            label: Text('${_filter.count}'),
            offset: const Offset(-6, 6),
            child: IconButton(
              tooltip: 'Filter',
              icon: Icon(_filter.isActive ? Icons.filter_alt_rounded : Icons.filter_alt_outlined),
              onPressed: _openFilters,
            ),
          ),
          const SizedBox(width: 4),
        ],
      ),
      body: txAsync.when(
        loading: () => const LoadingState(),
        error: (e, _) => ErrorState(error: e, onRetry: () => ref.invalidate(allTransactionsProvider)),
        data: (_) => GroupedTransactionList(
          transactions: filtered,
          leadingSlivers: [
            SliverToBoxAdapter(
              child: Padding(
                padding: const EdgeInsets.fromLTRB(16, 4, 16, 0),
                child: Column(
                  children: [
                    const PeriodSelector(),
                    const SizedBox(height: 10),
                    _SummaryBar(summary: summary, currency: currency),
                    if (_filter.isActive)
                      Align(
                        alignment: Alignment.centerLeft,
                        child: TextButton.icon(
                          onPressed: () => setState(() => _filter = const TransactionFilter()),
                          icon: const Icon(Icons.close_rounded, size: 16),
                          label: Text('Clear ${_filter.count} ${_filter.count == 1 ? 'filter' : 'filters'}'),
                        ),
                      ),
                  ],
                ),
              ),
            ),
            if (filtered.isEmpty)
              SliverFillRemaining(
                hasScrollBody: false,
                child: EmptyState(
                  icon: Icons.receipt_long_rounded,
                  title: _filter.isActive ? 'No matches' : 'No transactions in ${range.label()}',
                  message: _filter.isActive ? 'Try removing some filters.' : 'Add your first expense or income.',
                  actionLabel: _filter.isActive ? null : 'Add transaction',
                  onAction: () => context.push('/transactions/new'),
                ),
              ),
          ],
          itemBuilder: (context, t, tile) => Slidable(
            key: ValueKey(t.id),
            endActionPane: ActionPane(
              motion: const BehindMotion(),
              extentRatio: 0.55,
              children: [
                SlidableAction(
                  onPressed: (_) => context.push('/transactions/new', extra: t.id),
                  backgroundColor: context.colors.secondaryContainer,
                  foregroundColor: context.colors.onSecondaryContainer,
                  icon: Icons.copy_rounded,
                  label: 'Copy',
                ),
                SlidableAction(
                  onPressed: (_) => context.push('/transactions/${t.id}/edit'),
                  backgroundColor: context.colors.primaryContainer,
                  foregroundColor: context.colors.onPrimaryContainer,
                  icon: Icons.edit_rounded,
                  label: 'Edit',
                ),
                SlidableAction(
                  onPressed: (_) => _delete(t),
                  backgroundColor: context.colors.errorContainer,
                  foregroundColor: context.colors.onErrorContainer,
                  icon: Icons.delete_rounded,
                  label: 'Delete',
                ),
              ],
            ),
            child: tile,
          ),
        ),
      ),
    );
  }

  Future<void> _delete(Transaction t) async {
    final ok = await confirmDialog(context, title: 'Delete transaction?', message: 'This cannot be undone.');
    if (!ok) return;
    final ledger = ref.read(ledgerProvider);
    final profile = ref.read(userProfileProvider).value;
    await ledger?.deleteTransaction(t, actor: profile, categoryName: ref.read(categoryMapProvider)[t.categoryId]?.name);
    if (mounted) context.showSnack('Transaction deleted');
  }

  Future<void> _openFilters() async {
    final result = await showModalBottomSheet<TransactionFilter>(
      context: context,
      isScrollControlled: true,
      builder: (_) => _FilterSheet(initial: _filter),
    );
    if (result != null) setState(() => _filter = result);
  }
}

class _SummaryBar extends StatelessWidget {
  const _SummaryBar({required this.summary, required this.currency});
  final PeriodSummary summary;
  final String currency;

  @override
  Widget build(BuildContext context) {
    Widget stat(String label, double value, Color color) => Expanded(
          child: Column(
            children: [
              Text(label, style: context.text.labelSmall?.copyWith(color: context.colors.onSurfaceVariant)),
              const SizedBox(height: 2),
              Text(
                Money.format(value, currency, compact: true),
                style: context.text.titleSmall?.copyWith(color: color),
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
              ),
            ],
          ),
        );
    return AppCard(
      padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 8),
      child: Row(
        children: [
          stat('Income', summary.income, AppTheme.income),
          Container(width: 1, height: 28, color: context.colors.outlineVariant),
          stat('Expenses', summary.expense, AppTheme.expense),
          Container(width: 1, height: 28, color: context.colors.outlineVariant),
          stat('Net', summary.net, summary.net >= 0 ? AppTheme.income : AppTheme.expense),
        ],
      ),
    );
  }
}

class _FilterSheet extends ConsumerStatefulWidget {
  const _FilterSheet({required this.initial});
  final TransactionFilter initial;

  @override
  ConsumerState<_FilterSheet> createState() => _FilterSheetState();
}

class _FilterSheetState extends ConsumerState<_FilterSheet> {
  late TransactionFilter _f = widget.initial;

  @override
  Widget build(BuildContext context) {
    final categories = (ref.watch(categoriesProvider).value ?? const []).where((c) => c.parentId == null).toList();
    final accounts = ref.watch(accountsProvider).value ?? const [];
    final household = ref.watch(activeHouseholdProvider).value;
    final tags = ref.watch(tagSuggestionsProvider);

    Widget section(String title, List<Widget> chips) => Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Padding(padding: const EdgeInsets.only(top: 14, bottom: 8), child: Text(title, style: context.text.titleSmall)),
            Wrap(spacing: 8, runSpacing: 8, children: chips),
          ],
        );

    return DraggableScrollableSheet(
      expand: false,
      initialChildSize: 0.75,
      maxChildSize: 0.95,
      builder: (context, controller) => Column(
        children: [
          Expanded(
            child: ListView(
              controller: controller,
              padding: const EdgeInsets.fromLTRB(20, 0, 20, 12),
              children: [
                Text('Filters', style: context.text.titleLarge),
                section('Type', [
                  for (final t in TransactionType.values)
                    FilterChip(
                      label: Text(t.label),
                      selected: _f.types.contains(t),
                      onSelected: (v) => setState(() {
                        final s = {..._f.types};
                        v ? s.add(t) : s.remove(t);
                        _f = _f.copyWith(types: s);
                      }),
                    ),
                ]),
                section('Category', [
                  for (final c in categories)
                    FilterChip(
                      // The checkmark replaces the colour dot once selected.
                      avatar: _f.categoryIds.contains(c.id) ? null : Icon(Icons.circle, size: 10, color: Color(c.color)),
                      label: Text(c.name),
                      selected: _f.categoryIds.contains(c.id),
                      onSelected: (v) => setState(() {
                        final s = {..._f.categoryIds};
                        v ? s.add(c.id) : s.remove(c.id);
                        _f = _f.copyWith(categoryIds: s);
                      }),
                    ),
                ]),
                section('Account', [
                  for (final a in accounts)
                    FilterChip(
                      label: Text(a.name),
                      selected: _f.accountIds.contains(a.id),
                      onSelected: (v) => setState(() {
                        final s = {..._f.accountIds};
                        v ? s.add(a.id) : s.remove(a.id);
                        _f = _f.copyWith(accountIds: s);
                      }),
                    ),
                ]),
                if (household != null && household.isShared)
                  section('Member', [
                    for (final m in household.sortedMembers)
                      FilterChip(
                        avatar: MemberAvatar(initials: m.initials, color: m.color, size: 20),
                        label: Text(m.name),
                        selected: _f.memberIds.contains(m.uid),
                        onSelected: (v) => setState(() {
                          final s = {..._f.memberIds};
                          v ? s.add(m.uid) : s.remove(m.uid);
                          _f = _f.copyWith(memberIds: s);
                        }),
                      ),
                  ]),
                if (tags.isNotEmpty)
                  section('Tags', [
                    for (final t in tags)
                      FilterChip(
                        label: Text('#$t'),
                        selected: _f.tags.contains(t),
                        onSelected: (v) => setState(() {
                          final s = {..._f.tags};
                          v ? s.add(t) : s.remove(t);
                          _f = _f.copyWith(tags: s);
                        }),
                      ),
                  ]),
                section('Other', [
                  FilterChip(
                    avatar: const Icon(Icons.attach_file_rounded, size: 16),
                    label: const Text('Has receipt'),
                    selected: _f.onlyWithReceipts,
                    onSelected: (v) => setState(() => _f = _f.copyWith(onlyWithReceipts: v)),
                  ),
                ]),
              ],
            ),
          ),
          SafeArea(
            minimum: const EdgeInsets.fromLTRB(20, 8, 20, 16),
            child: Row(
              children: [
                Expanded(
                  child: OutlinedButton(
                    onPressed: () => setState(() => _f = const TransactionFilter()),
                    child: const Text('Reset'),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  flex: 2,
                  child: FilledButton(onPressed: () => Navigator.pop(context, _f), child: const Text('Apply')),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
