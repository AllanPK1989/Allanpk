import 'package:material_ui/material_ui.dart';

/// Selectable accent seeds. The index is persisted in settings.
class AccentOption {
  const AccentOption(this.name, this.seed);
  final String name;
  final Color seed;
}

const List<AccentOption> kAccentOptions = [
  AccentOption('Indigo', Color(0xFF4F46E5)),
  AccentOption('Emerald', Color(0xFF059669)),
  AccentOption('Ocean', Color(0xFF0284C7)),
  AccentOption('Sunset', Color(0xFFEA580C)),
  AccentOption('Rose', Color(0xFFE11D48)),
  AccentOption('Violet', Color(0xFF7C3AED)),
  AccentOption('Teal', Color(0xFF0D9488)),
  AccentOption('Slate', Color(0xFF475569)),
];

class AppTheme {
  AppTheme._();

  static const String fontFamily = 'Inter';

  /// Semantic colours that stay the same across accents.
  static const Color income = Color(0xFF16A34A);
  static const Color expense = Color(0xFFDC2626);
  static const Color transfer = Color(0xFF2563EB);
  static const Color warning = Color(0xFFF59E0B);

  static ThemeData light(Color seed) => _build(seed, Brightness.light);
  static ThemeData dark(Color seed) => _build(seed, Brightness.dark);

