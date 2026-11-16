import 'package:material_ui/material_ui.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// Browser-local preferences (never synced): appearance and alert behaviour.
class AppSettings {
  const AppSettings({
    this.themeMode = ThemeMode.system,
    this.accentIndex = 0,
    this.budgetAlerts = true,
    this.browserNotifications = false,
    this.hideAmounts = false,
    this.compactLayout = false,
  });

  final ThemeMode themeMode;
  final int accentIndex;

  /// Warn when a transaction pushes a budget past its threshold.
  final bool budgetAlerts;

  /// Also raise a browser notification (requires permission).
  final bool browserNotifications;

  /// Privacy mode: masks amounts on the dashboard.
  final bool hideAmounts;
  final bool compactLayout;

  AppSettings copyWith({
    ThemeMode? themeMode,
    int? accentIndex,
    bool? budgetAlerts,
    bool? browserNotifications,
    bool? hideAmounts,
    bool? compactLayout,
  }) {
    return AppSettings(
      themeMode: themeMode ?? this.themeMode,
      accentIndex: accentIndex ?? this.accentIndex,
      budgetAlerts: budgetAlerts ?? this.budgetAlerts,
      browserNotifications: browserNotifications ?? this.browserNotifications,
      hideAmounts: hideAmounts ?? this.hideAmounts,
      compactLayout: compactLayout ?? this.compactLayout,
    );
  }

  static AppSettings load(SharedPreferences prefs) {
    final modeIndex = prefs.getInt('themeMode') ?? ThemeMode.system.index;
    return AppSettings(
      themeMode: ThemeMode.values[modeIndex.clamp(0, ThemeMode.values.length - 1)],
      accentIndex: prefs.getInt('accentIndex') ?? 0,
      budgetAlerts: prefs.getBool('budgetAlerts') ?? true,
      browserNotifications: prefs.getBool('browserNotifications') ?? false,
      hideAmounts: prefs.getBool('hideAmounts') ?? false,
      compactLayout: prefs.getBool('compactLayout') ?? false,
    );
  }

  Future<void> persist(SharedPreferences prefs) async {
    await prefs.setInt('themeMode', themeMode.index);
    await prefs.setInt('accentIndex', accentIndex);
    await prefs.setBool('budgetAlerts', budgetAlerts);
    await prefs.setBool('browserNotifications', browserNotifications);
    await prefs.setBool('hideAmounts', hideAmounts);
    await prefs.setBool('compactLayout', compactLayout);
  }
}
