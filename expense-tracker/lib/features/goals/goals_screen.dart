import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:material_ui/material_ui.dart';

import '../../core/constants/app_icons.dart';
import '../../core/utils/date_utils.dart';
import '../../core/utils/extensions.dart';
import '../../core/utils/money.dart';
import '../../core/widgets/widgets.dart';
import '../../models/models.dart';
import '../analytics/widgets/charts.dart';
import '../household/household_providers.dart';
import '../transactions/widgets/pickers.dart';

class GoalsScreen extends ConsumerWidget {
  const GoalsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final goalsAsync = ref.watch(goalsProvider);
    final currency = ref.watch(baseCurrencyProvider);
    return Scaffold(
      appBar: AppBar(
        title: const Text('Savings goals'),
        actions: [
          IconButton(icon: const Icon(Icons.add_rounded), onPressed: () => context.push('/goals/new')),
          const SizedBox(width: 4),
        ],
      ),
      body: goalsAsync.when(
        loading: () => const LoadingState(),
        error: (e, _) => ErrorState(error: e),
        data: (goals) {
          if (goals.isEmpty) {
            return EmptyState(
              icon: Icons.savings_outlined,
              title: 'Save for something',
              message: 'A holiday, an emergency fund, a new laptop. Set a target and watch it grow.',
              actionLabel: 'Create a goal',
              onAction: () => context.push('/goals/new'),
            );
          }
          final active = goals.where((g) => !g.isCompleted).toList()..sort((a, b) => b.progress.compareTo(a.progress));
          final done = goals.where((g) => g.isCompleted).toList();
          final totalSaved = goals.fold<double>(0, (s, g) => s + g.savedAmount);
          return ListView(
            padding: const EdgeInsets.fromLTRB(16, 4, 16, 40),
            children: [
              AppCard(
                child: Row(
                  children: [
                    IconBadge(iconKey: 'savings', color: kPalette[6], size: 44),
                    const SizedBox(width: 12),
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text('Total saved towards goals', style: context.text.labelMedium?.copyWith(color: context.colors.onSurfaceVariant)),
                        Text(Money.format(totalSaved, currency), style: context.text.titleLarge),
                      ],
                    ),
                  ],
                ),
              ),
              if (active.isNotEmpty) const SectionHeader(title: 'In progress'),
              for (final g in active) _GoalCard(goal: g, currency: currency),
              if (done.isNotEmpty) const SectionHeader(title: 'Completed'),
              for (final g in done) _GoalCard(goal: g, currency: currency),
            ],
          );
        },
      ),
    );
  }
}

class _GoalCard extends ConsumerWidget {
  const _GoalCard({required this.goal, required this.currency});
  final Goal goal;
  final String currency;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final g = goal;
    final monthly = g.monthlyNeeded(DateTime.now());
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: AppCard(
        onTap: () => context.push('/goals/${g.id}/edit'),
        child: Column(
          children: [
            Row(
              children: [
                ProgressRing(
                  fraction: g.progress,
                  color: Color(g.color),
                  size: 60,
                  child: Icon(iconFor(g.iconKey), color: Color(g.color), size: 22),
                ),
                const SizedBox(width: 14),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(g.name, style: context.text.titleSmall),
                      Text(
                        '${Money.format(g.savedAmount, currency, compact: true)} of ${Money.format(g.targetAmount, currency, compact: true)} · ${Money.percent(g.progress)}',
                        style: context.text.bodySmall?.copyWith(color: context.colors.onSurfaceVariant),
                      ),
                      if (g.deadline != null)
                        Text(
                          'By ${AppDates.dayMonthYear.format(g.deadline!)}'
                          '${monthly != null && !g.isCompleted ? ' · ${Money.format(monthly, currency, compact: true)}/month needed' : ''}',
                          style: context.text.labelSmall?.copyWith(color: context.colors.onSurfaceVariant),
                        ),
                    ],
                  ),
                ),
                if (!g.isCompleted)
                  FilledButton.tonal(
                    style: FilledButton.styleFrom(minimumSize: const Size(0, 40), padding: const EdgeInsets.symmetric(horizontal: 14)),
                    onPressed: () => _contribute(context, ref),
                    child: const Text('Add'),
                  )
                else
                  const Icon(Icons.emoji_events_rounded, color: Color(0xFFF59E0B)),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _contribute(BuildContext context, WidgetRef ref) async {
    final controller = TextEditingController();
    final accounts = (ref.read(accountsProvider).value ?? const []).where((a) => !a.isArchived).toList();
    String? accountId;
    final amount = await showDialog<double>(
      context: context,
      builder: (dialog) => StatefulBuilder(
        builder: (context, setState) => AlertDialog(
          title: Text('Add to ${goal.name}'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextField(
                controller: controller,
                autofocus: true,
                keyboardType: const TextInputType.numberWithOptions(decimal: true),
                decoration: InputDecoration(labelText: 'Amount', prefixText: '${Money.symbol(currency)} '),
              ),
              const SizedBox(height: 12),
              OutlinedButton.icon(
                onPressed: () async {
                  final picked = await showAccountPicker(context, accounts: accounts, selected: accountId);
                  if (picked != null) setState(() => accountId = picked);
                },
                icon: const Icon(Icons.account_balance_wallet_outlined, size: 18),
                label: Text(accountId == null ? 'Record as transfer from… (optional)' : accounts.firstWhere((a) => a.id == accountId).name),
              ),
            ],
          ),
          actions: [
            TextButton(onPressed: () => Navigator.pop(dialog), child: const Text('Cancel')),
            FilledButton(
              style: FilledButton.styleFrom(minimumSize: const Size(0, 44)),
              onPressed: () => Navigator.pop(dialog, Money.parse(controller.text)),
              child: const Text('Add'),
            ),
          ],
        ),
      ),
    );
    if (amount == null || amount <= 0) return;
    final profile = ref.read(userProfileProvider).value;
    final ledger = ref.read(ledgerProvider);
    if (profile == null || ledger == null) return;
    await ledger.contributeToGoal(goal: goal, amount: amount, actor: profile, currency: currency, accountId: accountId);
    if (context.mounted) context.showSnack('Added ${Money.format(amount, currency)} to ${goal.name}');
  }
}
