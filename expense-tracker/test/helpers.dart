import 'package:expense_budget_manager/models/models.dart';

final now = DateTime(2026, 11, 15, 12);

Transaction tx({
  String id = 't',
  TransactionType type = TransactionType.expense,
  required double amount,
  required DateTime date,
  String? categoryId,
  String accountId = 'cash',
  String? toAccountId,
  String payee = '',
  String createdBy = 'u1',
  bool isPrivate = false,
  List<String> tags = const [],
}) {
  return Transaction(
    id: id,
    type: type,
    amount: amount,
    currency: 'INR',
    originalAmount: amount,
    accountId: accountId,
    toAccountId: toAccountId,
    categoryId: categoryId,
    date: date,
    payee: payee,
    tags: tags,
    isPrivate: isPrivate,
    createdBy: createdBy,
    createdAt: date,
    updatedAt: date,
  );
}

Category cat(String id, String name, {CategoryKind kind = CategoryKind.expense, String? parentId}) => Category(
      id: id,
      name: name,
      kind: kind,
      iconKey: 'category',
      color: 0xFF000000,
      parentId: parentId,
    );

Account acc(String id, {double initial = 0, AccountType type = AccountType.cash}) => Account(
      id: id,
      name: id,
      type: type,
      currency: 'INR',
      initialBalance: initial,
      createdBy: 'u1',
      createdAt: now,
    );

Household household({List<String> members = const ['u1', 'u2']}) => Household(
      id: 'h',
      name: 'Home',
      ownerId: 'u1',
      baseCurrency: 'INR',
      memberIds: members,
      members: {
        for (final m in members)
          m: HouseholdMember(uid: m, name: 'User $m', role: m == 'u1' ? MemberRole.owner : MemberRole.adult, joinedAt: now),
      },
      inviteCode: 'ABCD2345',
      createdAt: now,
    );
