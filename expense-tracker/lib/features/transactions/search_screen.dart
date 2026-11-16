import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:material_ui/material_ui.dart';

import '../../core/utils/expression.dart';
import '../../core/utils/extensions.dart';
import '../../core/utils/money.dart';
import '../../core/widgets/widgets.dart';
import '../../models/models.dart';
import '../household/household_providers.dart';
import 'widgets/transaction_tile.dart';

/// Free-text search across payee, note, tags, category, account and amount.
class SearchScreen extends ConsumerStatefulWidget {
  const SearchScreen({super.key});

  @override
  ConsumerState<SearchScreen> createState() => _SearchScreenState();
}

class _SearchScreenState extends ConsumerState<SearchScreen> {
  final _controller = TextEditingController();
  String _query = '';

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final all = ref.watch(allTransactionsProvider).value ?? const [];
    final categories = ref.watch(categoryMapProvider);
    final accounts = ref.watch(accountMapProvider);
    final currency = ref.watch(baseCurrencyProvider);
    final q = _query.trim().toLowerCase();
    final amountQuery = evaluateExpression(q);

    final results = q.isEmpty
        ? const <Transaction>[]
        : all.where((t) {
            if (amountQuery != null && (t.amount - amountQuery).abs() < 0.005) return true;
            if (t.payee.toLowerCase().contains(q)) return true;
            if (t.note.toLowerCase().contains(q)) return true;
            if (t.tags.any((tag) => tag.contains(q.replaceAll('#', '')))) return true;
            final cat = categories[t.categoryId];
            if (cat != null && cat.name.toLowerCase().contains(q)) return true;
            final acc = accounts[t.accountId];
            if (acc != null && acc.name.toLowerCase().contains(q)) return true;
            return false;
          }).toList();
    final total = results.where((t) => t.isExpense).fold<double>(0, (s, t) => s + t.amount);

    return Scaffold(
      appBar: AppBar(
        titleSpacing: 0,
        title: TextField(
          controller: _controller,
          autofocus: true,
          decoration: InputDecoration(
            hintText: 'Search payee, note, #tag, amount…',
            filled: false,
            border: InputBorder.none,
            enabledBorder: InputBorder.none,
            focusedBorder: InputBorder.none,
            suffixIcon: _query.isEmpty
                ? null
                : IconButton(
                    icon: const Icon(Icons.close_rounded),
                    onPressed: () => setState(() {
                      _controller.clear();
                      _query = '';
                    }),
                  ),
          ),
          onChanged: (v) => setState(() => _query = v),
        ),
      ),
      body: q.isEmpty
          ? const EmptyState(
              icon: Icons.search_rounded,
              title: 'Search everything',
              message: 'Type a merchant, note, tag, category, account name or an exact amount.',
            )
          : results.isEmpty
              ? const EmptyState(icon: Icons.search_off_rounded, title: 'No results')
              : GroupedTransactionList(
                  transactions: results,
                  leadingSlivers: [
                    SliverToBoxAdapter(
                      child: Padding(
                        padding: const EdgeInsets.fromLTRB(20, 8, 20, 0),
                        child: Text(
                          '${results.length} ${results.length == 1 ? 'result' : 'results'}'
                          '${total > 0 ? ' · ${Money.format(total, currency)} spent' : ''}',
                          style: context.text.bodySmall?.copyWith(color: context.colors.onSurfaceVariant),
                        ),
                      ),
                    ),
                  ],
                ),
    );
  }
}
