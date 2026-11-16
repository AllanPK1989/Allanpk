import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:material_ui/material_ui.dart';

import '../../core/theme/app_theme.dart';
import '../../core/utils/date_utils.dart';
import '../../core/utils/extensions.dart';
import '../../core/widgets/widgets.dart';
import '../../models/models.dart';
import '../household/household_providers.dart';

class RecurringScreen extends ConsumerWidget {
  const RecurringScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final rulesAsync = ref.watch(recurringProvider);
    final categories = ref.watch(categoryMapProvider);
    final accounts = ref.watch(accountMapProvider);
    final currency = ref.watch(baseCurrencyProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Recurring'),
        actions: [
          IconButton(icon: const Icon(Icons.add_rounded), onPressed: () => context.push('/recurring/new')),
          const SizedBox(width: 4),
        ],
      ),
      body: rulesAsync.when(
        loading: () => const LoadingState(),
        error: (e, _) => ErrorState(error: e),
        data: (rules) {
          if (rules.isEmpty) {
            return EmptyState(
              icon: Icons.repeat_rounded,
              title: 'No recurring transactions',
              message: 'Rent, salary, EMIs and subscriptions can post themselves on schedule.',
              actionLabel: 'Add recurring',
              onAction: () => context.push('/recurring/new'),
            );
          }
          final active = rules.where((r) => r.isActive).toList();
          final paused = rules.where((r) => !r.isActive).toList();
          final monthlyOut = active.where((r) => r.type == TransactionType.expense).fold<double>(0, (s, r) => s + _monthly(r));
          final monthlyIn = active.where((r) => r.type == TransactionType.income).fold<double>(0, (s, r) => s + _monthly(r));

          return ListView(
            padding: const EdgeInsets.fromLTRB(16, 4, 16, 40),
            children: [
              AppCard(
                child: Row(
                  children: [
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text('Monthly commitments', style: context.text.labelMedium?.copyWith(color: context.colors.onSurfaceVariant)),
                          AmountText(monthlyOut, currency: currency, type: TransactionType.expense, style: context.text.titleLarge),
                        ],
                      ),
                    ),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text('Monthly income', style: context.text.labelMedium?.copyWith(color: context.colors.onSurfaceVariant)),
                          AmountText(monthlyIn, currency: currency, type: TransactionType.income, style: context.text.titleLarge),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
              if (active.isNotEmpty) const SectionHeader(title: 'Upcoming'),
              for (final r in active) _RuleTile(rule: r, categories: categories, accounts: accounts, currency: currency),
              if (paused.isNotEmpty) const SectionHeader(title: 'Paused / finished'),
              for (final r in paused) _RuleTile(rule: r, categories: categories, accounts: accounts, currency: currency),
            ],
          );
        },
      ),
    );
  }

  static double _monthly(RecurringRule r) {
    final perPeriod = r.amount / r.interval;
    return switch (r.frequency) {
      RecurrenceFrequency.daily => perPeriod * 30,
      RecurrenceFrequency.weekly => perPeriod * 52 / 12,
      RecurrenceFrequency.monthly => perPeriod,
      RecurrenceFrequency.yearly => perPeriod / 12,
    };
  }
}

class _RuleTile extends ConsumerWidget {
  const _RuleTile({required this.rule, required this.categories, required this.accounts, required this.currency});
  final RecurringRule rule;
  final Map<String, Category> categories;
  final Map<String, Account> accounts;
  final String currency;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final r = rule;
    final cat = categories[r.categoryId];
    final due = r.nextDue;
    final overdue = r.isActive && due.isBefore(DateTime.now());
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: AppCard(
        padding: const EdgeInsets.symmetric(vertical: 4),
        child: ListTile(
          onTap: () => context.push('/recurring/${r.id}/edit'),
          leading: IconBadge(
            iconKey: r.type == TransactionType.transfer ? 'currency_exchange' : (cat?.iconKey ?? 'repeat'),
            color: r.type == TransactionType.transfer ? AppTheme.transfer.argb : (cat?.color ?? 0xFF78909C),
            size: 42,
          ),
          title: Text(r.payee.isNotEmpty ? r.payee : (cat?.name ?? r.type.label), style: context.text.titleSmall),
          subtitle: Text(
            '${r.frequencyLabel} · ${accounts[r.accountId]?.name ?? 'Account'}'
            '${r.isActive ? ' · next ${AppDates.relativeDay(due)}' : ' · paused'}'
            '${r.autoAdd ? '' : ' · reminder only'}',
            style: context.text.bodySmall?.copyWith(color: overdue ? AppTheme.warning : context.colors.onSurfaceVariant),
          ),
          trailing: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              AmountText(r.amount, currency: currency, type: r.type, signed: true, style: context.text.titleSmall),
              Switch(
                value: r.isActive,
                onChanged: (v) => ref.read(ledgerProvider)?.saveRecurring(
                      r.copyWith(isActive: v, nextDue: v && r.nextDue.isBefore(DateTime.now()) ? DateTime.now() : null),
                    ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
