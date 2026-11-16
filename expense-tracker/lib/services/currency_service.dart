import 'dart:convert';

import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

/// Exchange rates relative to a base currency, cached for 24 hours.
/// Uses the free Frankfurter API (ECB reference rates, no key required).
class CurrencyService {
  CurrencyService(this._prefs, {http.Client? client}) : _client = client ?? http.Client();

  final SharedPreferences _prefs;
  final http.Client _client;

  static const _cacheKeyPrefix = 'rates_';
  static const _maxAge = Duration(hours: 24);

  Future<RateTable> rates(String base, {bool forceRefresh = false}) async {
    final cached = _readCache(base);
    if (!forceRefresh && cached != null && !cached.isStale) return cached;
    try {
      final uri = Uri.parse('https://api.frankfurter.app/latest?from=$base');
      final res = await _client.get(uri).timeout(const Duration(seconds: 8));
      if (res.statusCode == 200) {
        final json = jsonDecode(res.body) as Map<String, dynamic>;
        final raw = (json['rates'] as Map<String, dynamic>).map(
          (k, v) => MapEntry(k, (v as num).toDouble()),
        );
        raw[base] = 1;
        final table = RateTable(base: base, rates: raw, fetchedAt: DateTime.now());
        await _prefs.setString('$_cacheKeyPrefix$base', jsonEncode(table.toJson()));
        return table;
      }
    } catch (_) {
      // Fall through to the cache / identity table.
    }
    return cached ?? RateTable(base: base, rates: {base: 1}, fetchedAt: null);
  }

  RateTable? _readCache(String base) {
    final raw = _prefs.getString('$_cacheKeyPrefix$base');
    if (raw == null) return null;
    try {
      return RateTable.fromJson(jsonDecode(raw) as Map<String, dynamic>);
    } catch (_) {
      return null;
    }
  }
}

class RateTable {
  const RateTable({required this.base, required this.rates, required this.fetchedAt});

  final String base;

  /// 1 unit of [base] = rates[code] units of code.
  final Map<String, double> rates;
  final DateTime? fetchedAt;

  bool get isStale =>
      fetchedAt == null || DateTime.now().difference(fetchedAt!) > CurrencyService._maxAge;

  bool get isOffline => fetchedAt == null;

  /// Rate to convert [from] into [base]. Returns null when unknown.
  double? rateToBase(String from) {
    if (from == base) return 1;
    final r = rates[from];
    if (r == null || r == 0) return null;
    return 1 / r;
  }

  double convertToBase(double amount, String from) {
    final r = rateToBase(from);
    return r == null ? amount : amount * r;
  }

  Map<String, dynamic> toJson() => {
        'base': base,
        'rates': rates,
        'fetchedAt': fetchedAt?.toIso8601String(),
      };

  factory RateTable.fromJson(Map<String, dynamic> json) => RateTable(
        base: json['base'] as String,
        rates: (json['rates'] as Map<String, dynamic>).map(
          (k, v) => MapEntry(k, (v as num).toDouble()),
        ),
        fetchedAt: json['fetchedAt'] == null ? null : DateTime.parse(json['fetchedAt'] as String),
      );
}
