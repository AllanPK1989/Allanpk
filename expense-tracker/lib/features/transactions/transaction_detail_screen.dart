import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:material_ui/material_ui.dart';

import '../../core/theme/app_theme.dart';
import '../../core/utils/date_utils.dart';
import '../../core/utils/extensions.dart';
import '../../core/utils/money.dart';
import '../../core/widgets/widgets.dart';
import '../../models/models.dart';
import '../../router.dart';
import '../auth/auth_providers.dart';
import '../household/household_providers.dart';

class TransactionDetailScreen extends ConsumerWidget {
  const TransactionDetailScreen({super.key, required this.id});
  final String id;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final all = ref.watch(allTransactionsProvider).value ?? const [];
    final tx = all.where((t) => t.id == id).firstOrNull;
    if (tx == null) {
      return Scaffold(
        appBar: AppBar(),
        body: const EmptyState(icon: Icons.search_off_rounded, title: 'Transaction not found'),
      );
    }
    final categories = ref.watch(categoryMapProvider);
    final accounts = ref.watch(accountMapProvider);
    final household = ref.watch(activeHouseholdProvider).value;
    final currency = ref.watch(baseCurrencyProvider);
    final role = ref.watch(myRoleProvider);
    final uid = ref.watch(currentUidProvider);
    final cat = categories[tx.categoryId];
    final parent = cat?.parentId == null ? null : categories[cat!.parentId];
    final account = accounts[tx.accountId];
    final toAccount = tx.toAccountId == null ? null : accounts[tx.toAccountId];
    final member = household?.members[tx.createdBy];
    final canEdit = tx.createdBy == uid || role.canEditOthersTransactions;
    final color = switch (tx.type) {
      TransactionType.expense => AppTheme.expense,
      TransactionType.income => AppTheme.income,
      TransactionType.transfer => AppTheme.transfer,
    };

