import 'package:flutter_animate/flutter_animate.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:material_ui/material_ui.dart';

import '../../core/constants/app_icons.dart';
import '../../core/theme/app_theme.dart';
import '../../core/utils/date_utils.dart';
import '../../core/utils/extensions.dart';
import '../../core/utils/money.dart';
import '../../core/widgets/widgets.dart';
import '../../models/models.dart';
import '../analytics/analytics_engine.dart';
import '../analytics/widgets/charts.dart';
import '../auth/auth_providers.dart';
import '../household/household_providers.dart';
import '../transactions/widgets/transaction_tile.dart';
import 'period_selector.dart';

class DashboardScreen extends ConsumerWidget {
  const DashboardScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final profile = ref.watch(userProfileProvider).value;
    final household = ref.watch(activeHouseholdProvider).value;
    final txAsync = ref.watch(allTransactionsProvider);
    final currency = ref.watch(baseCurrencyProvider);
    final range = ref.watch(selectedPeriodProvider);
    final summary = ref.watch(periodSummaryProvider);
    final periodTx = ref.watch(periodTransactionsProvider);
    final all = txAsync.value ?? const [];
    final categories = ref.watch(categoryMapProvider);
    final budgets = ref.watch(budgetProgressProvider);
    final goals = (ref.watch(goalsProvider).value ?? const []).where((g) => !g.isCompleted).toList();
    final activity = ref.watch(activityProvider).value ?? const [];
    final netWorth = ref.watch(netWorthProvider);
    final settings = ref.watch(appSettingsProvider);

    final greeting = _greeting();
    final firstName = (profile?.displayName ?? '').split(' ').first;
    final categorySpend = AnalyticsEngine.byCategory(periodTx, categories);
    final daily = AnalyticsEngine.dailySeries(all, range);
    final comparison = AnalyticsEngine.compareExpense(all, range);
    final insights = AnalyticsEngine.insights(
      txs: all,
      range: range,
      categories: categories,
      budgets: budgets,
      money: (v) => Money.format(v, currency, compact: true),
    );
    final recent = periodTx.take(5).toList();

