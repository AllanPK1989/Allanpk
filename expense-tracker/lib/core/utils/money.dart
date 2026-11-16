import 'package:intl/intl.dart';

import '../constants/currencies.dart';

/// Formats amounts consistently across the app and reports.
class Money {
  Money._();

  static final Map<String, NumberFormat> _cache = {};

  static NumberFormat _format(String currency) {
    final info = currencyInfo(currency);
    return _cache.putIfAbsent(currency, () {
      return NumberFormat.currency(
        locale: currency == 'INR' ? 'en_IN' : 'en_US',
        symbol: info.symbol,
        decimalDigits: info.decimals,
      );
    });
  }

  /// "₹1,23,456.00" / "$1,234.50"; compact: "₹1.2L", "₹15K", "$2.3M".
  static String format(double amount, String currency, {bool compact = false}) {
    if (compact) return _compact(amount, currency);
    return _format(currency).format(amount);
  }

  /// Short labels for charts and chips. INR uses lakh/crore, others K/M/B.
  static String _compact(double amount, String currency) {
    final symbol = currencyInfo(currency).symbol;
    final abs = amount.abs();
    final sign = amount < 0 ? '-' : '';
    String trim(double v) {
      final s = v.toStringAsFixed(v >= 100 ? 0 : 1);
      return s.endsWith('.0') ? s.substring(0, s.length - 2) : s;
    }

    if (currency == 'INR') {
      if (abs >= 1e7) return '$sign$symbol${trim(abs / 1e7)}Cr';
      if (abs >= 1e5) return '$sign$symbol${trim(abs / 1e5)}L';
    } else {
      if (abs >= 1e9) return '$sign$symbol${trim(abs / 1e9)}B';
      if (abs >= 1e6) return '$sign$symbol${trim(abs / 1e6)}M';
    }
    if (abs >= 1e3) return '$sign$symbol${trim(abs / 1e3)}K';
    if (abs == abs.roundToDouble()) return '$sign$symbol${abs.toInt()}';
    return '$sign$symbol${abs.toStringAsFixed(currencyInfo(currency).decimals)}';
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