    return Scaffold(
      appBar: AppBar(
        title: Text(tx.type.label),
        actions: [
          IconButton(
            tooltip: 'Duplicate',
            icon: const Icon(Icons.copy_rounded),
            onPressed: () => context.push('/transactions/new', extra: tx.id),
          ),
          if (canEdit)
            IconButton(
              tooltip: 'Edit',
              icon: const Icon(Icons.edit_rounded),
              onPressed: () => context.push('/transactions/${tx.id}/edit'),
            ),
          if (canEdit)
            IconButton(
              tooltip: 'Delete',
              icon: const Icon(Icons.delete_outline_rounded),
              onPressed: () async {
                final ok = await confirmDialog(context, title: 'Delete transaction?', message: 'This cannot be undone.');
                if (!ok) return;
                final profile = ref.read(userProfileProvider).value;
                await ref.read(ledgerProvider)?.deleteTransaction(tx, actor: profile, categoryName: cat?.name);
                if (context.mounted) context.popOrHome();
              },
            ),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(16, 8, 16, 32),
        children: [
          AppCard(
            padding: const EdgeInsets.all(20),
            child: Column(
              children: [
                IconBadge(
                  iconKey: tx.isTransfer ? 'currency_exchange' : (cat?.iconKey ?? 'category'),
                  color: tx.isTransfer ? AppTheme.transfer.argb : (cat?.color ?? 0xFF78909C),
                  size: 64,
                ),
                const SizedBox(height: 14),
                Text(
                  Money.format(tx.amount, currency),
                  style: context.text.displaySmall?.copyWith(color: color, fontFeatures: const [FontFeature.tabularFigures()]),
                ),
                if (tx.currency != currency)
                  Text(
                    '${tx.currency} ${Money.plain(tx.originalAmount, tx.currency)} @ ${tx.exchangeRate.toStringAsFixed(4)}',
                    style: context.text.bodySmall?.copyWith(color: context.colors.onSurfaceVariant),
                  ),
                const SizedBox(height: 6),
                Text(
                  tx.payee.isNotEmpty ? tx.payee : (tx.isTransfer ? 'Transfer' : cat?.name ?? 'Uncategorised'),
                  style: context.text.titleMedium,
                  textAlign: TextAlign.center,
                ),
                Text(
                  '${AppDates.weekdayDate.format(tx.date)}, ${AppDates.dayMonthYear.format(tx.date).split(' ').last} · ${AppDates.time.format(tx.date)}',
                  style: context.text.bodySmall?.copyWith(color: context.colors.onSurfaceVariant),
                ),
              ],
            ),
          ),
          const SizedBox(height: 14),
          AppCard(
            padding: const EdgeInsets.symmetric(vertical: 6),
            child: Column(
              children: [
                if (!tx.isTransfer)
                  _Row(
                    'Category',
                    parent == null ? (cat?.name ?? 'Uncategorised') : '${parent.name} › ${cat!.name}',
                    icon: Icons.category_outlined,
                  ),
                _Row(tx.isTransfer ? 'From' : 'Account', account?.name ?? 'Unknown', icon: Icons.account_balance_wallet_outlined),
                if (tx.isTransfer) _Row('To', toAccount?.name ?? 'Unknown', icon: Icons.arrow_forward_rounded),
                if (tx.note.isNotEmpty) _Row('Note', tx.note, icon: Icons.notes_rounded),
                if (tx.tags.isNotEmpty) _Row('Tags', tx.tags.map((t) => '#$t').join('  '), icon: Icons.tag_rounded),
                if (household != null && household.isShared)
                  _Row('Added by', member?.name ?? tx.createdByName, icon: Icons.person_outline_rounded),
                if (tx.isPrivate) const _Row('Visibility', 'Private · only you can see this', icon: Icons.lock_outline_rounded),
                if (tx.recurringId != null) const _Row('Source', 'Recurring rule', icon: Icons.repeat_rounded),
                if (tx.goalId != null) const _Row('Linked to', 'Savings goal', icon: Icons.savings_outlined),
                _Row('Last updated', AppDates.timeAgo(tx.updatedAt), icon: Icons.history_rounded),
              ],
            ),
          ),
          if (tx.receiptUrls.isNotEmpty) ...[
            const SizedBox(height: 14),
            const SectionHeader(title: 'Receipts'),
            GridView.count(
              crossAxisCount: 3,
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              mainAxisSpacing: 8,
              crossAxisSpacing: 8,
              children: [
                for (final url in tx.receiptUrls)
                  GestureDetector(
                    onTap: () => showDialog<void>(
                      context: context,
                      builder: (_) => Dialog(
                        insetPadding: const EdgeInsets.all(12),
                        child: InteractiveViewer(
                          child: Image.network(url, fit: BoxFit.contain, webHtmlElementStrategy: WebHtmlElementStrategy.fallback),
                        ),
                      ),
                    ),
                    child: ClipRRect(
                      borderRadius: BorderRadius.circular(12),
                      child: Image.network(
                        url,
                        fit: BoxFit.cover,
                        // Falls back to an <img> element if the bucket has no CORS policy.
                        webHtmlElementStrategy: WebHtmlElementStrategy.fallback,
                        errorBuilder: (_, _, _) => Container(
                          color: context.colors.surfaceContainerHighest,
                          child: const Icon(Icons.broken_image_outlined),
                        ),
                      ),
                    ),
                  ),
              ],
            ),
          ],
        ],
      ),
    );
  }
}

class _Row extends StatelessWidget {
  const _Row(this.label, this.value, {required this.icon});
  final String label;
  final String value;
  final IconData icon;

  @override
  Widget build(BuildContext context) {
    return ListTile(
      dense: true,
      leading: Icon(icon, size: 20),
      title: Text(label, style: context.text.labelMedium?.copyWith(color: context.colors.onSurfaceVariant)),
      subtitle: Text(value, style: context.text.bodyMedium?.copyWith(color: context.colors.onSurface)),
    );
  }
}
