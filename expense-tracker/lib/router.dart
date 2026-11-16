import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:material_ui/material_ui.dart';

import 'features/accounts/account_detail_screen.dart';
import 'features/accounts/account_editor_screen.dart';
import 'features/accounts/accounts_screen.dart';
import 'features/analytics/insights_screen.dart';
import 'features/auth/auth_providers.dart';
import 'features/auth/auth_screens.dart';
import 'features/budgets/budget_detail_screen.dart';
import 'features/budgets/budget_editor_screen.dart';
import 'features/budgets/budgets_screen.dart';
import 'features/categories/categories_screen.dart';
import 'features/categories/category_editor_screen.dart';
import 'features/goals/goal_editor_screen.dart';
import 'features/goals/goals_screen.dart';
import 'features/home/dashboard_screen.dart';
import 'features/home/home_shell.dart';
import 'features/household/activity_screen.dart';
import 'features/household/family_screen.dart';
import 'features/household/household_providers.dart';
import 'features/onboarding/onboarding_screen.dart';
import 'features/recurring/recurring_editor_screen.dart';
import 'features/recurring/recurring_screen.dart';
import 'features/reports/import_csv_screen.dart';
import 'features/reports/reports_screen.dart';
import 'features/settings/more_screen.dart';
import 'features/settings/settings_screens.dart';
import 'features/transactions/search_screen.dart';
import 'features/transactions/transaction_detail_screen.dart';
import 'features/transactions/transaction_editor_screen.dart';
import 'features/transactions/transactions_screen.dart';

/// Pings GoRouter whenever auth / profile / lock state changes.
class _RouterRefresh extends ChangeNotifier {
  void ping() => notifyListeners();
}

final _rootKey = GlobalKey<NavigatorState>(debugLabel: 'root');

