import 'enums.dart';
import 'model_utils.dart';

/// A template that generates transactions on a schedule (rent, salary,
/// subscriptions). Due instances are materialised by the app when it starts.
class RecurringRule {
  RecurringRule({
    required this.id,
    required this.type,
    required this.amount,
    required this.currency,
    required this.accountId,
    this.toAccountId,
    this.categoryId,
    this.payee = '',
    this.note = '',
    this.tags = const [],
    required this.frequency,
    this.interval = 1,
    required this.nextDue,
    this.endDate,
    this.autoAdd = true,
    this.isActive = true,
    this.isPrivate = false,
    required this.createdBy,
    required this.createdAt,
    this.lastGeneratedAt,
    int? anchorDay,
  }) : anchorDay = anchorDay ?? nextDue.day;

  final String id;
  final TransactionType type;
  final double amount;
  final String currency;
  final String accountId;
  final String? toAccountId;
  final String? categoryId;
  final String payee;
  final String note;
  final List<String> tags;
  final RecurrenceFrequency frequency;

  /// Every N periods (e.g. every 2 weeks).
  final int interval;
  final DateTime nextDue;
  final DateTime? endDate;

  /// When false the app reminds instead of creating automatically.
  final bool autoAdd;
  final bool isActive;
  final bool isPrivate;
  final String createdBy;
  final DateTime createdAt;
  final DateTime? lastGeneratedAt;

  /// Day of month the schedule is anchored to, so a rule created on the 31st
  /// still fires on the 31st after passing through a short month.
  final int anchorDay;

  String get frequencyLabel {
    if (interval == 1) return frequency.label;
    final unit = switch (frequency) {
      RecurrenceFrequency.daily => 'days',
      RecurrenceFrequency.weekly => 'weeks',
      RecurrenceFrequency.monthly => 'months',
      RecurrenceFrequency.yearly => 'years',
    };
    return 'Every $interval $unit';
  }

  /// Computes the occurrence after [from], keeping the day-of-month stable.
  DateTime nextAfter(DateTime from) {
    switch (frequency) {
      case RecurrenceFrequency.daily:
        return from.add(Duration(days: interval));
      case RecurrenceFrequency.weekly:
        return from.add(Duration(days: 7 * interval));
      case RecurrenceFrequency.monthly:
        return _addMonths(from, interval);
      case RecurrenceFrequency.yearly:
        return _addMonths(from, 12 * interval);
    }
  }

  DateTime _addMonths(DateTime date, int months) {
    final totalMonths = date.month - 1 + months;
    final year = date.year + (totalMonths - totalMonths % 12) ~/ 12;
    final month = totalMonths % 12 + 1;
    final lastDay = DateTime(year, month + 1, 0).day;
    final wanted = anchorDay > date.day ? anchorDay : date.day;
    final day = wanted > lastDay ? lastDay : wanted;
    return DateTime(year, month, day, date.hour, date.minute);
  }

  /// All occurrences that are due on or before [until] starting at [nextDue].
  List<DateTime> dueOccurrences(DateTime until) {
    final result = <DateTime>[];
    var cursor = nextDue;
    var guard = 0;
    while (!cursor.isAfter(until) && guard < 500) {
      if (endDate != null && cursor.isAfter(endDate!)) break;
      result.add(cursor);
      cursor = nextAfter(cursor);
      guard++;
    }
    return result;
  }

  RecurringRule copyWith({
    TransactionType? type,
    double? amount,
    String? currency,
    String? accountId,
    String? toAccountId,
    bool clearToAccount = false,
    String? categoryId,
    bool clearCategory = false,
    String? payee,
    String? note,
    List<String>? tags,
    RecurrenceFrequency? frequency,
    int? interval,
    DateTime? nextDue,
    DateTime? endDate,
    bool clearEndDate = false,
    bool? autoAdd,
    bool? isActive,
    bool? isPrivate,
    DateTime? lastGeneratedAt,
    int? anchorDay,
  }) {
    return RecurringRule(
      id: id,
      type: type ?? this.type,
      amount: amount ?? this.amount,
      currency: currency ?? this.currency,
      accountId: accountId ?? this.accountId,
      toAccountId: clearToAccount ? null : (toAccountId ?? this.toAccountId),
      categoryId: clearCategory ? null : (categoryId ?? this.categoryId),
      payee: payee ?? this.payee,
      note: note ?? this.note,
      tags: tags ?? this.tags,
      frequency: frequency ?? this.frequency,
      interval: interval ?? this.interval,
      nextDue: nextDue ?? this.nextDue,
      endDate: clearEndDate ? null : (endDate ?? this.endDate),
      autoAdd: autoAdd ?? this.autoAdd,
      isActive: isActive ?? this.isActive,
      isPrivate: isPrivate ?? this.isPrivate,
      createdBy: createdBy,
      createdAt: createdAt,
      lastGeneratedAt: lastGeneratedAt ?? this.lastGeneratedAt,
      anchorDay: anchorDay ?? (nextDue != null ? nextDue.day : this.anchorDay),
    );
  }

  Map<String, dynamic> toMap() => {
        'type': type.storageKey,
        'amount': amount,
        'currency': currency,
        'accountId': accountId,
        'toAccountId': toAccountId,
        'categoryId': categoryId,
        'payee': payee,
        'note': note,
        'tags': tags,
        'frequency': frequency.storageKey,
        'interval': interval,
        'nextDue': nextDue,
        'endDate': endDate,
        'autoAdd': autoAdd,
        'isActive': isActive,
        'isPrivate': isPrivate,
        'createdBy': createdBy,
        'createdAt': createdAt,
        'lastGeneratedAt': lastGeneratedAt,
        'anchorDay': anchorDay,
      };

  factory RecurringRule.fromMap(String id, Map<String, dynamic> map) {
    return RecurringRule(
      id: id,
      type: TransactionType.fromKey(map['type'] as String?),
      amount: parseDouble(map['amount']),
      currency: parseString(map['currency'], 'INR'),
      accountId: parseString(map['accountId']),
      toAccountId: map['toAccountId'] as String?,
      categoryId: map['categoryId'] as String?,
      payee: parseString(map['payee']),
      note: parseString(map['note']),
      tags: parseStringList(map['tags']),
      frequency: RecurrenceFrequency.fromKey(map['frequency'] as String?),
      interval: parseInt(map['interval'], 1).clamp(1, 365),
      nextDue: parseDate(map['nextDue']),
      endDate: parseDateOrNull(map['endDate']),
      autoAdd: parseBool(map['autoAdd'], true),
      isActive: parseBool(map['isActive'], true),
      isPrivate: parseBool(map['isPrivate']),
      createdBy: parseString(map['createdBy']),
      createdAt: parseDate(map['createdAt']),
      lastGeneratedAt: parseDateOrNull(map['lastGeneratedAt']),
      anchorDay: map['anchorDay'] == null ? null : parseInt(map['anchorDay']).clamp(1, 31),
    );
  }
}
