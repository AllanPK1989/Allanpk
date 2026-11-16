import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:material_ui/material_ui.dart';

import '../../core/utils/extensions.dart';
import '../../core/utils/money.dart';
import '../../core/widgets/widgets.dart';
import '../../models/models.dart';
import '../analytics/analytics_engine.dart';
import '../household/household_providers.dart';

class AccountsScreen extends ConsumerWidget {
  const AccountsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final balances = ref.watch(balancesProvider);
    final currency = ref.watch(baseCurrencyProvider);
    final netWorth = ref.watch(netWorthProvider);
    final active = balances.where((b) => !b.account.isArchived).toList();
    final archived = balances.where((b) => b.account.isArchived).toList();
    final assets = active.where((b) => b.balance >= 0 && !b.account.excludeFromTotals).fold<double>(0, (s, b) => s + b.balance);
    final liabilities = active.where((b) => b.balance < 0 && !b.account.excludeFromTotals).fold<double>(0, (s, b) => s + b.balance);

    final byType = <AccountType, List<AccountBalance>>{};
    for (final b in active) {
      byType.putIfAbsent(b.account.type, () => []).add(b);
    }

    return Scaffold(
      appBar: AppBar(
        title: const Text('Accounts'),
        actions: [
          IconButton(icon: const Icon(Icons.add_rounded), onPressed: () => context.push('/accounts/new')),
          const SizedBox(width: 4),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(16, 4, 16, 40),
        children: [
          AppCard(
            padding: const EdgeInsets.all(18),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('Net worth', style: context.text.labelMedium?.copyWith(color: context.colors.onSurfaceVariant)),
                Text(Money.format(netWorth, currency), style: context.text.headlineMedium),
                const SizedBox(height: 10),
                Row(
                  children: [
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text('Assets', style: context.text.labelSmall?.copyWith(color: context.colors.onSurfaceVariant)),
                          AmountText(assets, currency: currency, style: context.text.titleSmall, type: TransactionType.income),
                        ],
                      ),
                    ),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text('Liabilities', style: context.text.labelSmall?.copyWith(color: context.colors.onSurfaceVariant)),
                          AmountText(liabilities.abs(), currency: currency, style: context.text.titleSmall, type: TransactionType.expense),
                        ],
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
          if (active.isEmpty)
            EmptyState(
              icon: Icons.account_balance_wallet_outlined,
              title: 'No accounts',
              message: 'Add your cash, bank, card and wallet accounts to track balances.',
              actionLabel: 'Add account',
              onAction: () => context.push('/accounts/new'),
            ),
          for (final type in AccountType.values)
            if (byType[type] != null) ...[
              SectionHeader(title: type.label),
              AppCard(
                padding: const EdgeInsets.symmetric(vertical: 4),
                child: Column(children: [for (final b in byType[type]!) _AccountTile(balance: b, currency: currency)]),
              ),
              const SizedBox(height: 6),
            ],
          if (archived.isNotEmpty) ...[
            const SectionHeader(title: 'Archived'),
            AppCard(
              padding: const EdgeInsets.symmetric(vertical: 4),
              child: Column(children: [for (final b in archived) _AccountTile(balance: b, currency: currency)]),
            ),
          ],
        ],
      ),
    );
  }
}

class _AccountTile extends StatelessWidget {
  const _AccountTile({required this.balance, required this.currency});
  final AccountBalance balance;
  final String currency;

  @override
  Widget build(BuildContext context) {
    final a = balance.account;
    return ListTile(
      onTap: () => context.push('/accounts/${a.id}'),
      leading: IconBadge(iconKey: a.resolvedIconKey, color: a.color, size: 42),
      title: Text(a.name, style: context.text.titleSmall),
      subtitle: Text(
        [
          if (a.isArchived) 'Archived',
          if (!a.isShared) 'Private',
          if (a.excludeFromTotals) 'Excluded from totals',
          '${balance.transactionCount} transactions',
        ].join(' · '),
        style: context.text.bodySmall?.copyWith(color: context.colors.onSurfaceVariant),
      ),
      trailing: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        crossAxisAlignment: CrossAxisAlignment.end,
        children: [
          AmountText(balance.balance, currency: currency, style: context.text.titleSmall, colored: balance.balance < 0),
          if (a.creditLimit != null)
            Text(
              '${Money.format((a.creditLimit! + balance.balance).clamp(0, a.creditLimit!), currency, compact: true)} available',
              style: context.text.labelSmall?.copyWith(color: context.colors.onSurfaceVariant),
            ),
        ],
      ),
    );
  }
}
