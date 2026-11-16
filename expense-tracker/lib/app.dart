import 'package:flutter/gestures.dart' show PointerDeviceKind;
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:material_ui/material_ui.dart';

import 'core/theme/app_theme.dart';
import 'features/auth/auth_providers.dart';
import 'features/household/household_providers.dart';
import 'router.dart';

final _messengerKey = GlobalKey<ScaffoldMessengerState>(debugLabel: 'messenger');

class ExpenseBudgetApp extends ConsumerWidget {
  const ExpenseBudgetApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final settings = ref.watch(appSettingsProvider);
    final router = ref.watch(routerProvider);
    final seed = kAccentOptions[settings.accentIndex.clamp(0, kAccentOptions.length - 1)].seed;

    // Keep the recurring processor alive while signed in.
    ref.watch(recurringProcessorProvider);

    // Removed from the active household by its owner: say so. Listening also
    // keeps the membership guard running.
    ref.listen(removalNoticeProvider, (previous, next) {
      final notice = next.value;
      if (notice == null || identical(notice, previous?.value)) return;
      _messengerKey.currentState
        ?..hideCurrentSnackBar()
        ..showSnackBar(
          SnackBar(content: Text(notice.message), behavior: SnackBarBehavior.floating),
        );
      // Pages of the old household (a budget, a transaction) mean nothing in
      // the new one, so start on its dashboard. With no household left the
      // router sends the user to onboarding by itself.
      if (notice.switchedTo != null) router.go('/home');
    });

    return MaterialApp.router(
      title: 'Expense & Budget Manager',
      scaffoldMessengerKey: _messengerKey,
      debugShowCheckedModeBanner: false,
      theme: AppTheme.light(seed),
      darkTheme: AppTheme.dark(seed),
      themeMode: settings.themeMode,
      routerConfig: router,
      localizationsDelegates: GlobalMaterialLocalizations.delegates,
      supportedLocales: const [Locale('en', 'IN'), Locale('en', 'US'), Locale('en')],
      scrollBehavior: const MaterialScrollBehavior().copyWith(
        dragDevices: {PointerDeviceKind.touch, PointerDeviceKind.mouse, PointerDeviceKind.trackpad},
      ),
      builder: (context, child) => _AppFrame(child: child ?? const SizedBox.shrink()),
    );
  }
}

/// Keeps the app at a comfortable reading width on large monitors while
/// filling phones and laptops edge to edge.
class _AppFrame extends StatelessWidget {
  const _AppFrame({required this.child});
  final Widget child;

  static const double maxWidth = 1280;

  @override
  Widget build(BuildContext context) {
    final width = MediaQuery.sizeOf(context).width;
    if (width <= maxWidth) return child;
    final scheme = Theme.of(context).colorScheme;
    return ColoredBox(
      color: scheme.surfaceContainerLow,
      child: Center(
        child: ClipRect(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: maxWidth),
            child: MediaQuery(
              data: MediaQuery.of(context).copyWith(size: Size(maxWidth, MediaQuery.sizeOf(context).height)),
              child: child,
            ),
          ),
        ),
      ),
    );
  }
}

/// Materialises due recurring transactions once the ledger is available.
final recurringProcessorProvider = Provider<void>((ref) {
  final ledger = ref.watch(ledgerProvider);
  final profile = ref.watch(userProfileProvider).value;
  final rules = ref.watch(recurringProvider).value;
  if (ledger == null || profile == null || rules == null || rules.isEmpty) return;
  final due = rules.where((r) => r.isActive && !r.nextDue.isAfter(DateTime.now())).toList();
  if (due.isEmpty) return;
  // Fire and forget; Firestore transactions guard against double-posting.
  ledger.processRecurring(due, profile).catchError((_) => 0);
});