  static ThemeData _build(Color seed, Brightness brightness) {
    final scheme = ColorScheme.fromSeed(
      seedColor: seed,
      brightness: brightness,
      dynamicSchemeVariant: DynamicSchemeVariant.tonalSpot,
    );
    final isDark = brightness == Brightness.dark;
    final surface = isDark ? const Color(0xFF0F1115) : const Color(0xFFF7F7FA);
    final card = isDark ? const Color(0xFF181B22) : Colors.white;

    final base = ThemeData(
      useMaterial3: true,
      colorScheme: scheme.copyWith(surface: surface, surfaceContainerLowest: card),
      brightness: brightness,
      fontFamily: fontFamily,
      scaffoldBackgroundColor: surface,
      splashFactory: InkSparkle.splashFactory,
      visualDensity: VisualDensity.standard,
    );

    final textTheme = base.textTheme.apply(fontFamily: fontFamily).copyWith(
          displayLarge: base.textTheme.displayLarge?.copyWith(fontWeight: FontWeight.w700, letterSpacing: -1),
          displayMedium: base.textTheme.displayMedium?.copyWith(fontWeight: FontWeight.w700, letterSpacing: -0.8),
          displaySmall: base.textTheme.displaySmall?.copyWith(fontWeight: FontWeight.w700, letterSpacing: -0.5),
          headlineLarge: base.textTheme.headlineLarge?.copyWith(fontWeight: FontWeight.w700, letterSpacing: -0.5),
          headlineMedium: base.textTheme.headlineMedium?.copyWith(fontWeight: FontWeight.w700, letterSpacing: -0.4),
          headlineSmall: base.textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.w600, letterSpacing: -0.3),
          titleLarge: base.textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w600, letterSpacing: -0.2),
          titleMedium: base.textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w600),
          titleSmall: base.textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w600),
          labelLarge: base.textTheme.labelLarge?.copyWith(fontWeight: FontWeight.w600),
        );

    return base.copyWith(
      textTheme: textTheme,
      appBarTheme: AppBarTheme(
        backgroundColor: surface,
        surfaceTintColor: Colors.transparent,
        elevation: 0,
        scrolledUnderElevation: 0,
        centerTitle: false,
        titleTextStyle: textTheme.titleLarge?.copyWith(color: scheme.onSurface),
        iconTheme: IconThemeData(color: scheme.onSurface),
      ),
      cardTheme: CardThemeData(
        color: card,
        elevation: 0,
        surfaceTintColor: Colors.transparent,
        margin: EdgeInsets.zero,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(20),
          side: BorderSide(color: scheme.outlineVariant.withValues(alpha: isDark ? 0.4 : 0.6)),
        ),
      ),
      navigationBarTheme: NavigationBarThemeData(
        backgroundColor: card,
        surfaceTintColor: Colors.transparent,
        indicatorColor: scheme.primaryContainer,
        elevation: 0,
        height: 68,
        labelTextStyle: WidgetStateProperty.resolveWith(
          (states) => textTheme.labelSmall?.copyWith(
            fontWeight: states.contains(WidgetState.selected) ? FontWeight.w700 : FontWeight.w500,
            color: states.contains(WidgetState.selected) ? scheme.onSurface : scheme.onSurfaceVariant,
          ),
        ),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: isDark ? const Color(0xFF1F232B) : const Color(0xFFF1F2F6),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: BorderSide.none,
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: BorderSide.none,
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: BorderSide(color: scheme.primary, width: 1.5),
        ),
        errorBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: BorderSide(color: scheme.error),
        ),
        focusedErrorBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: BorderSide(color: scheme.error, width: 1.5),
        ),
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
        labelStyle: textTheme.bodyMedium?.copyWith(color: scheme.onSurfaceVariant),
      ),
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          minimumSize: const Size.fromHeight(52),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
          textStyle: textTheme.labelLarge?.copyWith(fontSize: 16),
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          minimumSize: const Size.fromHeight(52),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
          side: BorderSide(color: scheme.outlineVariant),
          textStyle: textTheme.labelLarge?.copyWith(fontSize: 16),
        ),
      ),
      textButtonTheme: TextButtonThemeData(
        style: TextButton.styleFrom(
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        ),
      ),
      segmentedButtonTheme: SegmentedButtonThemeData(
        style: SegmentedButton.styleFrom(
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
          side: BorderSide(color: scheme.outlineVariant),
        ),
      ),
      chipTheme: ChipThemeData(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
        side: BorderSide(color: scheme.outlineVariant),
        labelStyle: textTheme.labelMedium,
      ),
      floatingActionButtonTheme: FloatingActionButtonThemeData(
        backgroundColor: scheme.primary,
        foregroundColor: scheme.onPrimary,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
        elevation: 2,
      ),
      dialogTheme: DialogThemeData(
        backgroundColor: card,
        surfaceTintColor: Colors.transparent,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(24)),
      ),
      bottomSheetTheme: BottomSheetThemeData(
        backgroundColor: card,
        surfaceTintColor: Colors.transparent,
        showDragHandle: true,
        shape: const RoundedRectangleBorder(
          borderRadius: BorderRadius.vertical(top: Radius.circular(28)),
        ),
      ),
      listTileTheme: ListTileThemeData(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
        iconColor: scheme.onSurfaceVariant,
      ),
      dividerTheme: DividerThemeData(color: scheme.outlineVariant.withValues(alpha: 0.5), space: 1),
      snackBarTheme: SnackBarThemeData(
        behavior: SnackBarBehavior.floating,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      ),
      switchTheme: SwitchThemeData(
        thumbIcon: WidgetStateProperty.resolveWith(
          (states) => states.contains(WidgetState.selected) ? const Icon(Icons.check, size: 14) : null,
        ),
      ),
      progressIndicatorTheme: ProgressIndicatorThemeData(
        linearTrackColor: scheme.surfaceContainerHighest,
      ),
      pageTransitionsTheme: const PageTransitionsTheme(
        builders: {
          TargetPlatform.android: FadeForwardsPageTransitionsBuilder(),
          TargetPlatform.iOS: FadeForwardsPageTransitionsBuilder(),
          TargetPlatform.macOS: FadeForwardsPageTransitionsBuilder(),
          TargetPlatform.linux: FadeForwardsPageTransitionsBuilder(),
          TargetPlatform.windows: FadeForwardsPageTransitionsBuilder(),
        },
      ),
    );
  }
}
