import 'package:intl/intl.dart';

import '../constants/currencies.dart';

/// Formats amounts consistently across the app and reports.
class Money {
  Money._();

  static final Map<String, NumberFormat> _cache = {};

  static NumberFormat _format(String currency, {bool compact = false}) {
    final info = currencyInfo(currency);
    final key = '$currency-$compact';
    return _cache.putIfAbsent(key, () {
      if (compact) {
        return NumberFormat.compactCurrency(
          locale: currency == 'INR' ? 'en_IN' : 'en_US',
          symbol: info.symbol,
          decimalDigits: 1,
        );
      }
      return NumberFormat.currency(
        locale: currency == 'INR' ? 'en_IN' : 'en_US',
        symbol: info.symbol,
        decimalDigits: info.decimals,
      );
    });
  }

  /// "₹1,23,456.00" / "$1,234.50".
  static String format(double amount, String currency, {bool compact = false}) {
    final f = _format(currency, compact: compact);
    return f.format(amount);
  }

  /// Formats with an explicit sign: "+₹500" or "-₹500".
  static String signed(double amount, String currency, {bool compact = false}) {
    final abs = format(amount.abs(), currency, compact: compact);
    if (amount > 0) return '+$abs';
    if (amount < 0) return '-$abs';
    return abs;
  }

  /// Plain number without symbol: "1,234.50".
  static String plain(double amount, String currency) {
    final info = currencyInfo(currency);
    final f = NumberFormat.currency(
      locale: currency == 'INR' ? 'en_IN' : 'en_US',
      symbol: '',
      decimalDigits: info.decimals,
    );
    return f.format(amount).trim();
  }

  static String symbol(String currency) => currencyInfo(currency).symbol;

  /// Parses user input like "1,250.50" or "₹ 1250".
  static double? parse(String input) {
    final cleaned = input.replaceAll(RegExp(r'[^0-9.\-]'), '');
    if (cleaned.isEmpty || cleaned == '-' || cleaned == '.') return null;
    return double.tryParse(cleaned);
  }

  static String percent(double fraction, {int decimals = 0}) {
    return '${(fraction * 100).toStringAsFixed(decimals)}%';
  }
}