final routerProvider = Provider<GoRouter>((ref) {
  final refresh = _RouterRefresh();
  ref.listen(authStateProvider, (_, _) => refresh.ping());
  ref.listen(userProfileProvider, (_, _) => refresh.ping());
  ref.onDispose(refresh.dispose);

  return GoRouter(
    navigatorKey: _rootKey,
    initialLocation: '/splash',
    refreshListenable: refresh,
    redirect: (context, state) {
      final auth = ref.read(authStateProvider);
      final profile = ref.read(userProfileProvider);
      final path = state.uri.path;

      const authPaths = {'/sign-in', '/sign-up', '/forgot-password'};
      final onAuth = authPaths.contains(path);
      final onSplash = path == '/splash';
      final onOnboarding = path.startsWith('/onboarding');

      if (auth.isLoading) return onSplash ? null : '/splash';
      final user = auth.value;
      if (user == null) return onAuth ? null : '/sign-in';

      if (profile.isLoading && !profile.hasValue) return onSplash ? null : '/splash';
      final p = profile.value;
      if (p == null || p.activeHouseholdId == null) {
        return onOnboarding ? null : '/onboarding';
      }
      if (onAuth || onSplash || onOnboarding) return '/home';
      return null;
    },
    routes: [
      GoRoute(path: '/splash', builder: (_, _) => const SplashScreen()),
      GoRoute(path: '/sign-in', builder: (_, _) => const SignInScreen()),
      GoRoute(path: '/sign-up', builder: (_, _) => const SignUpScreen()),
      GoRoute(path: '/forgot-password', builder: (_, _) => const ForgotPasswordScreen()),
      GoRoute(
        path: '/onboarding',
        builder: (_, _) => const OnboardingScreen(),
        routes: [
          GoRoute(path: 'join', builder: (_, _) => const JoinHouseholdScreen()),
        ],
      ),
      StatefulShellRoute.indexedStack(
        builder: (context, state, shell) => HomeShell(shell: shell),
        branches: [
          StatefulShellBranch(
            routes: [GoRoute(path: '/home', builder: (_, _) => const DashboardScreen())],
          ),
          StatefulShellBranch(
            routes: [GoRoute(path: '/transactions', builder: (_, _) => const TransactionsScreen())],
          ),
          StatefulShellBranch(
            routes: [GoRoute(path: '/budgets', builder: (_, _) => const BudgetsScreen())],
          ),
          StatefulShellBranch(
            routes: [GoRoute(path: '/insights', builder: (_, _) => const InsightsScreen())],
          ),
          StatefulShellBranch(
            routes: [GoRoute(path: '/more', builder: (_, _) => const MoreScreen())],
          ),
        ],
      ),
      // Full-screen routes pushed above the shell.
      GoRoute(
        path: '/transactions/new',
        parentNavigatorKey: _rootKey,
        builder: (_, state) => TransactionEditorScreen(
          initialType: state.uri.queryParameters['type'],
          duplicateOf: state.extra is String ? state.extra as String? : null,
        ),
      ),
      GoRoute(
        path: '/transactions/:id',
        parentNavigatorKey: _rootKey,
        builder: (_, state) => TransactionDetailScreen(id: state.pathParameters['id']!),
        routes: [
          GoRoute(
            path: 'edit',
            parentNavigatorKey: _rootKey,
            builder: (_, state) => TransactionEditorScreen(editId: state.pathParameters['id']),
          ),
        ],
      ),
      GoRoute(path: '/search', parentNavigatorKey: _rootKey, builder: (_, _) => const SearchScreen()),
      GoRoute(
        path: '/budgets/new',
        parentNavigatorKey: _rootKey,
        builder: (_, _) => const BudgetEditorScreen(),
      ),
      GoRoute(
        path: '/budgets/:id',
        parentNavigatorKey: _rootKey,
        builder: (_, state) => BudgetDetailScreen(id: state.pathParameters['id']!),
        routes: [
          GoRoute(
            path: 'edit',
            parentNavigatorKey: _rootKey,
            builder: (_, state) => BudgetEditorScreen(editId: state.pathParameters['id']),
          ),
        ],
      ),
      GoRoute(
        path: '/goals',
        parentNavigatorKey: _rootKey,
        builder: (_, _) => const GoalsScreen(),
        routes: [
          GoRoute(path: 'new', parentNavigatorKey: _rootKey, builder: (_, _) => const GoalEditorScreen()),
          GoRoute(
            path: ':id/edit',
            parentNavigatorKey: _rootKey,
            builder: (_, state) => GoalEditorScreen(editId: state.pathParameters['id']),
          ),
        ],
      ),
      GoRoute(
        path: '/accounts',
        parentNavigatorKey: _rootKey,
        builder: (_, _) => const AccountsScreen(),
        routes: [
          GoRoute(path: 'new', parentNavigatorKey: _rootKey, builder: (_, _) => const AccountEditorScreen()),
          GoRoute(
            path: ':id',
            parentNavigatorKey: _rootKey,
            builder: (_, state) => AccountDetailScreen(id: state.pathParameters['id']!),
            routes: [
              GoRoute(
                path: 'edit',
                parentNavigatorKey: _rootKey,
                builder: (_, state) => AccountEditorScreen(editId: state.pathParameters['id']),
              ),
            ],
          ),
        ],
      ),
      GoRoute(
        path: '/categories',
        parentNavigatorKey: _rootKey,
        builder: (_, _) => const CategoriesScreen(),
        routes: [
          GoRoute(
            path: 'new',
            parentNavigatorKey: _rootKey,
            builder: (_, state) => CategoryEditorScreen(initialKind: state.uri.queryParameters['kind']),
          ),
          GoRoute(
            path: ':id/edit',
            parentNavigatorKey: _rootKey,
            builder: (_, state) => CategoryEditorScreen(editId: state.pathParameters['id']),
          ),
        ],
      ),
      GoRoute(
        path: '/recurring',
        parentNavigatorKey: _rootKey,
        builder: (_, _) => const RecurringScreen(),
        routes: [
          GoRoute(path: 'new', parentNavigatorKey: _rootKey, builder: (_, _) => const RecurringEditorScreen()),
          GoRoute(
            path: ':id/edit',
            parentNavigatorKey: _rootKey,
            builder: (_, state) => RecurringEditorScreen(editId: state.pathParameters['id']),
          ),
        ],
      ),
      GoRoute(
        path: '/family',
        parentNavigatorKey: _rootKey,
        builder: (_, _) => const FamilyScreen(),
        routes: [
          GoRoute(path: 'join', parentNavigatorKey: _rootKey, builder: (_, _) => const JoinHouseholdScreen()),
          GoRoute(path: 'activity', parentNavigatorKey: _rootKey, builder: (_, _) => const ActivityScreen()),
        ],
      ),
      GoRoute(
        path: '/reports',
        parentNavigatorKey: _rootKey,
        builder: (_, _) => const ReportsScreen(),
        routes: [
          GoRoute(path: 'import', parentNavigatorKey: _rootKey, builder: (_, _) => const ImportCsvScreen()),
        ],
      ),
      GoRoute(
        path: '/settings/profile',
        parentNavigatorKey: _rootKey,
        builder: (_, _) => const ProfileScreen(),
      ),
      GoRoute(
        path: '/settings/appearance',
        parentNavigatorKey: _rootKey,
        builder: (_, _) => const AppearanceScreen(),
      ),
      GoRoute(
        path: '/settings/security',
        parentNavigatorKey: _rootKey,
        builder: (_, _) => const SecurityScreen(),
      ),
      GoRoute(
        path: '/settings/notifications',
        parentNavigatorKey: _rootKey,
        builder: (_, _) => const NotificationsScreen(),
      ),
      GoRoute(
        path: '/settings/household',
        parentNavigatorKey: _rootKey,
        builder: (_, _) => const HouseholdSettingsScreen(),
      ),
      GoRoute(
        path: '/settings/about',
        parentNavigatorKey: _rootKey,
        builder: (_, _) => const AboutScreen(),
      ),
    ],
  );
});

/// Small helper so screens can push without importing go_router everywhere.
extension NavX on BuildContext {
  void goTo(String location, {Object? extra}) => GoRouter.of(this).push(location, extra: extra);
  void goReplace(String location) => GoRouter.of(this).go(location);
  bool get canPopRoute => GoRouter.of(this).canPop();
  void popRoute() => GoRouter.of(this).pop();
}
