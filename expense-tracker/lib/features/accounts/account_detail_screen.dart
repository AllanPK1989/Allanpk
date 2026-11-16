import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:material_ui/material_ui.dart';

import '../../core/utils/date_utils.dart';
import '../../core/utils/extensions.dart';
import '../../core/utils/money.dart';
import '../../core/widgets/widgets.dart';
import '../../models/models.dart';
import '../analytics/analytics_engine.dart';
import '../analytics/widgets/charts.dart';
import '../household/household_providers.dart';
import '../transactions/widgets/transaction_tile.dart';

class AccountDetailScreen extends ConsumerWidget {
  const AccountDetailScreen({super.key, required this.id});
  final String id;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final balance = ref.watch(balancesProvider).where((b) => b.account.id == id).firstOrNull;
    final currency = ref.watch(baseCurrencyProvider);
    final all = ref.watch(allTransactionsProvider).value ?? const [];
    if (balance == null) {
      return Scaffold(appBar: AppBar(), body: const EmptyState(icon: Icons.search_off_rounded, title: 'Account not found'));
    }
    final a = balance.account;
    final txs = all.where((t) => t.accountId == id || t.toAccountId == id).toList();
    final range = DateRange.lastDays(30);
    final recent = AnalyticsEngine.inRange(txs, range);
    final inflow = recent.where((t) => t.isIncome || (t.isTransfer && t.toAccountId == id)).fold<double>(0, (s, t) => s + t.amount);
    final outflow = recent.where((t) => t.isExpense || (t.isTransfer && t.accountId == id)).fold<double>(0, (s, t) => s + t.amount);

    // Balance history over the last 30 days.
    final points = <DailyPoint>[];
    var cursor = AppDates.dateOnly(range.start);
    while (!cursor.isAfter(range.end)) {
      final asOf = DateTime(cursor.year, cursor.month, cursor.day, 23, 59, 59);
      final b = AnalyticsEngine.balances([a], txs, asOf: asOf).first.balance;
      points.add(DailyPoint(cursor, b, 0));
      cursor = cursor.add(const Duration(days: 1));
    }

    return Scaffold(
      appBar: AppBar(
        title: Text(a.name),
        actions: [
          IconButton(icon: const Icon(Icons.edit_rounded), onPressed: () => context.push('/accounts/$id/edit')),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(16, 4, 16, 40),
        children: [
          AppCard(
            padding: const EdgeInsets.all(20),
            child: Row(
              children: [
                IconBadge(iconKey: a.resolvedIconKey, color: a.color, size: 60),
                const SizedBox(width: 16),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(a.type.label, style: context.text.labelMedium?.copyWith(color: context.colors.onSurfaceVariant)),
                      Text(Money.format(balance.balance, currency), style: context.text.headlineSmall),
                      Text(
                        'Opening ${Money.format(a.initialBalance, currency, compact: true)} · ${balance.transactionCount} transactions',
                        style: context.text.bodySmall?.copyWith(color: context.colors.onSurfaceVariant),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 12),
          Row(
            children: [
              Expanded(
                child: AppCard(
                  padding: const EdgeInsets.all(14),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('In · 30 days', style: context.text.labelSmall?.copyWith(color: context.colors.onSurfaceVariant)),
                      AmountText(inflow, currency: currency, type: TransactionType.income, style: context.text.titleMedium),
                    ],
                  ),
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: AppCard(
                  padding: const EdgeInsets.all(14),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('Out · 30 days', style: context.text.labelSmall?.copyWith(color: context.colors.onSurfaceVariant)),
                      AmountText(outflow, currency: currency, type: TransactionType.expense, style: context.text.titleMedium),
                    ],
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 14),
          const SectionHeader(title: 'Balance · last 30 days'),
          AppCard(
            padding: const EdgeInsets.fromLTRB(8, 16, 16, 8),
            child: DailySpendChart(points: points, currency: currency),
          ),
          const SizedBox(height: 14),
          const SectionHeader(title: 'Transactions'),
          if (txs.isEmpty)
            const AppCard(child: EmptyState(icon: Icons.receipt_long_rounded, title: 'No transactions yet', compact: true))
          else
            AppCard(
              padding: const EdgeInsets.symmetric(vertical: 4),
              child: Column(children: [for (final t in txs.take(50)) TransactionTile(transaction: t, showDate: true)]),
            ),
        ],
      ),
    );
  }
}
