import 'package:flutter_animate/flutter_animate.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:material_ui/material_ui.dart';

import '../../core/utils/extensions.dart';
import '../../core/utils/money.dart';
import '../../core/widgets/widgets.dart';
import '../analytics/analytics_engine.dart';
import '../analytics/widgets/charts.dart';
import '../household/household_providers.dart';

class BudgetsScreen extends ConsumerWidget {
  const BudgetsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final budgetsAsync = ref.watch(budgetsProvider);
    final progress = ref.watch(budgetProgressProvider);
    final currency = ref.watch(baseCurrencyProvider);
    final role = ref.watch(myRoleProvider);
    final goals = ref.watch(goalsProvider).value ?? const [];
    final activeGoals = goals.where((g) => !g.isCompleted).length;

    final totalLimit = progress.fold<double>(0, (s, p) => s + p.limit);
    final totalSpent = progress.fold<double>(0, (s, p) => s + p.spent);
    final overall = progress.where((p) => p.budget.isOverall).toList();
    final categoryBudgets = progress.where((p) => !p.budget.isOverall).toList();

    return Scaffold(
      appBar: AppBar(
        title: const Text('Budgets'),
        actions: [
          IconButton(
            tooltip: 'Savings goals',
            icon: Badge(
              isLabelVisible: activeGoals > 0,
              label: Text('$activeGoals'),
              child: const Icon(Icons.savings_outlined),
            ),
            onPressed: () => context.push('/goals'),
          ),
          if (role.canManageBudgets)
            IconButton(
              tooltip: 'New budget',
              icon: const Icon(Icons.add_rounded),
              onPressed: () => context.push('/budgets/new'),
            ),
          const SizedBox(width: 4),
        ],
      ),
      body: budgetsAsync.when(
        loading: () => const LoadingState(),
        error: (e, _) => ErrorState(error: e),
        data: (_) {
          if (progress.isEmpty) {
            return EmptyState(
              icon: Icons.pie_chart_outline_rounded,
              title: 'No budgets yet',
              message: 'Set a monthly limit for a category or your whole household and track it in real time.',
              actionLabel: role.canManageBudgets ? 'Create a budget' : null,
              onAction: () => context.push('/budgets/new'),
            );
          }
          return ListView(
            padding: const EdgeInsets.fromLTRB(16, 4, 16, 110),
            children: [
              AppCard(
                padding: const EdgeInsets.all(18),
                child: Row(
                  children: [
                    ProgressRing(
                      fraction: totalLimit <= 0 ? 0 : totalSpent / totalLimit,
                      color: totalSpent > totalLimit
                          ? budgetColor(BudgetStatus.over)
                          : totalLimit > 0 && totalSpent / totalLimit > 0.8
                              ? budgetColor(BudgetStatus.warning)
                              : budgetColor(BudgetStatus.onTrack),
                      size: 84,
                      strokeWidth: 9,
                      child: Text(
                        totalLimit <= 0 ? '—' : Money.percent(totalSpent / totalLimit),
                        style: context.text.titleMedium,
                      ),
                    ),
                    const SizedBox(width: 18),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text('All budgets', style: context.text.labelMedium?.copyWith(color: context.colors.onSurfaceVariant)),
                          Text(Money.format(totalSpent, currency), style: context.text.headlineSmall),
                          Text(
                            'of ${Money.format(totalLimit, currency)} · ${Money.format((totalLimit - totalSpent).clamp(0, double.infinity), currency, compact: true)} left',
                            style: context.text.bodySmall?.copyWith(color: context.colors.onSurfaceVariant),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ).animate().fadeIn(duration: 300.ms),
              if (overall.isNotEmpty) ...[
                const SectionHeader(title: 'Overall'),
                for (final p in overall) _BudgetCard(progress: p, currency: currency),
              ],
              if (categoryBudgets.isNotEmpty) ...[
                const SectionHeader(title: 'By category'),
                for (final p in categoryBudgets) _BudgetCard(progress: p, currency: currency),
              ],
            ],
          );
        },
      ),
    );
  }
}

class _BudgetCard extends ConsumerWidget {
  const _BudgetCard({required this.progress, required this.currency});
  final BudgetProgress progress;
  final String currency;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final p = progress;
    final color = budgetColor(p.status);
    final categories = ref.watch(categoryMapProvider);
    final firstCat = p.budget.categoryIds.isEmpty ? null : categories[p.budget.categoryIds.first];
    final statusText = switch (p.status) {
      BudgetStatus.over => '${Money.format(p.spent - p.limit, currency, compact: true)} over',
      BudgetStatus.warning => '${Money.format(p.remaining, currency, compact: true)} left',
      BudgetStatus.onTrack => '${Money.format(p.remaining, currency, compact: true)} left',
    };
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: AppCard(
        onTap: () => context.push('/budgets/${p.budget.id}'),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                IconBadge(
                  iconKey: firstCat?.iconKey ?? 'account_balance_wallet',
                  color: firstCat?.color ?? p.budget.color,
                  size: 42,
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(p.budget.name, style: context.text.titleSmall, maxLines: 1, overflow: TextOverflow.ellipsis),
                      Text(
                        '${p.budget.period.label} · ${p.daysLeft} ${p.daysLeft == 1 ? 'day' : 'days'} left'
                        '${p.budget.rollover ? ' · rollover' : ''}',
                        style: context.text.bodySmall?.copyWith(color: context.colors.onSurfaceVariant),
                      ),
                    ],
                  ),
                ),
                Column(
                  crossAxisAlignment: CrossAxisAlignment.end,
                  children: [
                    Text(Money.format(p.spent, currency, compact: true), style: context.text.titleSmall?.copyWith(color: color)),
                    Text(
                      'of ${Money.format(p.limit, currency, compact: true)}',
                      style: context.text.labelSmall?.copyWith(color: context.colors.onSurfaceVariant),
                    ),
                  ],
                ),
              ],
            ),
            const SizedBox(height: 12),
            BudgetBar(fraction: p.fraction, color: color),
            const SizedBox(height: 8),
            Row(
              children: [
                Icon(
                  p.status == BudgetStatus.over ? Icons.error_outline_rounded : Icons.check_circle_outline_rounded,
                  size: 14,
                  color: color,
                ),
                const SizedBox(width: 4),
                Text(statusText, style: context.text.labelSmall?.copyWith(color: color, fontWeight: FontWeight.w700)),
                const Spacer(),
                if (p.daysLeft > 0 && p.remaining > 0)
                  Text(
                    '${Money.format(p.dailyAllowance, currency, compact: true)}/day to stay on track',
                    style: context.text.labelSmall?.copyWith(color: context.colors.onSurfaceVariant),
                  ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
