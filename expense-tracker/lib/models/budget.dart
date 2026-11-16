import 'enums.dart';
import 'model_utils.dart';

class Budget {
  const Budget({
    required this.id,
    required this.name,
    required this.amount,
    required this.period,
    required this.startDate,
    this.endDate,
    this.categoryIds = const [],
    this.accountIds = const [],
    this.rollover = false,
    this.alertThreshold = 0.8,
    this.isShared = true,
    this.memberIds = const [],
    required this.createdBy,
    required this.createdAt,
    this.isArchived = false,
    this.color = 0xFF1E88E5,
  });

  final String id;
  final String name;
  final double amount;
  final BudgetPeriod period;
  final DateTime startDate;

  /// Only used for [BudgetPeriod.custom].
  final DateTime? endDate;

  /// Empty means "all expense categories".
  final List<String> categoryIds;

  /// Empty means "all accounts".
  final List<String> accountIds;
  final bool rollover;

  /// Fraction (0-1) of the budget at which to warn the user.
  final double alertThreshold;
  final bool isShared;

  /// Restrict the budget to transactions by these members. Empty = everyone.
  final List<String> memberIds;
  final String createdBy;
  final DateTime createdAt;
  final bool isArchived;
  final int color;

  bool get isOverall => categoryIds.isEmpty;

  Budget copyWith({
    String? name,
    double? amount,
    BudgetPeriod? period,
    DateTime? startDate,
    DateTime? endDate,
    bool clearEndDate = false,
    List<String>? categoryIds,
    List<String>? accountIds,
    bool? rollover,
    double? alertThreshold,
    bool? isShared,
    List<String>? memberIds,
    bool? isArchived,
    int? color,
  }) {
    return Budget(
      id: id,
      name: name ?? this.name,
      amount: amount ?? this.amount,
      period: period ?? this.period,
      startDate: startDate ?? this.startDate,
      endDate: clearEndDate ? null : (endDate ?? this.endDate),
      categoryIds: categoryIds ?? this.categoryIds,
      accountIds: accountIds ?? this.accountIds,
      rollover: rollover ?? this.rollover,
      alertThreshold: alertThreshold ?? this.alertThreshold,
      isShared: isShared ?? this.isShared,
      memberIds: memberIds ?? this.memberIds,
      createdBy: createdBy,
      createdAt: createdAt,
      isArchived: isArchived ?? this.isArchived,
      color: color ?? this.color,
    );
  }

  Map<String, dynamic> toMap() => {
        'name': name,
        'amount': amount,
        'period': period.storageKey,
        'startDate': startDate,
        'endDate': endDate,
        'categoryIds': categoryIds,
        'accountIds': accountIds,
        'rollover': rollover,
        'alertThreshold': alertThreshold,
        'isShared': isShared,
        'memberIds': memberIds,
        'createdBy': createdBy,
        'createdAt': createdAt,
        'isArchived': isArchived,
        'color': color,
      };

  factory Budget.fromMap(String id, Map<String, dynamic> map) {
    return Budget(
      id: id,
      name: parseString(map['name'], 'Budget'),
      amount: parseDouble(map['amount']),
      period: BudgetPeriod.fromKey(map['period'] as String?),
      startDate: parseDate(map['startDate']),
      endDate: parseDateOrNull(map['endDate']),
      categoryIds: parseStringList(map['categoryIds']),
      accountIds: parseStringList(map['accountIds']),
      rollover: parseBool(map['rollover']),
      alertThreshold: parseDouble(map['alertThreshold'], 0.8),
      isShared: parseBool(map['isShared'], true),
      memberIds: parseStringList(map['memberIds']),
      createdBy: parseString(map['createdBy']),
      createdAt: parseDate(map['createdAt']),
      isArchived: parseBool(map['isArchived']),
      color: parseInt(map['color'], 0xFF1E88E5),
    );
  }
}
