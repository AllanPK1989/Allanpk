import 'enums.dart';
import 'model_utils.dart';

/// A single ledger entry. Amounts are always stored in the household's base
/// currency (`amount`) alongside the original amount and currency the user
/// entered, so multi-currency spending can still be analysed consistently.
class Transaction {
  const Transaction({
    required this.id,
    required this.type,
    required this.amount,
    required this.currency,
    required this.originalAmount,
    this.exchangeRate = 1,
    required this.accountId,
    this.toAccountId,
    this.categoryId,
    required this.date,
    this.payee = '',
    this.note = '',
    this.tags = const [],
    this.receiptUrls = const [],
    this.isPrivate = false,
    required this.createdBy,
    this.createdByName = '',
    required this.createdAt,
    required this.updatedAt,
    this.recurringId,
    this.goalId,
  });

  final String id;
  final TransactionType type;

  /// Amount in the household base currency.
  final double amount;

  /// Currency the user entered the transaction in.
  final String currency;
  final double originalAmount;
  final double exchangeRate;
  final String accountId;
  final String? toAccountId;
  final String? categoryId;
  final DateTime date;
  final String payee;
  final String note;
  final List<String> tags;
  final List<String> receiptUrls;

  /// Private entries are only visible to their creator.
  final bool isPrivate;
  final String createdBy;
  final String createdByName;
  final DateTime createdAt;
  final DateTime updatedAt;
  final String? recurringId;
  final String? goalId;

  bool get isExpense => type == TransactionType.expense;
  bool get isIncome => type == TransactionType.income;
  bool get isTransfer => type == TransactionType.transfer;

  /// Signed amount from the perspective of net worth: income positive,
  /// expenses negative, transfers neutral.
  double get signedAmount => switch (type) {
        TransactionType.income => amount,
        TransactionType.expense => -amount,
        TransactionType.transfer => 0,
      };

  Transaction copyWith({
    TransactionType? type,
    double? amount,
    String? currency,
    double? originalAmount,
    double? exchangeRate,
    String? accountId,
    String? toAccountId,
    bool clearToAccount = false,
    String? categoryId,
    bool clearCategory = false,
    DateTime? date,
    String? payee,
    String? note,
    List<String>? tags,
    List<String>? receiptUrls,
    bool? isPrivate,
    DateTime? updatedAt,
    String? recurringId,
    String? goalId,
  }) {
    return Transaction(
      id: id,
      type: type ?? this.type,
      amount: amount ?? this.amount,
      currency: currency ?? this.currency,
      originalAmount: originalAmount ?? this.originalAmount,
      exchangeRate: exchangeRate ?? this.exchangeRate,
      accountId: accountId ?? this.accountId,
      toAccountId: clearToAccount ? null : (toAccountId ?? this.toAccountId),
      categoryId: clearCategory ? null : (categoryId ?? this.categoryId),
      date: date ?? this.date,
      payee: payee ?? this.payee,
      note: note ?? this.note,
      tags: tags ?? this.tags,
      receiptUrls: receiptUrls ?? this.receiptUrls,
      isPrivate: isPrivate ?? this.isPrivate,
      createdBy: createdBy,
      createdByName: createdByName,
      createdAt: createdAt,
      updatedAt: updatedAt ?? this.updatedAt,
      recurringId: recurringId ?? this.recurringId,
      goalId: goalId ?? this.goalId,
    );
  }

  Map<String, dynamic> toMap() => {
        'type': type.storageKey,
        'amount': amount,
        'currency': currency,
        'originalAmount': originalAmount,
        'exchangeRate': exchangeRate,
        'accountId': accountId,
        'toAccountId': toAccountId,
        'categoryId': categoryId,
        'date': date,
        'payee': payee,
        'note': note,
        'tags': tags,
        'receiptUrls': receiptUrls,
        'isPrivate': isPrivate,
        'createdBy': createdBy,
        'createdByName': createdByName,
        'createdAt': createdAt,
        'updatedAt': updatedAt,
        'recurringId': recurringId,
        'goalId': goalId,
        // Denormalised for cheap range queries and reporting.
        'year': date.year,
        'month': date.month,
      };

  factory Transaction.fromMap(String id, Map<String, dynamic> map) {
    final amount = parseDouble(map['amount']);
    return Transaction(
      id: id,
      type: TransactionType.fromKey(map['type'] as String?),
      amount: amount,
      currency: parseString(map['currency'], 'INR'),
      originalAmount: parseDouble(map['originalAmount'], amount),
      exchangeRate: parseDouble(map['exchangeRate'], 1),
      accountId: parseString(map['accountId']),
      toAccountId: map['toAccountId'] as String?,
      categoryId: map['categoryId'] as String?,
      date: parseDate(map['date']),
      payee: parseString(map['payee']),
      note: parseString(map['note']),
      tags: parseStringList(map['tags']),
      receiptUrls: parseStringList(map['receiptUrls']),
      isPrivate: parseBool(map['isPrivate']),
      createdBy: parseString(map['createdBy']),
      createdByName: parseString(map['createdByName']),
      createdAt: parseDate(map['createdAt']),
      updatedAt: parseDate(map['updatedAt']),
      recurringId: map['recurringId'] as String?,
      goalId: map['goalId'] as String?,
    );
  }
}
