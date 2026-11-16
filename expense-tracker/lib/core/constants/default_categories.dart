import '../../models/models.dart';

class DefaultCategorySpec {
  const DefaultCategorySpec(this.name, this.iconKey, this.color, this.kind);
  final String name;
  final String iconKey;
  final int color;
  final CategoryKind kind;
}

const List<DefaultCategorySpec> kDefaultCategories = [
  DefaultCategorySpec('Food & Dining', 'restaurant', 0xFFF4511E, CategoryKind.expense),
  DefaultCategorySpec('Groceries', 'local_grocery_store', 0xFF43A047, CategoryKind.expense),
  DefaultCategorySpec('Transport', 'directions_bus', 0xFF1E88E5, CategoryKind.expense),
  DefaultCategorySpec('Fuel', 'local_gas_station', 0xFF546E7A, CategoryKind.expense),
  DefaultCategorySpec('Shopping', 'shopping_bag', 0xFFD81B60, CategoryKind.expense),
  DefaultCategorySpec('Bills & Utilities', 'bolt', 0xFFFB8C00, CategoryKind.expense),
  DefaultCategorySpec('Rent & Housing', 'home', 0xFF6D4C41, CategoryKind.expense),
  DefaultCategorySpec('Health', 'local_hospital', 0xFFE53935, CategoryKind.expense),
  DefaultCategorySpec('Education', 'school', 0xFF3949AB, CategoryKind.expense),
  DefaultCategorySpec('Entertainment', 'movie', 0xFF8E24AA, CategoryKind.expense),
  DefaultCategorySpec('Subscriptions', 'subscriptions', 0xFF5E35B1, CategoryKind.expense),
  DefaultCategorySpec('Travel', 'flight', 0xFF00ACC1, CategoryKind.expense),
  DefaultCategorySpec('Personal Care', 'spa', 0xFF00897B, CategoryKind.expense),
  DefaultCategorySpec('Kids', 'child_care', 0xFFFDD835, CategoryKind.expense),
  DefaultCategorySpec('Pets', 'pets', 0xFF7CB342, CategoryKind.expense),
  DefaultCategorySpec('Gifts & Donations', 'volunteer_activism', 0xFFEC407A, CategoryKind.expense),
  DefaultCategorySpec('Insurance', 'shield', 0xFF039BE5, CategoryKind.expense),
  DefaultCategorySpec('EMI & Loans', 'request_quote', 0xFF8D6E63, CategoryKind.expense),
  DefaultCategorySpec('Other Expense', 'more_horiz', 0xFF78909C, CategoryKind.expense),
  DefaultCategorySpec('Salary', 'work', 0xFF43A047, CategoryKind.income),
  DefaultCategorySpec('Business', 'storefront', 0xFF00897B, CategoryKind.income),
  DefaultCategorySpec('Freelance', 'laptop', 0xFF1E88E5, CategoryKind.income),
  DefaultCategorySpec('Investments', 'trending_up', 0xFF5E35B1, CategoryKind.income),
  DefaultCategorySpec('Rental Income', 'real_estate_agent', 0xFF6D4C41, CategoryKind.income),
  DefaultCategorySpec('Gifts Received', 'redeem', 0xFFD81B60, CategoryKind.income),
  DefaultCategorySpec('Refunds', 'undo', 0xFF00ACC1, CategoryKind.income),
  DefaultCategorySpec('Other Income', 'more_horiz', 0xFF78909C, CategoryKind.income),
];
