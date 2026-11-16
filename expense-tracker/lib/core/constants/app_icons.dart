import 'package:material_ui/material_ui.dart';

/// Icon catalogue keyed by stable string names. Categories, accounts and goals
/// store the key, never the code point, so icon font upgrades stay safe.
const Map<String, IconData> kIconCatalog = {
  // Food & home
  'restaurant': Icons.restaurant_rounded,
  'fastfood': Icons.fastfood_rounded,
  'local_cafe': Icons.local_cafe_rounded,
  'local_grocery_store': Icons.local_grocery_store_rounded,
  'shopping_bag': Icons.shopping_bag_rounded,
  'shopping_cart': Icons.shopping_cart_rounded,
  'home': Icons.home_rounded,
  'house': Icons.house_rounded,
  'chair': Icons.chair_rounded,
  'cleaning_services': Icons.cleaning_services_rounded,
  'bolt': Icons.bolt_rounded,
  'water_drop': Icons.water_drop_rounded,
  'wifi': Icons.wifi_rounded,
  'phone_android': Icons.phone_android_rounded,
  'receipt_long': Icons.receipt_long_rounded,
  // Transport
  'directions_car': Icons.directions_car_rounded,
  'local_gas_station': Icons.local_gas_station_rounded,
  'directions_bus': Icons.directions_bus_rounded,
  'two_wheeler': Icons.two_wheeler_rounded,
  'train': Icons.train_rounded,
  'flight': Icons.flight_rounded,
  'local_taxi': Icons.local_taxi_rounded,
  'local_parking': Icons.local_parking_rounded,
  // Health & personal
  'local_hospital': Icons.local_hospital_rounded,
  'medication': Icons.medication_rounded,
  'fitness_center': Icons.fitness_center_rounded,
  'spa': Icons.spa_rounded,
  'content_cut': Icons.content_cut_rounded,
  'checkroom': Icons.checkroom_rounded,
  'child_care': Icons.child_care_rounded,
  'pets': Icons.pets_rounded,
  'school': Icons.school_rounded,
  'menu_book': Icons.menu_book_rounded,
  // Fun
  'movie': Icons.movie_rounded,
  'sports_esports': Icons.sports_esports_rounded,
  'music_note': Icons.music_note_rounded,
  'subscriptions': Icons.subscriptions_rounded,
  'sports_soccer': Icons.sports_soccer_rounded,
  'beach_access': Icons.beach_access_rounded,
  'celebration': Icons.celebration_rounded,
  'card_giftcard': Icons.card_giftcard_rounded,
  'volunteer_activism': Icons.volunteer_activism_rounded,
  // Money
  'payments': Icons.payments_rounded,
  'account_balance': Icons.account_balance_rounded,
  'account_balance_wallet': Icons.account_balance_wallet_rounded,
  'wallet': Icons.wallet_rounded,
  'credit_card': Icons.credit_card_rounded,
  'savings': Icons.savings_rounded,
  'trending_up': Icons.trending_up_rounded,
  'currency_exchange': Icons.currency_exchange_rounded,
  'work': Icons.work_rounded,
  'business_center': Icons.business_center_rounded,
  'laptop': Icons.laptop_rounded,
  'storefront': Icons.storefront_rounded,
  'real_estate_agent': Icons.real_estate_agent_rounded,
  'shield': Icons.shield_rounded,
  'request_quote': Icons.request_quote_rounded,
  'undo': Icons.undo_rounded,
  'redeem': Icons.redeem_rounded,
  'category': Icons.category_rounded,
  'more_horiz': Icons.more_horiz_rounded,
  'star': Icons.star_rounded,
  'favorite': Icons.favorite_rounded,
  'build': Icons.build_rounded,
  'handyman': Icons.handyman_rounded,
  'luggage': Icons.luggage_rounded,
  'hotel': Icons.hotel_rounded,
  'diamond': Icons.diamond_rounded,
  'directions_bike': Icons.directions_bike_rounded,
  'emoji_events': Icons.emoji_events_rounded,
  'rocket_launch': Icons.rocket_launch_rounded,
};

IconData iconFor(String? key) => kIconCatalog[key] ?? Icons.category_rounded;

/// Vivid, high-contrast colours for member avatars and per-member charts
/// (no greys, browns or pale yellows, which read as "disabled").
const List<int> kMemberPalette = [
  0xFF0284C7, // sky
  0xFFE11D48, // rose
  0xFF059669, // emerald
  0xFFEA580C, // orange
  0xFF7C3AED, // violet
  0xFFDB2777, // pink
  0xFF0D9488, // teal
  0xFFCA8A04, // amber
];

/// Stable colour choice for a member who joins a household. Uses a simple
/// character sum so the result is the same on every platform.
int memberColorFor(String uid) {
  final sum = uid.codeUnits.fold<int>(0, (a, b) => a + b);
  return kMemberPalette[sum % kMemberPalette.length];
}

/// Curated palette for categories, accounts, goals and member avatars.
const List<int> kPalette = [
  0xFFE53935, // red
  0xFFF4511E, // deep orange
  0xFFFB8C00, // orange
  0xFFFDD835, // yellow
  0xFF7CB342, // light green
  0xFF43A047, // green
  0xFF00897B, // teal
  0xFF00ACC1, // cyan
  0xFF039BE5, // light blue
  0xFF1E88E5, // blue
  0xFF3949AB, // indigo
  0xFF5E35B1, // deep purple
  0xFF8E24AA, // purple
  0xFFD81B60, // pink
  0xFF6D4C41, // brown
  0xFF546E7A, // blue grey
];
