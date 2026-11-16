import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:material_ui/material_ui.dart';

import '../../core/theme/app_theme.dart';
import '../../core/utils/date_utils.dart';
import '../../core/utils/extensions.dart';
import '../../core/utils/money.dart';
import '../../core/widgets/widgets.dart';
import '../../models/models.dart';
import '../home/period_selector.dart';
import '../household/household_providers.dart';
import 'analytics_engine.dart';
import 'widgets/charts.dart';

/// Deep-dive analytics: overview, categories, members and patterns.
class InsightsScreen extends ConsumerStatefulWidget {
  const InsightsScreen({super.key});

  @override
  ConsumerState<InsightsScreen> createState() => _InsightsScreenState();
}

class _InsightsScreenState extends ConsumerState<InsightsScreen> with SingleTickerProviderStateMixin {
  late final TabController _tabs = TabController(length: 4, vsync: this);
  int? _selectedSlice;
  TransactionType _breakdownType = TransactionType.expense;

  @override
  void dispose() {
    _tabs.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final txAsync = ref.watch(allTransactionsProvider);
    return Scaffold(
      appBar: AppBar(
        title: const Text('Insights'),
        actions: [
          IconButton(
            tooltip: 'Reports',
            icon: const Icon(Icons.picture_as_pdf_outlined),
            onPressed: () => context.push('/reports'),
          ),
          const SizedBox(width: 4),
        ],
        bottom: TabBar(
          controller: _tabs,
          isScrollable: true,
          tabAlignment: TabAlignment.start,
          tabs: const [Tab(text: 'Overview'), Tab(text: 'Categories'), Tab(text: 'Members'), Tab(text: 'Patterns')],
        ),
      ),
      body: txAsync.when(
        loading: () => const LoadingState(),
        error: (e, _) => ErrorState(error: e),
        data: (all) => Column(
          children: [
            const Padding(padding: EdgeInsets.fromLTRB(16, 8, 16, 0), child: PeriodSelector()),
            Expanded(
              child: TabBarView(
                controller: _tabs,
                children: [
                  _OverviewTab(all: all),
                  _CategoriesTab(
                    all: all,
                    selected: _selectedSlice,
                    type: _breakdownType,
                    onSelect: (i) => setState(() => _selectedSlice = i),
                    onType: (t) => setState(() {
                      _breakdownType = t;
                      _selectedSlice = null;
                    }),
                  ),
                  _MembersTab(all: all),
                  _PatternsTab(all: all),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _OverviewTab extends ConsumerWidget {
  const _OverviewTab({required this.all});
  final List<Transaction> all;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final range = ref.watch(selectedPeriodProvider);
    final currency = ref.watch(baseCurrencyProvider);
    final categories = ref.watch(categoryMapProvider);
    final budgets = ref.watch(budgetProgressProvider);
    final summary = AnalyticsEngine.summarize(all, range);
    final previous = AnalyticsEngine.summarize(all, range.previous());
    final daily = AnalyticsEngine.dailySeries(all, range);
    final prevDaily = AnalyticsEngine.dailySeries(all, range.previous());
    final months = AnalyticsEngine.monthlySeries(all, endMonth: range.end, months: 6);
    final forecast = AnalyticsEngine.forecast(all, range, DateTime.now());
    final insights = AnalyticsEngine.insights(
      txs: all,
      range: range,
      categories: categories,
      budgets: budgets,
      money: (v) => Money.format(v, currency, compact: true),
    );

    Widget delta(double current, double prev, {bool lowerIsBetter = true}) {
      if (prev == 0) return const SizedBox.shrink();
      final pct = (current - prev) / prev;
      final good = lowerIsBetter ? pct <= 0 : pct >= 0;
      return Text(
        '${pct >= 0 ? '▲' : '▼'} ${(pct.abs() * 100).round()}% vs prev',
        style: context.text.labelSmall?.copyWith(color: good ? AppTheme.income : AppTheme.expense, fontWeight: FontWeight.w700),
      );
    }

    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 12, 16, 110),
      children: [
        Row(
          children: [
            Expanded(
              child: _StatCard(
                label: 'Income',
                value: Money.format(summary.income, currency, compact: true),
                color: AppTheme.income,
                icon: Icons.south_west_rounded,
                footer: delta(summary.income, previous.income, lowerIsBetter: false),
              ),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: _StatCard(
                label: 'Expenses',
                value: Money.format(summary.expense, currency, compact: true),
                color: AppTheme.expense,
                icon: Icons.north_east_rounded,
                footer: delta(summary.expense, previous.expense),
              ),
            ),
          ],
        ),
        const SizedBox(height: 10),
        Row(
          children: [
            Expanded(
              child: _StatCard(
                label: 'Net savings',
                value: Money.format(summary.net, currency, compact: true),
                color: summary.net >= 0 ? AppTheme.income : AppTheme.expense,
                icon: Icons.savings_outlined,
                footer: Text(
                  summary.income > 0 ? '${Money.percent(summary.savingsRate)} savings rate' : 'No income recorded',
                  style: context.text.labelSmall?.copyWith(color: context.colors.onSurfaceVariant),
                ),
              ),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: _StatCard(
                label: 'Avg per day',
                value: Money.format(summary.averageDailySpend, currency, compact: true),
                color: context.colors.primary,
                icon: Icons.today_rounded,
                footer: Text(
                  '${summary.transactionCount} transactions',
                  style: context.text.labelSmall?.copyWith(color: context.colors.onSurfaceVariant),
                ),
              ),
            ),
          ],
        ),
        const SizedBox(height: 16),
        const SectionHeader(title: 'Daily spending', subtitle: 'Dashed line: previous period'),
        AppCard(
          padding: const EdgeInsets.fromLTRB(8, 16, 16, 8),
          child: DailySpendChart(points: daily, currency: currency, compareTo: prevDaily, height: 190),
        ),
        const SizedBox(height: 16),
        if (range.contains(DateTime.now()) && forecast.daysRemaining > 0)
          AppCard(
            child: Row(
              children: [
                IconBadge(iconKey: 'trending_up', color: context.colors.primary.argb, size: 40),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('Forecast', style: context.text.titleSmall),
                      Text(
                        'At ${Money.format(forecast.averageDaily, currency, compact: true)} a day you will end this period around '
                        '${Money.format(forecast.projectedTotal, currency, compact: true)} '
                        '(${forecast.daysRemaining} days remaining).',
                        style: context.text.bodySmall?.copyWith(color: context.colors.onSurfaceVariant),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        const SizedBox(height: 16),
        const SectionHeader(title: 'Income vs expenses', subtitle: 'Last 6 months'),
        AppCard(
          padding: const EdgeInsets.fromLTRB(8, 16, 16, 8),
          child: Column(
            children: [
              IncomeExpenseBars(months: months, currency: currency),
              const SizedBox(height: 8),
              const Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  _Legend(color: AppTheme.income, label: 'Income'),
                  SizedBox(width: 16),
                  _Legend(color: AppTheme.expense, label: 'Expenses'),
                ],
              ),
            ],
          ),
        ),
        const SizedBox(height: 16),
        const SectionHeader(title: 'Monthly net'),
        AppCard(
          padding: const EdgeInsets.symmetric(vertical: 6),
          child: Column(
            children: [
              for (final m in months.reversed)
                ListTile(
                  dense: true,
                  title: Text(AppDates.fullMonthYear.format(m.month)),
                  subtitle: Text(
                    'In ${Money.format(m.income, currency, compact: true)} · Out ${Money.format(m.expense, currency, compact: true)}',
                    style: context.text.bodySmall,
                  ),
                  trailing: AmountText(m.net, currency: currency, signed: true, compact: true, style: context.text.titleSmall),
                ),
            ],
          ),
        ),
        const SizedBox(height: 16),
        const SectionHeader(title: 'Observations'),
        for (final ins in insights)
          Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: AppCard(
              padding: const EdgeInsets.all(14),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  IconBadge(
                    iconKey: ins.iconKey,
                    color: switch (ins.tone) {
                      InsightTone.positive => AppTheme.income.argb,
                      InsightTone.warning => AppTheme.warning.argb,
                      InsightTone.neutral => context.colors.primary.argb,
                    },
                    size: 36,
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(ins.title, style: context.text.titleSmall),
                        const SizedBox(height: 2),
                        Text(ins.body, style: context.text.bodySmall?.copyWith(color: context.colors.onSurfaceVariant)),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ),
      ],
    );
  }
}

class _CategoriesTab extends ConsumerWidget {
  const _CategoriesTab({
    required this.all,
    required this.selected,
    required this.type,
    required this.onSelect,
    required this.onType,
  });
  final List<Transaction> all;
  final int? selected;
  final TransactionType type;
  final ValueChanged<int?> onSelect;
  final ValueChanged<TransactionType> onType;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final range = ref.watch(selectedPeriodProvider);
    final currency = ref.watch(baseCurrencyProvider);
    final categories = ref.watch(categoryMapProvider);
    final slices = AnalyticsEngine.byCategory(all, categories, type: type, range: range);
    final prevSlices = {
      for (final s in AnalyticsEngine.byCategory(all, categories, type: type, range: range.previous())) s.categoryId: s.amount,
    };
    final total = slices.fold<double>(0, (s, c) => s + c.amount);
    final selectedSlice = selected != null && selected! < slices.length ? slices[selected!] : null;
    final subs = selectedSlice?.categoryId == null
        ? const <CategorySpend>[]
        : AnalyticsEngine.bySubcategory(AnalyticsEngine.inRange(all, range), categories, selectedSlice!.categoryId!);

    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 12, 16, 110),
      children: [
        SegmentedButton<TransactionType>(
          segments: const [
            ButtonSegment(value: TransactionType.expense, label: Text('Expenses')),
            ButtonSegment(value: TransactionType.income, label: Text('Income')),
          ],
          selected: {type},
          showSelectedIcon: false,
          onSelectionChanged: (s) => onType(s.first),
        ),
        const SizedBox(height: 16),
        if (slices.isEmpty)
          const AppCard(child: EmptyState(icon: Icons.donut_large_rounded, title: 'No data for this period', compact: true))
        else ...[
          AppCard(
            padding: const EdgeInsets.all(20),
            child: Column(
              children: [
                CategoryDonut(
                  slices: slices,
                  currency: currency,
                  total: total,
                  size: 220,
                  selectedIndex: selected,
                  onSelect: onSelect,
                ),
                const SizedBox(height: 8),
                Text(
                  selectedSlice == null ? 'Tap a slice to focus' : 'Tap again or elsewhere to clear',
                  style: context.text.labelSmall?.copyWith(color: context.colors.onSurfaceVariant),
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),
          AppCard(
            padding: const EdgeInsets.symmetric(vertical: 4),
            child: Column(
              children: [
                for (var i = 0; i < slices.length; i++)
                  Builder(
                    builder: (context) {
                      final c = slices[i];
                      final prev = prevSlices[c.categoryId] ?? 0;
                      final pct = prev == 0 ? null : (c.amount - prev) / prev;
                      return ListTile(
                        selected: selected == i,
                        onTap: () => onSelect(selected == i ? null : i),
                        leading: IconBadge(iconKey: c.iconKey, color: c.color, size: 40),
                        title: Text(c.name, style: context.text.titleSmall),
                        subtitle: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const SizedBox(height: 4),
                            BudgetBar(fraction: c.share, color: Color(c.color), height: 5),
                            const SizedBox(height: 4),
                            Text(
                              '${c.count} ${c.count == 1 ? 'transaction' : 'transactions'}'
                              '${pct == null ? '' : ' · ${pct >= 0 ? '▲' : '▼'} ${(pct.abs() * 100).round()}% vs prev'}',
                              style: context.text.labelSmall?.copyWith(color: context.colors.onSurfaceVariant),
                            ),
                          ],
                        ),
                        trailing: Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          crossAxisAlignment: CrossAxisAlignment.end,
                          children: [
                            Text(Money.format(c.amount, currency, compact: true), style: context.text.titleSmall),
                            Text(Money.percent(c.share), style: context.text.labelSmall?.copyWith(color: Color(c.color), fontWeight: FontWeight.w700)),
                          ],
                        ),
                      );
                    },
                  ),
              ],
            ),
          ),
          if (subs.length > 1) ...[
            const SizedBox(height: 16),
            SectionHeader(title: '${selectedSlice!.name} breakdown'),
            AppCard(
              padding: const EdgeInsets.symmetric(vertical: 4),
              child: Column(
                children: [
                  for (final s in subs)
                    ListTile(
                      dense: true,
                      leading: IconBadge(iconKey: s.iconKey, color: s.color, size: 32),
                      title: Text(s.name),
                      trailing: Text('${Money.format(s.amount, currency, compact: true)} · ${Money.percent(s.share)}', style: context.text.labelLarge),
                    ),
                ],
              ),
            ),
          ],
        ],
      ],
    );
  }
}

class _MembersTab extends ConsumerWidget {
  const _MembersTab({required this.all});
  final List<Transaction> all;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final range = ref.watch(selectedPeriodProvider);
    final currency = ref.watch(baseCurrencyProvider);
    final household = ref.watch(activeHouseholdProvider).value;
    final categories = ref.watch(categoryMapProvider);
    if (household == null) return const LoadingState();
    if (!household.isShared) {
      return EmptyState(
        icon: Icons.family_restroom_rounded,
        title: 'Just you for now',
        message: 'Invite family members to compare spending side by side.',
        actionLabel: 'Invite family',
        onAction: () => context.push('/family'),
      );
    }
    final members = AnalyticsEngine.byMember(all, household, range: range);
    final totalExpense = members.fold<double>(0, (s, m) => s + m.expense);
    final periodTx = AnalyticsEngine.inRange(all, range);

    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 12, 16, 110),
      children: [
        if (members.isEmpty)
          const AppCard(child: EmptyState(icon: Icons.people_outline_rounded, title: 'No activity this period', compact: true))
        else ...[
          AppCard(
            padding: const EdgeInsets.fromLTRB(8, 16, 16, 8),
            child: SimpleBars(
              labels: members.map((m) => m.name.split(' ').first).toList(),
              values: members.map((m) => m.expense).toList(),
              colors: members.map((m) => Color(m.color)).toList(),
              currency: currency,
            ),
          ),
          const SizedBox(height: 16),
          for (final m in members)
            Padding(
              padding: const EdgeInsets.only(bottom: 10),
              child: AppCard(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        MemberAvatar(initials: household.members[m.uid]?.initials ?? '?', color: m.color, photoUrl: household.members[m.uid]?.photoUrl, size: 44),
                        const SizedBox(width: 12),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(m.name, style: context.text.titleSmall),
                              Text(
                                '${m.count} ${m.count == 1 ? 'transaction' : 'transactions'} · ${totalExpense == 0 ? '0%' : Money.percent(m.expense / totalExpense)} of spending',
                                style: context.text.bodySmall?.copyWith(color: context.colors.onSurfaceVariant),
                              ),
                            ],
                          ),
                        ),
                        Column(
                          crossAxisAlignment: CrossAxisAlignment.end,
                          children: [
                            Text(Money.format(m.expense, currency, compact: true), style: context.text.titleSmall?.copyWith(color: AppTheme.expense)),
                            if (m.income > 0)
                              Text('+${Money.format(m.income, currency, compact: true)}', style: context.text.labelSmall?.copyWith(color: AppTheme.income)),
                          ],
                        ),
                      ],
                    ),
                    const SizedBox(height: 10),
                    Wrap(
                      spacing: 6,
                      runSpacing: 6,
                      children: [
                        for (final c in AnalyticsEngine.byCategory(periodTx.where((t) => t.createdBy == m.uid), categories).take(4))
                          Chip(
                            avatar: Icon(Icons.circle, size: 10, color: Color(c.color)),
                            label: Text('${c.name} ${Money.format(c.amount, currency, compact: true)}'),
                            visualDensity: VisualDensity.compact,
                          ),
                      ],
                    ),
                  ],
                ),
              ),
            ),
        ],
      ],
    );
  }
}

