import 'enums.dart';
import 'model_utils.dart';

class Account {
  const Account({
    required this.id,
    required this.name,
    required this.type,
    required this.currency,
    this.initialBalance = 0,
    this.color = 0xFF2E7D32,
    this.iconKey,
    this.isArchived = false,
    this.isShared = true,
    this.excludeFromTotals = false,
    this.creditLimit,
    required this.createdBy,
    required this.createdAt,
    this.sortOrder = 0,
  });

  final String id;
  final String name;
  final AccountType type;
  final String currency;
  final double initialBalance;
  final int color;
  final String? iconKey;
  final bool isArchived;

  /// Shared accounts are visible to every household member; private ones only
  /// to their creator.
  final bool isShared;
  final bool excludeFromTotals;
  final double? creditLimit;
  final String createdBy;
  final DateTime createdAt;
  final int sortOrder;

  String get resolvedIconKey => iconKey ?? type.iconKey;

  Account copyWith({
    String? name,
    AccountType? type,
    String? currency,
    double? initialBalance,
    int? color,
    String? iconKey,
    bool? isArchived,
    bool? isShared,
    bool? excludeFromTotals,
    double? creditLimit,
    bool clearCreditLimit = false,
    int? sortOrder,
  }) {
    return Account(
      id: id,
      name: name ?? this.name,
      type: type ?? this.type,
      currency: currency ?? this.currency,
      initialBalance: initialBalance ?? this.initialBalance,
      color: color ?? this.color,
      iconKey: iconKey ?? this.iconKey,
      isArchived: isArchived ?? this.isArchived,
      isShared: isShared ?? this.isShared,
      excludeFromTotals: excludeFromTotals ?? this.excludeFromTotals,
      creditLimit: clearCreditLimit ? null : (creditLimit ?? this.creditLimit),
      createdBy: createdBy,
      createdAt: createdAt,
      sortOrder: sortOrder ?? this.sortOrder,
    );
  }

  Map<String, dynamic> toMap() => {
        'name': name,
        'type': type.storageKey,
        'currency': currency,
        'initialBalance': initialBalance,
        'color': color,
        'iconKey': iconKey,
        'isArchived': isArchived,
        'isShared': isShared,
        'excludeFromTotals': excludeFromTotals,
        'creditLimit': creditLimit,
        'createdBy': createdBy,
        'createdAt': createdAt,
        'sortOrder': sortOrder,
      };

  factory Account.fromMap(String id, Map<String, dynamic> map) {
    return Account(
      id: id,
      name: parseString(map['name'], 'Account'),
      type: AccountType.fromKey(map['type'] as String?),
      currency: parseString(map['currency'], 'INR'),
      initialBalance: parseDouble(map['initialBalance']),
      color: parseInt(map['color'], 0xFF2E7D32),
      iconKey: map['iconKey'] as String?,
      isArchived: parseBool(map['isArchived']),
      isShared: parseBool(map['isShared'], true),
      excludeFromTotals: parseBool(map['excludeFromTotals']),
      creditLimit: map['creditLimit'] == null ? null : parseDouble(map['creditLimit']),
      createdBy: parseString(map['createdBy']),
      createdAt: parseDate(map['createdAt']),
      sortOrder: parseInt(map['sortOrder']),
    );
  }
}
