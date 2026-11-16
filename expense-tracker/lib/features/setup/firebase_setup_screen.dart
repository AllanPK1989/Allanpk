import 'package:material_ui/material_ui.dart';

import '../../core/theme/app_theme.dart';

/// Shown when firebase_options.dart still holds placeholder values.
class FirebaseSetupApp extends StatelessWidget {
  const FirebaseSetupApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Expense & Budget Manager',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.light(kAccentOptions.first.seed),
      darkTheme: AppTheme.dark(kAccentOptions.first.seed),
      home: const _SetupScreen(),
    );
  }
}

class _SetupScreen extends StatelessWidget {
  const _SetupScreen();

  @override
  Widget build(BuildContext context) {
    final text = Theme.of(context).textTheme;
    final scheme = Theme.of(context).colorScheme;
    return Scaffold(
      body: SafeArea(
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 520),
            child: ListView(
              padding: const EdgeInsets.all(28),
              shrinkWrap: true,
              children: [
                Icon(Icons.local_fire_department_rounded, size: 56, color: scheme.primary),
                const SizedBox(height: 16),
                Text('Connect Firebase to get started', style: text.headlineSmall),
                const SizedBox(height: 12),
                Text(
                  'This build is not linked to a Firebase project yet. Run the steps below '
                  'once, then rebuild the app.',
                  style: text.bodyMedium?.copyWith(color: scheme.onSurfaceVariant),
                ),
                const SizedBox(height: 20),
                const _Step(1, 'Install the CLI tools', 'npm install -g firebase-tools\ndart pub global activate flutterfire_cli'),
                const _Step(2, 'Sign in and link the project', 'firebase login\nflutterfire configure'),
                const _Step(3, 'Enable Auth providers', 'Firebase console → Authentication → Email/Password, Google, Apple'),
                const _Step(4, 'Deploy rules and indexes', 'firebase deploy --only firestore,storage'),
                const SizedBox(height: 12),
                Text(
                  'Full instructions live in SETUP.md in the project root.',
                  style: text.bodySmall?.copyWith(color: scheme.onSurfaceVariant),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _Step extends StatelessWidget {
  const _Step(this.n, this.title, this.command);
  final int n;
  final String title;
  final String command;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final text = Theme.of(context).textTheme;
    return Padding(
      padding: const EdgeInsets.only(bottom: 14),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          CircleAvatar(
            radius: 14,
            backgroundColor: scheme.primaryContainer,
            child: Text('$n', style: text.labelLarge),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(title, style: text.titleSmall),
                const SizedBox(height: 6),
                Container(
                  width: double.infinity,
                  padding: const EdgeInsets.all(10),
                  decoration: BoxDecoration(
                    color: scheme.surfaceContainerHighest.withValues(alpha: 0.6),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: Text(
                    command,
                    style: text.bodySmall?.copyWith(fontFamily: 'monospace'),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
