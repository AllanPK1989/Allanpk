import 'package:material_ui/material_ui.dart';

import '../../models/enums.dart';
import '../theme/app_theme.dart';
import '../utils/money.dart';

/// Renders an amount with colour semantics for income / expense / transfer.
class AmountText extends StatelessWidget {
  const AmountText(
    this.amount, {
    super.key,
    required this.currency,
    this.type,
    this.style,
    this.signed = false,
    this.compact = false,
    this.colored = true,
  });

  final double amount;
  final String currency;
  final TransactionType? type;
  final TextStyle? style;
  final bool signed;
  final bool compact;
  final bool colored;

  static Color colorFor(TransactionType? type, double amount, ColorScheme scheme) {
    switch (type) {
      case TransactionType.income:
        return AppTheme.income;
      case TransactionType.expense:
        return AppTheme.expense;
      case TransactionType.transfer:
        return AppTheme.transfer;
      case null:
        if (amount > 0) return AppTheme.income;
        if (amount < 0) return AppTheme.expense;
        return scheme.onSurface;
    }
  }

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final base = style ?? Theme.of(context).textTheme.titleMedium;
    String label;
    if (signed && type != null) {
      final sign = switch (type!) {
        TransactionType.income => '+',
        TransactionType.expense => '-',
        TransactionType.transfer => '',
      };
      label = '$sign${Money.format(amount.abs(), currency, compact: compact)}';
    } else if (signed) {
      label = Money.signed(amount, currency, compact: compact);
    } else {
      label = Money.format(amount, currency, compact: compact);
    }
    return Text(
      label,
      style: base?.copyWith(
        color: colored ? colorFor(type, amount, scheme) : null,
        fontFeatures: const [FontFeature.tabularFigures()],
      ),
      maxLines: 1,
      overflow: TextOverflow.ellipsis,
    );
  }
}
