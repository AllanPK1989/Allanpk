import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:material_ui/material_ui.dart';

import '../../core/utils/extensions.dart';
import '../../core/utils/money.dart';
import '../../core/widgets/widgets.dart';
import '../analytics/analytics_engine.dart';
import '../analytics/widgets/charts.dart';
import '../household/household_providers.dart';
import '../transactions/widgets/transaction_tile.dart';

class BudgetDetailScreen extends ConsumerWidget {
  const BudgetDetailScreen({super.key, required this.id});
  final String id;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final progress = ref.watch(budgetProgressProvider).where((p) => p.budget.id == id).firstOrNull;
    final currency = ref.watch(baseCurrencyProvider);
    final role = ref.watch(myRoleProvider);
    if (progress == null) {
      return Scaffold(appBar: AppBar(), body: const EmptyState(icon: Icons.search_off_rounded, title: 'Budget not found'));
    }
    final p = progress;
    final color = budgetColor(p.status);
    final daily = AnalyticsEngine.dailySeries(p.transactions, p.range);
    final categories = ref.watch(categoryMapProvider);
    final byCat = AnalyticsEngine.byCategory(p.transactions, categories);

    return Scaffold(
      appBar: AppBar(
        title: Text(p.budget.name),
        actions: [
          if (role.canManageBudgets)
            IconButton(icon: const Icon(Icons.edit_rounded), onPressed: () => context.push('/budgets/$id/edit')),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(16, 4, 16, 40),
        children: [
          AppCard(
            padding: const EdgeInsets.all(20),
            child: Column(
              children: [
                Row(
                  children: [
                    ProgressRing(
                      fraction: p.fraction,
                      color: color,
                      size: 92,
                      strokeWidth: 10,
                      child: Text(Money.percent(p.limit <= 0 ? 0 : p.spent / p.limit), style: context.text.titleMedium),
                    ),
                    const SizedBox(width: 18),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text('Spent', style: context.text.labelMedium?.copyWith(color: context.colors.onSurfaceVariant)),
                          Text(Money.format(p.spent, currency), style: context.text.headlineSmall?.copyWith(color: color)),
                          Text('of ${Money.format(p.limit, currency)}', style: context.text.bodyMedium),
                          const SizedBox(height: 4),
                          Text(p.range.label(), style: context.text.bodySmall?.copyWith(color: context.colors.onSurfaceVariant)),
                        ],
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 16),
                Row(
                  children: [
                    _Stat('Remaining', Money.format(p.remaining, currency, compact: true)),
                    _Stat('Days left', '${p.daysLeft}'),
                    _Stat('Per day', Money.format(p.dailyAllowance, currency, compact: true)),
                    _Stat('Projected', Money.format(p.projectedTotal, currency, compact: true)),
                  ],
                ),
              ],
            ),
          ),
          const SizedBox(height: 14),
          AppCard(
            padding: const EdgeInsets.all(14),
            child: Row(
              children: [
                Icon(
                  p.spent <= p.expectedByNow ? Icons.thumb_up_alt_outlined : Icons.speed_rounded,
                  color: p.spent <= p.expectedByNow ? budgetColor(BudgetStatus.onTrack) : budgetColor(BudgetStatus.warning),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Text(
                    p.spent <= p.expectedByNow
                        ? 'You are ${Money.format(p.expectedByNow - p.spent, currency, compact: true)} under the even-pace line. Keep it up.'
                        : 'You are ${Money.format(p.spent - p.expectedByNow, currency, compact: true)} ahead of the even-pace line. '
                            'Slow down to ${Money.format(p.dailyAllowance, currency, compact: true)} a day.',
                    style: context.text.bodyMedium,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 14),
          const SectionHeader(title: 'Cumulative spend'),
          AppCard(
            padding: const EdgeInsets.fromLTRB(8, 16, 16, 8),
            child: DailySpendChart(points: daily, currency: currency, cumulative: true),
          ),
          if (byCat.length > 1) ...[
            const SizedBox(height: 14),
            const SectionHeader(title: 'Breakdown'),
            AppCard(
              child: Column(
                children: [
                  for (final c in byCat.take(8))
                    Padding(
                      padding: const EdgeInsets.symmetric(vertical: 6),
                      child: Row(
                        children: [
                          IconBadge(iconKey: c.iconKey, color: c.color, size: 32),
                          const SizedBox(width: 10),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(c.name, style: context.text.labelLarge),
                                const SizedBox(height: 4),
                                BudgetBar(fraction: c.share, color: Color(c.color), height: 5),
                              ],
                            ),
                          ),
                          const SizedBox(width: 10),
                          Text(Money.format(c.amount, currency, compact: true), style: context.text.labelLarge),
                        ],
                      ),
                    ),
                ],
              ),
            ),
          ],
          const SizedBox(height: 14),
          SectionHeader(title: 'Transactions', subtitle: '${p.transactions.length} in this period'),
          if (p.transactions.isEmpty)
            const AppCard(child: EmptyState(icon: Icons.receipt_long_rounded, title: 'Nothing spent yet', compact: true))
          else
            AppCard(
              padding: const EdgeInsets.symmetric(vertical: 4),
              child: Column(children: [for (final t in p.transactions.take(30)) TransactionTile(transaction: t, showDate: true)]),
            ),
        ],
      ),
    );
  }
}

class _Stat extends StatelessWidget {
  const _Stat(this.label, this.value);
  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Expanded(
      child: Column(
        children: [
          Text(label, style: context.text.labelSmall?.copyWith(color: context.colors.onSurfaceVariant)),
          const SizedBox(height: 2),
          Text(value, style: context.text.labelLarge, maxLines: 1, overflow: TextOverflow.ellipsis),
        ],
      ),
    );
  }
}