class _PatternsTab extends ConsumerWidget {
  const _PatternsTab({required this.all});
  final List<Transaction> all;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final range = ref.watch(selectedPeriodProvider);
    final currency = ref.watch(baseCurrencyProvider);
    final accounts = ref.watch(accountMapProvider);
    final weekday = AnalyticsEngine.weekdayAverages(all, range);
    final payees = AnalyticsEngine.topPayees(all, range: range, limit: 8);
    final periodTx = AnalyticsEngine.inRange(all, range);
    final daily = AnalyticsEngine.dailySeries(all, range);
    final maxDay = daily.isEmpty ? null : daily.reduce((a, b) => a.expense >= b.expense ? a : b);
    final noSpendDays = daily.where((d) => d.expense == 0 && !d.date.isAfter(DateTime.now())).length;
    final byAccount = <String, double>{};
    for (final t in periodTx.where((t) => t.isExpense)) {
      byAccount[t.accountId] = (byAccount[t.accountId] ?? 0) + t.amount;
    }
    final accountEntries = byAccount.entries.toList()..sort((a, b) => b.value.compareTo(a.value));
    final expenses = periodTx.where((t) => t.isExpense).toList();
    final small = expenses.where((t) => t.amount < 200).length;
    final large = expenses.where((t) => t.amount >= 5000).length;

    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 12, 16, 110),
      children: [
        const SectionHeader(title: 'Average spend by weekday'),
        AppCard(
          padding: const EdgeInsets.fromLTRB(8, 16, 16, 8),
          child: SimpleBars(
            labels: const ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
            values: weekday,
            currency: currency,
          ),
        ),
        const SizedBox(height: 16),
        Row(
          children: [
            Expanded(
              child: _StatCard(
                label: 'Biggest day',
                value: maxDay == null || maxDay.expense == 0 ? '—' : Money.format(maxDay.expense, currency, compact: true),
                color: AppTheme.expense,
                icon: Icons.local_fire_department_rounded,
                footer: Text(
                  maxDay == null || maxDay.expense == 0 ? '' : AppDates.weekdayDate.format(maxDay.date),
                  style: context.text.labelSmall?.copyWith(color: context.colors.onSurfaceVariant),
                ),
              ),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: _StatCard(
                label: 'No-spend days',
                value: '$noSpendDays',
                color: AppTheme.income,
                icon: Icons.self_improvement_rounded,
                footer: Text('out of ${range.elapsedDays(DateTime.now())} so far', style: context.text.labelSmall?.copyWith(color: context.colors.onSurfaceVariant)),
              ),
            ),
          ],
        ),
        const SizedBox(height: 10),
        Row(
          children: [
            Expanded(
              child: _StatCard(
                label: 'Small purchases',
                value: '$small',
                color: context.colors.primary,
                icon: Icons.coffee_rounded,
                footer: Text('under ${Money.format(200, currency, compact: true)}', style: context.text.labelSmall?.copyWith(color: context.colors.onSurfaceVariant)),
              ),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: _StatCard(
                label: 'Large purchases',
                value: '$large',
                color: AppTheme.warning,
                icon: Icons.diamond_outlined,
                footer: Text('over ${Money.format(5000, currency, compact: true)}', style: context.text.labelSmall?.copyWith(color: context.colors.onSurfaceVariant)),
              ),
            ),
          ],
        ),
        const SizedBox(height: 16),
        if (payees.isNotEmpty) ...[
          const SectionHeader(title: 'Top merchants'),
          AppCard(
            padding: const EdgeInsets.symmetric(vertical: 4),
            child: Column(
              children: [
                for (var i = 0; i < payees.length; i++)
                  ListTile(
                    dense: true,
                    leading: CircleAvatar(
                      radius: 16,
                      backgroundColor: context.colors.primaryContainer,
                      child: Text('${i + 1}', style: context.text.labelLarge),
                    ),
                    title: Text(payees[i].payee),
                    subtitle: Text('${payees[i].count} visits · avg ${Money.format(payees[i].amount / payees[i].count, currency, compact: true)}'),
                    trailing: Text(Money.format(payees[i].amount, currency, compact: true), style: context.text.titleSmall),
                  ),
              ],
            ),
          ),
          const SizedBox(height: 16),
        ],
        if (accountEntries.isNotEmpty) ...[
          const SectionHeader(title: 'Spending by account'),
          AppCard(
            padding: const EdgeInsets.symmetric(vertical: 4),
            child: Column(
              children: [
                for (final e in accountEntries)
                  ListTile(
                    dense: true,
                    leading: IconBadge(iconKey: accounts[e.key]?.resolvedIconKey ?? 'wallet', color: accounts[e.key]?.color ?? 0xFF78909C, size: 34),
                    title: Text(accounts[e.key]?.name ?? 'Unknown account'),
                    trailing: Text(Money.format(e.value, currency, compact: true), style: context.text.titleSmall),
                  ),
              ],
            ),
          ),
        ],
      ],
    );
  }
}

class _StatCard extends StatelessWidget {
  const _StatCard({required this.label, required this.value, required this.color, required this.icon, this.footer});
  final String label;
  final String value;
  final Color color;
  final IconData icon;
  final Widget? footer;

  @override
  Widget build(BuildContext context) {
    return AppCard(
      padding: const EdgeInsets.all(14),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(icon, size: 16, color: color),
              const SizedBox(width: 6),
              Expanded(child: Text(label, style: context.text.labelMedium?.copyWith(color: context.colors.onSurfaceVariant), maxLines: 1, overflow: TextOverflow.ellipsis)),
            ],
          ),
          const SizedBox(height: 6),
          Text(value, style: context.text.titleLarge?.copyWith(color: color), maxLines: 1, overflow: TextOverflow.ellipsis),
          if (footer != null) ...[const SizedBox(height: 2), footer!],
        ],
      ),
    );
  }
}

class _Legend extends StatelessWidget {
  const _Legend({required this.color, required this.label});
  final Color color;
  final String label;

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(width: 10, height: 10, decoration: BoxDecoration(color: color, borderRadius: BorderRadius.circular(3))),
        const SizedBox(width: 6),
        Text(label, style: context.text.labelSmall),
      ],
    );
  }
}
