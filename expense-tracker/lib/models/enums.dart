/// Shared enumerations used across models. Every enum stores a stable string
/// key in Firestore (`storageKey`) so renaming a Dart identifier never breaks
/// persisted data.
library;

enum TransactionType {
  expense('expense', 'Expense'),
  income('income', 'Income'),
  transfer('transfer', 'Transfer');

  const TransactionType(this.storageKey, this.label);
  final String storageKey;
  final String label;

  static TransactionType fromKey(String? key) => TransactionType.values
      .firstWhere((e) => e.storageKey == key, orElse: () => expense);
}

enum CategoryKind {
  expense('expense', 'Expense'),
  income('income', 'Income');

  const CategoryKind(this.storageKey, this.label);
  final String storageKey;
  final String label;

  static CategoryKind fromKey(String? key) => CategoryKind.values
      .firstWhere((e) => e.storageKey == key, orElse: () => expense);
}

enum AccountType {
  cash('cash', 'Cash', 'payments'),
  bank('bank', 'Bank account', 'account_balance'),
  card('card', 'Credit card', 'credit_card'),
  wallet('wallet', 'Digital wallet', 'wallet'),
  savings('savings', 'Savings', 'savings'),
  investment('investment', 'Investment', 'trending_up'),
  other('other', 'Other', 'category');

  const AccountType(this.storageKey, this.label, this.iconKey);
  final String storageKey;
  final String label;
  final String iconKey;

  static AccountType fromKey(String? key) => AccountType.values
      .firstWhere((e) => e.storageKey == key, orElse: () => other);
}

enum BudgetPeriod {
  weekly('weekly', 'Weekly'),
  monthly('monthly', 'Monthly'),
  quarterly('quarterly', 'Quarterly'),
  yearly('yearly', 'Yearly'),
  custom('custom', 'Custom range');

  const BudgetPeriod(this.storageKey, this.label);
  final String storageKey;
  final String label;

  static BudgetPeriod fromKey(String? key) => BudgetPeriod.values
      .firstWhere((e) => e.storageKey == key, orElse: () => monthly);
}

enum RecurrenceFrequency {
  daily('daily', 'Daily'),
  weekly('weekly', 'Weekly'),
  monthly('monthly', 'Monthly'),
  yearly('yearly', 'Yearly');

  const RecurrenceFrequency(this.storageKey, this.label);
  final String storageKey;
  final String label;

  static RecurrenceFrequency fromKey(String? key) => RecurrenceFrequency.values
      .firstWhere((e) => e.storageKey == key, orElse: () => monthly);
}

enum MemberRole {
  owner('owner', 'Owner', 'Full control, can manage members and delete the household'),
  adult('adult', 'Adult', 'Can add and edit everything, manage budgets and categories'),
  child('child', 'Child', 'Can add their own expenses and view shared budgets');

  const MemberRole(this.storageKey, this.label, this.description);
  final String storageKey;
  final String label;
  final String description;

  bool get canManageMembers => this == owner;
  bool get canManageBudgets => this != child;
  bool get canEditOthersTransactions => this != child;

  static MemberRole fromKey(String? key) => MemberRole.values
      .firstWhere((e) => e.storageKey == key, orElse: () => adult);
}

enum ActivityAction {
  created('created'),
  updated('updated'),
  deleted('deleted'),
  joined('joined'),
  left('left');

  const ActivityAction(this.storageKey);
  final String storageKey;

  static ActivityAction fromKey(String? key) => ActivityAction.values
      .firstWhere((e) => e.storageKey == key, orElse: () => updated);
}
