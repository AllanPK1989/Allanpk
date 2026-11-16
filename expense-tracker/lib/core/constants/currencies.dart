class CurrencyInfo {
  const CurrencyInfo(this.code, this.symbol, this.name, {this.decimals = 2});
  final String code;
  final String symbol;
  final String name;
  final int decimals;
}

/// Currencies offered in pickers. Exchange rates are fetched at runtime; this
/// list only drives symbols, names and decimal handling.
const List<CurrencyInfo> kCurrencies = [
  CurrencyInfo('INR', '₹', 'Indian Rupee'),
  CurrencyInfo('USD', r'$', 'US Dollar'),
  CurrencyInfo('EUR', '€', 'Euro'),
  CurrencyInfo('GBP', '£', 'British Pound'),
  CurrencyInfo('AED', 'د.إ', 'UAE Dirham'),
  CurrencyInfo('SAR', '﷼', 'Saudi Riyal'),
  CurrencyInfo('SGD', r'S$', 'Singapore Dollar'),
  CurrencyInfo('MYR', 'RM', 'Malaysian Ringgit'),
  CurrencyInfo('AUD', r'A$', 'Australian Dollar'),
  CurrencyInfo('CAD', r'C$', 'Canadian Dollar'),
  CurrencyInfo('JPY', '¥', 'Japanese Yen', decimals: 0),
  CurrencyInfo('CNY', '¥', 'Chinese Yuan'),
  CurrencyInfo('CHF', 'CHF', 'Swiss Franc'),
  CurrencyInfo('HKD', r'HK$', 'Hong Kong Dollar'),
  CurrencyInfo('NZD', r'NZ$', 'New Zealand Dollar'),
  CurrencyInfo('SEK', 'kr', 'Swedish Krona'),
  CurrencyInfo('NOK', 'kr', 'Norwegian Krone'),
  CurrencyInfo('DKK', 'kr', 'Danish Krone'),
  CurrencyInfo('ZAR', 'R', 'South African Rand'),
  CurrencyInfo('BRL', r'R$', 'Brazilian Real'),
  CurrencyInfo('MXN', r'MX$', 'Mexican Peso'),
  CurrencyInfo('KRW', '₩', 'South Korean Won', decimals: 0),
  CurrencyInfo('THB', '฿', 'Thai Baht'),
  CurrencyInfo('IDR', 'Rp', 'Indonesian Rupiah', decimals: 0),
  CurrencyInfo('PHP', '₱', 'Philippine Peso'),
  CurrencyInfo('LKR', 'Rs', 'Sri Lankan Rupee'),
  CurrencyInfo('PKR', 'Rs', 'Pakistani Rupee'),
  CurrencyInfo('BDT', '৳', 'Bangladeshi Taka'),
  CurrencyInfo('NPR', 'Rs', 'Nepalese Rupee'),
  CurrencyInfo('QAR', 'ر.ق', 'Qatari Riyal'),
  CurrencyInfo('KWD', 'د.ك', 'Kuwaiti Dinar', decimals: 3),
  CurrencyInfo('OMR', 'ر.ع.', 'Omani Rial', decimals: 3),
  CurrencyInfo('BHD', '.د.ب', 'Bahraini Dinar', decimals: 3),
  CurrencyInfo('TRY', '₺', 'Turkish Lira'),
  CurrencyInfo('PLN', 'zł', 'Polish Zloty'),
  CurrencyInfo('CZK', 'Kč', 'Czech Koruna'),
  CurrencyInfo('ILS', '₪', 'Israeli Shekel'),
  CurrencyInfo('EGP', 'E£', 'Egyptian Pound'),
  CurrencyInfo('NGN', '₦', 'Nigerian Naira'),
  CurrencyInfo('KES', 'KSh', 'Kenyan Shilling'),
  CurrencyInfo('VND', '₫', 'Vietnamese Dong', decimals: 0),
];

const String kDefaultCurrency = 'INR';

CurrencyInfo currencyInfo(String code) {
  return kCurrencies.firstWhere(
    (c) => c.code == code,
    orElse: () => CurrencyInfo(code, code, code),
  );
}