    return Scaffold(
      body: RefreshIndicator(
        onRefresh: () async {
          ref.invalidate(ratesProvider);
          await Future<void>.delayed(const Duration(milliseconds: 400));
        },
        child: CustomScrollView(
          slivers: [
            SliverAppBar(
              pinned: true,
              toolbarHeight: 64,
              title: Row(
                children: [
                  GestureDetector(
                    onTap: () => context.push('/family'),
                    child: MemberAvatar(
                      initials: profile?.initials ?? '?',
                      color: household?.members[profile?.uid]?.color ?? kPalette[9],
                      photoUrl: profile?.photoUrl,
                      size: 40,
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Text(
                          '$greeting${firstName.isEmpty ? '' : ', $firstName'}',
                          style: context.text.titleMedium,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                        ),
                        Text(
                          household?.name ?? '',
                          style: context.text.bodySmall?.copyWith(color: context.colors.onSurfaceVariant),
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                        ),
                      ],
                    ),
                  ),
                ],
              ),
              actions: [
                IconButton(
                  tooltip: settings.hideAmounts ? 'Show amounts' : 'Hide amounts',
                  icon: Icon(settings.hideAmounts ? Icons.visibility_off_outlined : Icons.visibility_outlined),
                  onPressed: () => ref.read(appSettingsProvider.notifier).setHideAmounts(!settings.hideAmounts),
                ),
                IconButton(
                  tooltip: 'Search',
                  icon: const Icon(Icons.search_rounded),
                  onPressed: () => context.push('/search'),
                ),
                const SizedBox(width: 4),
              ],
            ),
            SliverToBoxAdapter(
              child: Padding(
                padding: const EdgeInsets.fromLTRB(16, 4, 16, 0),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    const PeriodSelector(),
                    const SizedBox(height: 12),
                    _HeroCard(
                      netWorth: netWorth,
                      summary: summary,
                      comparison: comparison,
                      currency: currency,
                      hide: settings.hideAmounts,
                      loading: txAsync.isLoading && !txAsync.hasValue,
                    ).animate().fadeIn(duration: 350.ms).slideY(begin: 0.04, end: 0),
                    const SizedBox(height: 16),
                    if (budgets.isNotEmpty) ...[
                      SectionHeader(
                        title: 'Budgets',
                        subtitle: '${budgets.where((b) => b.status != BudgetStatus.over).length} of ${budgets.length} on track',
                        actionLabel: 'See all',
                        onAction: () => context.go('/budgets'),
                      ),
                      _BudgetStrip(budgets: budgets.take(3).toList(), currency: currency, hide: settings.hideAmounts),
                      const SizedBox(height: 16),
                    ],
                    SectionHeader(
                      title: 'Spending trend',
                      subtitle: range.label(),
                      actionLabel: 'Insights',
                      onAction: () => context.go('/insights'),
                    ),
                    AppCard(
                      padding: const EdgeInsets.fromLTRB(8, 16, 16, 8),
                      child: daily.every((p) => p.expense == 0)
                          ? const EmptyState(
                              icon: Icons.show_chart_rounded,
                              title: 'No spending recorded',
                              message: 'Your daily trend appears once you add expenses.',
                              compact: true,
                            )
                          : DailySpendChart(points: daily, currency: currency),
                    ),
                    const SizedBox(height: 16),
                    if (categorySpend.isNotEmpty) ...[
                      const SectionHeader(title: 'Top categories'),
                      _CategoryStrip(slices: categorySpend.take(6).toList(), currency: currency, hide: settings.hideAmounts),
                      const SizedBox(height: 16),
                    ],
                    const SectionHeader(title: 'Insights'),
                    _InsightCarousel(insights: insights),
                    const SizedBox(height: 16),
                    if (goals.isNotEmpty) ...[
                      SectionHeader(
                        title: 'Savings goals',
                        actionLabel: 'See all',
                        onAction: () => context.push('/goals'),
                      ),
                      _GoalStrip(goals: goals, currency: currency, hide: settings.hideAmounts),
                      const SizedBox(height: 16),
                    ],
                    SectionHeader(
                      title: 'Recent transactions',
                      actionLabel: 'See all',
                      onAction: () => context.go('/transactions'),
                    ),
                    if (recent.isEmpty)
                      AppCard(
                        child: EmptyState(
                          icon: Icons.receipt_long_rounded,
                          title: 'Nothing here yet',
                          message: 'Tap Add to record your first expense for ${range.label()}.',
                          compact: true,
                          actionLabel: 'Add transaction',
                          onAction: () => context.push('/transactions/new'),
                        ),
                      )
                    else
                      AppCard(
                        padding: const EdgeInsets.symmetric(vertical: 4),
                        child: Column(
                          children: [for (final t in recent) TransactionTile(transaction: t, showDate: true)],
                        ),
                      ),
                    if (household != null && household.isShared && activity.isNotEmpty) ...[
                      const SizedBox(height: 16),
                      SectionHeader(
                        title: 'Family activity',
                        actionLabel: 'See all',
                        onAction: () => context.push('/family/activity'),
                      ),
                      AppCard(
                        padding: const EdgeInsets.symmetric(vertical: 4),
                        child: Column(
                          children: [
                            for (final a in activity.take(3))
                              ListTile(
                                leading: MemberAvatar(
                                  initials: a.actorName.isEmpty ? '?' : a.actorName[0],
                                  color: household.members[a.actorId]?.color ?? kPalette[15],
                                  photoUrl: household.members[a.actorId]?.photoUrl,
                                ),
                                title: Text(a.summary, style: context.text.bodyMedium, maxLines: 2),
                                subtitle: Text(AppDates.timeAgo(a.at), style: context.text.labelSmall),
                              ),
                          ],
                        ),
                      ),
                    ],
                    const SizedBox(height: 100),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  static String _greeting() {
    final h = DateTime.now().hour;
    if (h < 12) return 'Good morning';
    if (h < 17) return 'Good afternoon';
    return 'Good evening';
  }
}

class _HeroCard extends StatelessWidget {
  const _HeroCard({
    required this.netWorth,
    required this.summary,
    required this.comparison,
    required this.currency,
    required this.hide,
    required this.loading,
  });

  final double netWorth;
  final PeriodSummary summary;
  final Comparison comparison;
  final String currency;
  final bool hide;
  final bool loading;

  String _m(double v) => hide ? '••••••' : Money.format(v, currency);

  @override
  Widget build(BuildContext context) {
    final scheme = context.colors;
    final pct = comparison.percent;
    final up = (pct ?? 0) > 0;
    return AppCard(
      padding: const EdgeInsets.all(20),
      gradient: LinearGradient(
        colors: [scheme.primary, Color.lerp(scheme.primary, scheme.tertiary, 0.6)!],
        begin: Alignment.topLeft,
        end: Alignment.bottomRight,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.account_balance_wallet_rounded, color: Colors.white.withValues(alpha: 0.9), size: 18),
              const SizedBox(width: 6),
              Text(
                'Total balance',
                style: context.text.labelLarge?.copyWith(color: Colors.white.withValues(alpha: 0.85)),
              ),
              const Spacer(),
              if (loading)
                const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white)),
            ],
          ),
          const SizedBox(height: 6),
          Text(
            _m(netWorth),
            style: context.text.displaySmall?.copyWith(
              color: Colors.white,
              fontFeatures: const [FontFeature.tabularFigures()],
            ),
          ),
          const SizedBox(height: 18),
          Row(
            children: [
              Expanded(
                child: _HeroStat(
                  label: 'Income',
                  value: _m(summary.income),
                  icon: Icons.south_west_rounded,
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: _HeroStat(
                  label: 'Expenses',
                  value: _m(summary.expense),
                  icon: Icons.north_east_rounded,
                  trailing: pct == null || hide
                      ? null
                      : Text(
                          '${up ? '▲' : '▼'} ${(pct.abs() * 100).round()}%',
                          style: context.text.labelSmall?.copyWith(
                            color: Colors.white,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Row(
            children: [
              Icon(
                summary.net >= 0 ? Icons.savings_rounded : Icons.warning_amber_rounded,
                color: Colors.white.withValues(alpha: 0.9),
                size: 16,
              ),
              const SizedBox(width: 6),
              Expanded(
                child: Text(
                  summary.income <= 0
                      ? 'Net this period: ${_m(summary.net)}'
                      : summary.net >= 0
                          ? 'Saved ${_m(summary.net)} · ${Money.percent(summary.savingsRate)} of income'
                          : 'Overspent by ${_m(-summary.net)} this period',
                  style: context.text.bodySmall?.copyWith(color: Colors.white.withValues(alpha: 0.9)),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _HeroStat extends StatelessWidget {
  const _HeroStat({required this.label, required this.value, required this.icon, this.trailing});
  final String label;
  final String value;
  final IconData icon;
  final Widget? trailing;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.16),
        borderRadius: BorderRadius.circular(14),
      ),
      child: Row(
        children: [
          Container(
            width: 28,
            height: 28,
            decoration: BoxDecoration(color: Colors.white.withValues(alpha: 0.2), shape: BoxShape.circle),
            child: Icon(icon, size: 16, color: Colors.white),
          ),
          const SizedBox(width: 8),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(label, style: context.text.labelSmall?.copyWith(color: Colors.white.withValues(alpha: 0.8))),
                Text(
                  value,
                  style: context.text.titleSmall?.copyWith(color: Colors.white),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
              ],
            ),
          ),
          ?trailing,
        ],
      ),
    );
  }
}

class _BudgetStrip extends StatelessWidget {
  const _BudgetStrip({required this.budgets, required this.currency, required this.hide});
  final List<BudgetProgress> budgets;
  final String currency;
  final bool hide;

  @override
  Widget build(BuildContext context) {
    return AppCard(
      padding: const EdgeInsets.fromLTRB(16, 12, 16, 12),
      child: Column(
        children: [
          for (final b in budgets)
            InkWell(
              onTap: () => context.push('/budgets/${b.budget.id}'),
              borderRadius: BorderRadius.circular(10),
              child: Padding(
                padding: const EdgeInsets.symmetric(vertical: 6),
                child: Column(
                  children: [
                    Row(
                      children: [
                        Expanded(child: Text(b.budget.name, style: context.text.titleSmall, maxLines: 1, overflow: TextOverflow.ellipsis)),
                        Text(
                          hide
                              ? '••••'
                              : '${Money.format(b.spent, currency, compact: true)} / ${Money.format(b.limit, currency, compact: true)}',
                          style: context.text.labelMedium?.copyWith(color: budgetColor(b.status), fontWeight: FontWeight.w700),
                        ),
                      ],
                    ),
                    const SizedBox(height: 6),
                    BudgetBar(fraction: b.fraction, color: budgetColor(b.status)),
                  ],
                ),
              ),
            ),
        ],
      ),
    );
  }
}

class _CategoryStrip extends StatelessWidget {
  const _CategoryStrip({required this.slices, required this.currency, required this.hide});
  final List<CategorySpend> slices;
  final String currency;
  final bool hide;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: 118,
      child: ListView.separated(
        scrollDirection: Axis.horizontal,
        itemCount: slices.length,
        separatorBuilder: (_, _) => const SizedBox(width: 10),
        itemBuilder: (context, i) {
          final s = slices[i];
          return SizedBox(
            width: 132,
            child: AppCard(
              padding: const EdgeInsets.all(12),
              onTap: () => context.go('/insights'),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Row(
                    children: [
                      IconBadge(iconKey: s.iconKey, color: s.color, size: 32),
                      const Spacer(),
                      Text(
                        Money.percent(s.share),
                        style: context.text.labelSmall?.copyWith(color: Color(s.color), fontWeight: FontWeight.w700),
                      ),
                    ],
                  ),
                  Text(s.name, style: context.text.labelMedium, maxLines: 1, overflow: TextOverflow.ellipsis),
                  Text(
                    hide ? '••••' : Money.format(s.amount, currency, compact: true),
                    style: context.text.titleSmall,
                  ),
                ],
              ),
            ),
          ).animate(delay: (60 * i).ms).fadeIn(duration: 300.ms).slideX(begin: 0.1, end: 0);
        },
      ),
    );
  }
}

class _InsightCarousel extends StatelessWidget {
  const _InsightCarousel({required this.insights});
  final List<Insight> insights;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: 124,
      child: ListView.separated(
        scrollDirection: Axis.horizontal,
        itemCount: insights.length,
        separatorBuilder: (_, _) => const SizedBox(width: 10),
        itemBuilder: (context, i) {
          final ins = insights[i];
          final color = switch (ins.tone) {
            InsightTone.positive => AppTheme.income,
            InsightTone.warning => AppTheme.warning,
            InsightTone.neutral => context.colors.primary,
          };
          return SizedBox(
            width: 250,
            child: AppCard(
              padding: const EdgeInsets.all(14),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  IconBadge(iconKey: ins.iconKey, color: color.argb, size: 36),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(ins.title, style: context.text.titleSmall, maxLines: 2, overflow: TextOverflow.ellipsis),
                        const SizedBox(height: 4),
                        Text(
                          ins.body,
                          style: context.text.bodySmall?.copyWith(color: context.colors.onSurfaceVariant),
                          maxLines: 3,
                          overflow: TextOverflow.ellipsis,
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          );
        },
      ),
    );
  }
}

class _GoalStrip extends StatelessWidget {
  const _GoalStrip({required this.goals, required this.currency, required this.hide});
  final List<Goal> goals;
  final String currency;
  final bool hide;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: 96,
      child: ListView.separated(
        scrollDirection: Axis.horizontal,
        itemCount: goals.length,
        separatorBuilder: (_, _) => const SizedBox(width: 10),
        itemBuilder: (context, i) {
          final g = goals[i];
          return SizedBox(
            width: 220,
            child: AppCard(
              padding: const EdgeInsets.all(12),
              onTap: () => context.push('/goals'),
              child: Row(
                children: [
                  ProgressRing(
                    fraction: g.progress,
                    color: Color(g.color),
                    size: 56,
                    child: Icon(iconFor(g.iconKey), color: Color(g.color), size: 20),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(g.name, style: context.text.titleSmall, maxLines: 1, overflow: TextOverflow.ellipsis),
                        Text(
                          hide ? '••••' : '${Money.format(g.savedAmount, currency, compact: true)} of ${Money.format(g.targetAmount, currency, compact: true)}',
                          style: context.text.bodySmall?.copyWith(color: context.colors.onSurfaceVariant),
                        ),
                        Text(
                          Money.percent(g.progress),
                          style: context.text.labelSmall?.copyWith(color: Color(g.color), fontWeight: FontWeight.w700),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          );
        },
      ),
    );
  }
}
