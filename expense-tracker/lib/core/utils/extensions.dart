import 'package:material_ui/material_ui.dart';

extension ContextX on BuildContext {
  ThemeData get theme => Theme.of(this);
  ColorScheme get colors => Theme.of(this).colorScheme;
  TextTheme get text => Theme.of(this).textTheme;
  bool get isDark => Theme.of(this).brightness == Brightness.dark;

  void showSnack(String message, {bool error = false}) {
    final messenger = ScaffoldMessenger.maybeOf(this);
    if (messenger == null) return;
    messenger
      ..hideCurrentSnackBar()
      ..showSnackBar(
        SnackBar(
          content: Text(message),
          behavior: SnackBarBehavior.floating,
          backgroundColor: error ? colors.error : null,
        ),
      );
  }
}

extension IntColorX on int {
  Color get asColor => Color(this);
}

extension ColorX on Color {
  /// ARGB integer for persistence.
  int get argb => toARGB32();

  Color withAlphaFraction(double fraction) => withValues(alpha: fraction);
}

extension StringX on String {
  String get capitalized => isEmpty ? this : this[0].toUpperCase() + substring(1);
}

extension ListSum on Iterable<double> {
  double get sum => fold(0, (a, b) => a + b);
}
