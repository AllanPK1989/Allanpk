import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:material_ui/material_ui.dart';

import '../../core/utils/extensions.dart';
import '../../core/utils/money.dart';
import '../../core/widgets/widgets.dart';
import '../../models/models.dart';
import '../analytics/analytics_engine.dart';
import '../household/household_providers.dart';

class CategoriesScreen extends ConsumerStatefulWidget {
  const CategoriesScreen({super.key});

  @override
  ConsumerState<CategoriesScreen> createState() => _CategoriesScreenState();
}

class _CategoriesScreenState extends ConsumerState<CategoriesScreen> {
  CategoryKind _kind = CategoryKind.expense;
  bool _showArchived = false;

  @override
  Widget build(BuildContext context) {
    final all = ref.watch(categoriesProvider).value ?? const [];
    final txs = ref.watch(allTransactionsProvider).value ?? const [];
    final currency = ref.watch(baseCurrencyProvider);
    final role = ref.watch(myRoleProvider);
    final visible = all.where((c) => c.kind == _kind && (_showArchived || !c.isArchived)).toList();
    final parents = visible.where((c) => c.parentId == null).toList();
    final children = <String, List<Category>>{};
    for (final c in visible.where((c) => c.parentId != null)) {
      children.putIfAbsent(c.parentId!, () => []).add(c);
    }
    final spend = {
      for (final s in AnalyticsEngine.byCategory(
        txs,
        {for (final c in all) c.id: c},
        type: _kind == CategoryKind.expense ? TransactionType.expense : TransactionType.income,
      ))
        s.categoryId: s,
    };

    return Scaffold(
      appBar: AppBar(
        title: const Text('Categories'),
        actions: [
          IconButton(
            tooltip: _showArchived ? 'Hide archived' : 'Show archived',
            icon: Icon(_showArchived ? Icons.inventory_2_rounded : Icons.inventory_2_outlined),
            onPressed: () => setState(() => _showArchived = !_showArchived),
          ),
          if (role.canManageBudgets)
            IconButton(
              icon: const Icon(Icons.add_rounded),
              onPressed: () => context.push('/categories/new?kind=${_kind.storageKey}'),
            ),
          const SizedBox(width: 4),
        ],
      ),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 4, 16, 8),
            child: SegmentedButton<CategoryKind>(
              segments: const [
                ButtonSegment(value: CategoryKind.expense, label: Text('Expense')),
                ButtonSegment(value: CategoryKind.income, label: Text('Income')),
              ],
              selected: {_kind},
              showSelectedIcon: false,
              onSelectionChanged: (s) => setState(() => _kind = s.first),
            ),
          ),
          Expanded(
            child: role.canManageBudgets
                ? ReorderableListView.builder(
                    padding: const EdgeInsets.fromLTRB(16, 0, 16, 40),
                    buildDefaultDragHandles: false,
                    itemCount: parents.length,
                    onReorderItem: (oldIndex, newIndex) {
                      final reordered = List.of(parents);
                      final item = reordered.removeAt(oldIndex);
                      reordered.insert(newIndex, item);
                      ref.read(ledgerProvider)?.reorderCategories(reordered);
                    },
                    itemBuilder: (context, i) => _CategoryRow(
                      key: ValueKey(parents[i].id),
                      category: parents[i],
                      subcategories: children[parents[i].id] ?? const [],
                      spend: spend,
                      currency: currency,
                      index: i,
                    ),
                  )
                : ListView.builder(
                    padding: const EdgeInsets.fromLTRB(16, 0, 16, 40),
                    itemCount: parents.length,
                    itemBuilder: (context, i) => _CategoryRow(
                      category: parents[i],
                      subcategories: children[parents[i].id] ?? const [],
                      spend: spend,
                      currency: currency,
                      index: null,
                    ),
                  ),
          ),
        ],
      ),
    );
  }
}

class _CategoryRow extends StatelessWidget {
  const _CategoryRow({
    super.key,
    required this.category,
    required this.subcategories,
    required this.spend,
    required this.currency,
    required this.index,
  });

  final Category category;
  final List<Category> subcategories;
  final Map<String?, CategorySpend> spend;
  final String currency;
  final int? index;

  @override
  Widget build(BuildContext context) {
    final c = category;
    final s = spend[c.id];
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: AppCard(
        padding: const EdgeInsets.symmetric(vertical: 4),
        child: Column(
          children: [
            ListTile(
              onTap: () => context.push('/categories/${c.id}/edit'),
              leading: IconBadge(iconKey: c.iconKey, color: c.color, size: 42),
              title: Text(c.name, style: context.text.titleSmall?.copyWith(decoration: c.isArchived ? TextDecoration.lineThrough : null)),
              subtitle: Text(
                s == null ? 'No transactions yet' : '${s.count} transactions · ${Money.format(s.amount, currency, compact: true)} all time',
                style: context.text.bodySmall?.copyWith(color: context.colors.onSurfaceVariant),
              ),
              trailing: index == null
                  ? null
                  : ReorderableDragStartListener(index: index!, child: const Icon(Icons.drag_handle_rounded)),
            ),
            for (final sub in subcategories)
              ListTile(
                dense: true,
                contentPadding: const EdgeInsets.only(left: 40, right: 16),
                onTap: () => context.push('/categories/${sub.id}/edit'),
                leading: IconBadge(iconKey: sub.iconKey, color: sub.color, size: 30),
                title: Text(sub.name, style: TextStyle(decoration: sub.isArchived ? TextDecoration.lineThrough : null)),
                trailing: Text(
                  spend[sub.id] == null ? '' : Money.format(spend[sub.id]!.amount, currency, compact: true),
                  style: context.text.labelMedium,
                ),
              ),
          ],
        ),
      ),
    );
  }
}
