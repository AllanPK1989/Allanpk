import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:material_ui/material_ui.dart';

import '../../../core/theme/app_theme.dart';
import '../../../core/utils/date_utils.dart';
import '../../../core/utils/extensions.dart';
import '../../../core/widgets/widgets.dart';
import '../../../models/models.dart';
import '../../household/household_providers.dart';

/// Single transaction row used across lists, details and dashboards.
class TransactionTile extends ConsumerWidget {
  const TransactionTile({
    super.key,
    required this.transaction,
    this.showDate = false,
    this.showMember = true,
    this.onTap,
    this.dense = false,
  });

  final Transaction transaction;
  final bool showDate;
  final bool showMember;
  final VoidCallback? onTap;
  final bool dense;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final tx = transaction;
    final categories = ref.watch(categoryMapProvider);
    final accounts = ref.watch(accountMapProvider);
    final household = ref.watch(activeHouseholdProvider).value;
    final currency = ref.watch(baseCurrencyProvider);
    final cat = tx.categoryId == null ? null : categories[tx.categoryId];
    final account = accounts[tx.accountId];
    final toAccount = tx.toAccountId == null ? null : accounts[tx.toAccountId];
    final member = household?.members[tx.createdBy];

    final String title;
    final String iconKey;
    final int color;
    if (tx.isTransfer) {
      title = tx.payee.isNotEmpty
          ? tx.payee
          : '${account?.name ?? 'Account'} → ${toAccount?.name ?? 'Account'}';
      iconKey = 'currency_exchange';
      color = AppTheme.transfer.argb;
    } else {
      title = tx.payee.isNotEmpty ? tx.payee : (cat?.name ?? 'Uncategorised');
      iconKey = cat?.iconKey ?? 'category';
      color = cat?.color ?? 0xFF78909C;
    }

    final subtitleParts = <String>[
      if (!tx.isTransfer && tx.payee.isNotEmpty && cat != null) cat.name,
      if (showDate) AppDates.relativeDay(tx.date),
      if (account != null && !tx.isTransfer) account.name,
      if (showMember && household != null && household.isShared && member != null) member.name,
      if (tx.note.isNotEmpty) tx.note,
    ];

    return ListTile(
      dense: dense,
      onTap: onTap ?? () => context.push('/transactions/${tx.id}'),
      contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 2),
      leading: Stack(
        clipBehavior: Clip.none,
        children: [
          IconBadge(iconKey: iconKey, color: color, size: dense ? 38 : 44),
          if (tx.isPrivate)
            Positioned(
              right: -4,
              bottom: -4,
              child: Container(
                padding: const EdgeInsets.all(2),
                decoration: BoxDecoration(color: context.colors.surface, shape: BoxShape.circle),
                child: Icon(Icons.lock_rounded, size: 12, color: context.colors.onSurfaceVariant),
              ),
            ),
          if (tx.receiptUrls.isNotEmpty)
            Positioned(
              right: -4,
              top: -4,
              child: Container(
                padding: const EdgeInsets.all(2),
                decoration: BoxDecoration(color: context.colors.surface, shape: BoxShape.circle),
                child: Icon(Icons.attach_file_rounded, size: 12, color: context.colors.onSurfaceVariant),
              ),
            ),
        ],
      ),
      title: Text(title, maxLines: 1, overflow: TextOverflow.ellipsis, style: context.text.titleSmall),
      subtitle: subtitleParts.isEmpty
          ? null
          : Text(
              subtitleParts.join(' · '),
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: context.text.bodySmall?.copyWith(color: context.colors.onSurfaceVariant),
            ),
      trailing: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        crossAxisAlignment: CrossAxisAlignment.end,
        children: [
          AmountText(tx.amount, currency: currency, type: tx.type, signed: true, style: context.text.titleSmall),
          if (tx.currency != currency)
            Text(
              '${tx.currency} ${tx.originalAmount.toStringAsFixed(2)}',
              style: context.text.labelSmall?.copyWith(color: context.colors.onSurfaceVariant),
            )
          else if (!showDate)
            Text(
              AppDates.time.format(tx.date),
              style: context.text.labelSmall?.copyWith(color: context.colors.onSurfaceVariant),
            ),
        ],
      ),
    );
  }
}

/// Groups transactions by day with a running daily total header.
class GroupedTransactionList extends ConsumerWidget {
  const GroupedTransactionList({
    super.key,
    required this.transactions,
    this.padding = const EdgeInsets.only(bottom: 96),
    this.leadingSlivers = const [],
    this.itemBuilder,
  });

  final List<Transaction> transactions;
  final EdgeInsetsGeometry padding;
  final List<Widget> leadingSlivers;

  /// Optional wrapper (e.g. Slidable) around each tile.
  final Widget Function(BuildContext, Transaction, Widget tile)? itemBuilder;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final currency = ref.watch(baseCurrencyProvider);
    final groups = <DateTime, List<Transaction>>{};
    for (final t in transactions) {
      final day = AppDates.dateOnly(t.date);
      groups.putIfAbsent(day, () => []).add(t);
    }
    final days = groups.keys.toList()..sort((a, b) => b.compareTo(a));

    return CustomScrollView(
      slivers: [
        ...leadingSlivers,
        for (final day in days) ...[
          SliverToBoxAdapter(
            child: Padding(
              padding: const EdgeInsets.fromLTRB(20, 18, 20, 6),
              child: Row(
                children: [
                  Expanded(
                    child: Text(
                      AppDates.relativeDay(day),
                      style: context.text.labelLarge?.copyWith(color: context.colors.onSurfaceVariant),
                    ),
                  ),
                  Builder(
                    builder: (context) {
                      final dayTotal = groups[day]!.fold<double>(0, (s, t) => s + t.signedAmount);
                      return AmountText(
                        dayTotal,
                        currency: currency,
                        signed: true,
                        style: context.text.labelLarge,
                      );
                    },
                  ),
                ],
              ),
            ),
          ),
          SliverToBoxAdapter(
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 12),
              child: AppCard(
                padding: const EdgeInsets.symmetric(vertical: 4),
                child: Column(
                  children: [
                    for (final t in groups[day]!)
                      itemBuilder == null
                          ? TransactionTile(transaction: t)
                          : itemBuilder!(context, t, TransactionTile(transaction: t)),
                  ],
                ),
              ),
            ),
          ),
        ],
        SliverPadding(padding: padding),
      ],
    );
  }
}
