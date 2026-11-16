/// Helpers for converting loosely typed Firestore maps into strongly typed
/// values. Models stay free of Firestore imports so they can be unit tested
/// without any platform plumbing.
library;

DateTime parseDate(dynamic value, {DateTime? fallback}) {
  if (value == null) return fallback ?? DateTime.now();
  if (value is DateTime) return value;
  if (value is int) return DateTime.fromMillisecondsSinceEpoch(value);
  if (value is String) return DateTime.tryParse(value) ?? fallback ?? DateTime.now();
  try {
    // cloud_firestore Timestamp exposes toDate(); resolved dynamically so the
    // model layer does not depend on the SDK.
    final DateTime converted = (value as dynamic).toDate() as DateTime;
    return converted;
  } catch (_) {
    return fallback ?? DateTime.now();
  }
}

DateTime? parseDateOrNull(dynamic value) {
  if (value == null) return null;
  return parseDate(value);
}

double parseDouble(dynamic value, [double fallback = 0]) {
  if (value == null) return fallback;
  if (value is double) return value;
  if (value is int) return value.toDouble();
  if (value is num) return value.toDouble();
  if (value is String) return double.tryParse(value) ?? fallback;
  return fallback;
}

int parseInt(dynamic value, [int fallback = 0]) {
  if (value == null) return fallback;
  if (value is int) return value;
  if (value is num) return value.toInt();
  if (value is String) return int.tryParse(value) ?? fallback;
  return fallback;
}

bool parseBool(dynamic value, [bool fallback = false]) {
  if (value is bool) return value;
  if (value is String) return value == 'true';
  if (value is num) return value != 0;
  return fallback;
}

String parseString(dynamic value, [String fallback = '']) {
  if (value == null) return fallback;
  if (value is String) return value;
  return value.toString();
}

List<String> parseStringList(dynamic value) {
  if (value is List) {
    return value.map((e) => e.toString()).toList();
  }
  return const [];
}

Map<String, dynamic> parseMap(dynamic value) {
  if (value is Map) {
    return value.map((k, v) => MapEntry(k.toString(), v));
  }
  return const {};
}

/// Rounds a monetary value to two decimals, avoiding floating point drift
/// when summing many transactions.
double roundMoney(double value) => (value * 100).roundToDouble() / 100;
