import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:material_ui/material_ui.dart';

import '../../core/constants/currencies.dart';
import '../../core/theme/app_theme.dart';
import '../../core/utils/extensions.dart';
import '../../core/widgets/widgets.dart';
import '../../services/auth_service.dart';
import '../auth/auth_providers.dart';
import '../household/household_providers.dart';

class ProfileScreen extends ConsumerStatefulWidget {
  const ProfileScreen({super.key});

  @override
  ConsumerState<ProfileScreen> createState() => _ProfileScreenState();
}

class _ProfileScreenState extends ConsumerState<ProfileScreen> {
  final _name = TextEditingController();
  bool _loaded = false;

  @override
  void dispose() {
    _name.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final profile = ref.watch(userProfileProvider).value;
    final household = ref.watch(activeHouseholdProvider).value;
    if (profile != null && !_loaded) {
      _name.text = profile.displayName;
      _loaded = true;
    }
    final member = household?.members[profile?.uid];
    return Scaffold(
      appBar: AppBar(title: const Text('Profile')),
      body: profile == null
          ? const LoadingState()
          : ListView(
              padding: const EdgeInsets.all(16),
              children: [
                Center(
                  child: MemberAvatar(initials: profile.initials, color: member?.color ?? 0xFF4F46E5, photoUrl: profile.photoUrl, size: 88),
                ),
                const SizedBox(height: 20),
                TextField(
                  controller: _name,
                  textCapitalization: TextCapitalization.words,
                  decoration: const InputDecoration(labelText: 'Display name', prefixIcon: Icon(Icons.person_outline_rounded)),
                ),
                const SizedBox(height: 12),
                TextField(
                  enabled: false,
                  controller: TextEditingController(text: profile.email),
                  decoration: const InputDecoration(labelText: 'Email', prefixIcon: Icon(Icons.mail_outline_rounded)),
                ),
                if (member != null) ...[
                  const SizedBox(height: 20),
                  Text('Your colour in ${household!.name}', style: context.text.titleSmall),
                  const SizedBox(height: 8),
                  ColorPicker(
                    selected: member.color,
                    onChanged: (c) => ref.read(userRepositoryProvider).updateMember(household.id, member.copyWith(color: c)),
                  ),
                ],
                const SizedBox(height: 24),
                FilledButton(
                  onPressed: () async {
                    final name = _name.text.trim();
                    if (name.length < 2) {
                      context.showSnack('Enter your name', error: true);
                      return;
                    }
                    await ref.read(authServiceProvider).updateDisplayName(name);
                    await ref.read(userRepositoryProvider).updateProfile(profile.uid, displayName: name);
                    if (household != null && member != null) {
                      await ref.read(userRepositoryProvider).updateMember(household.id, member.copyWith(name: name));
                    }
                    if (context.mounted) context.showSnack('Profile updated');
                  },
                  child: const Text('Save'),
                ),
              ],
            ),
    );
  }
}

class AppearanceScreen extends ConsumerWidget {
  const AppearanceScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final settings = ref.watch(appSettingsProvider);
    final notifier = ref.read(appSettingsProvider.notifier);
    return Scaffold(
      appBar: AppBar(title: const Text('Appearance')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Text('Theme', style: context.text.titleSmall),
          const SizedBox(height: 8),
          SegmentedButton<ThemeMode>(
            segments: const [
              ButtonSegment(value: ThemeMode.system, label: Text('System'), icon: Icon(Icons.brightness_auto_rounded)),
              ButtonSegment(value: ThemeMode.light, label: Text('Light'), icon: Icon(Icons.light_mode_rounded)),
              ButtonSegment(value: ThemeMode.dark, label: Text('Dark'), icon: Icon(Icons.dark_mode_rounded)),
            ],
            selected: {settings.themeMode},
            showSelectedIcon: false,
            onSelectionChanged: (s) => notifier.setThemeMode(s.first),
          ),
          const SizedBox(height: 24),
          Text('Accent colour', style: context.text.titleSmall),
          const SizedBox(height: 8),
          Wrap(
            spacing: 12,
            runSpacing: 12,
            children: [
              for (var i = 0; i < kAccentOptions.length; i++)
                GestureDetector(
                  onTap: () => notifier.setAccent(i),
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      AnimatedContainer(
                        duration: const Duration(milliseconds: 200),
                        width: 56,
                        height: 56,
                        decoration: BoxDecoration(
                          color: kAccentOptions[i].seed,
                          borderRadius: BorderRadius.circular(18),
                          border: Border.all(color: settings.accentIndex == i ? context.colors.onSurface : Colors.transparent, width: 3),
                        ),
                        child: settings.accentIndex == i ? const Icon(Icons.check_rounded, color: Colors.white) : null,
                      ),
                      const SizedBox(height: 4),
                      Text(kAccentOptions[i].name, style: context.text.labelSmall),
                    ],
                  ),
                ),
            ],
          ),
          const SizedBox(height: 24),
          SwitchListTile(
            contentPadding: EdgeInsets.zero,
            title: const Text('Mask amounts on the dashboard'),
            subtitle: const Text('Handy when sharing your screen'),
            value: settings.hideAmounts,
            onChanged: notifier.setHideAmounts,
          ),
        ],
      ),
    );
  }
}

class NotificationsScreen extends ConsumerWidget {
  const NotificationsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final settings = ref.watch(appSettingsProvider);
    final notifier = ref.read(appSettingsProvider.notifier);
    final appNotifier = ref.read(notifierProvider);
    return Scaffold(
      appBar: AppBar(title: const Text('Alerts')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          SwitchListTile(
            contentPadding: EdgeInsets.zero,
            title: const Text('Budget alerts'),
            subtitle: const Text('Warn when a new expense crosses a budget threshold or limit'),
            value: settings.budgetAlerts,
            onChanged: notifier.setBudgetAlerts,
          ),
          SwitchListTile(
            contentPadding: EdgeInsets.zero,
            title: const Text('Browser notifications'),
            subtitle: Text(
              appNotifier.isSupported
                  ? 'Also show a system notification for budget alerts'
                  : 'Not supported in this browser',
            ),
            value: settings.browserNotifications && appNotifier.isGranted,
            onChanged: !appNotifier.isSupported || !settings.budgetAlerts
                ? null
                : (v) async {
                    if (v) {
                      final granted = await appNotifier.requestPermission();
                      if (!granted && context.mounted) {
                        context.showSnack('Notifications are blocked for this site in your browser settings.', error: true);
                      }
                      await notifier.setBrowserNotifications(granted);
                    } else {
                      await notifier.setBrowserNotifications(false);
                    }
                  },
          ),
          const SizedBox(height: 12),
          AppCard(
            padding: const EdgeInsets.all(14),
            child: Text(
              'Recurring transactions post automatically when the app is open. Budget thresholds are set per budget '
              '(default 80%).',
              style: context.text.bodySmall?.copyWith(color: context.colors.onSurfaceVariant),
            ),
          ),
        ],
      ),
    );
  }
}

class HouseholdSettingsScreen extends ConsumerStatefulWidget {
  const HouseholdSettingsScreen({super.key});

  @override
  ConsumerState<HouseholdSettingsScreen> createState() => _HouseholdSettingsScreenState();
}

class _HouseholdSettingsScreenState extends ConsumerState<HouseholdSettingsScreen> {
  final _name = TextEditingController();
  bool _loaded = false;

  @override
  void dispose() {
    _name.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final household = ref.watch(activeHouseholdProvider).value;
    final role = ref.watch(myRoleProvider);
    if (household == null) return Scaffold(appBar: AppBar(), body: const LoadingState());
    if (!_loaded) {
      _name.text = household.name;
      _loaded = true;
    }
    final canEdit = role.canManageBudgets;
    final repo = ref.read(userRepositoryProvider);
    final info = currencyInfo(household.baseCurrency);
    return Scaffold(
      appBar: AppBar(title: const Text('Household settings')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          TextField(
            controller: _name,
            enabled: canEdit,
            textCapitalization: TextCapitalization.words,
            decoration: InputDecoration(
              labelText: 'Household name',
              prefixIcon: const Icon(Icons.home_rounded),
              suffixIcon: canEdit
                  ? IconButton(
                      icon: const Icon(Icons.check_rounded),
                      onPressed: () async {
                        await repo.updateHousehold(household.id, name: _name.text);
                        if (context.mounted) context.showSnack('Name updated');
                      },
                    )
                  : null,
            ),
          ),
          const SizedBox(height: 12),
          ListTile(
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14), side: BorderSide(color: context.colors.outlineVariant)),
            leading: const Icon(Icons.currency_exchange_rounded),
            title: const Text('Base currency'),
            subtitle: Text('${info.code} · ${info.name}'),
            trailing: canEdit ? const Icon(Icons.chevron_right_rounded) : null,
            onTap: !canEdit
                ? null
                : () async {
                    final picked = await showCurrencyPicker(context, selected: household.baseCurrency);
                    if (picked == null || picked == household.baseCurrency) return;
                    if (!context.mounted) return;
                    final ok = await confirmDialog(
                      context,
                      title: 'Change base currency to $picked?',
                      message: 'Existing amounts are not converted; they will simply be displayed in $picked. '
                          'Best done before you add transactions.',
                      confirmLabel: 'Change',
                      destructive: false,
                    );
                    if (ok) await repo.updateHousehold(household.id, baseCurrency: picked);
                  },
          ),
          const SizedBox(height: 12),
          ListTile(
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14), side: BorderSide(color: context.colors.outlineVariant)),
            leading: const Icon(Icons.event_repeat_rounded),
            title: const Text('Budget month starts on'),
            subtitle: Text(household.monthStartDay == 1 ? 'The 1st (calendar month)' : 'Day ${household.monthStartDay} (e.g. salary day)'),
            trailing: canEdit
                ? DropdownButton<int>(
                    value: household.monthStartDay,
                    underline: const SizedBox.shrink(),
                    items: [for (var d = 1; d <= 28; d++) DropdownMenuItem(value: d, child: Text('$d'))],
                    onChanged: (v) => v == null ? null : repo.updateHousehold(household.id, monthStartDay: v),
                  )
                : null,
          ),
          const SizedBox(height: 16),
          Consumer(
            builder: (context, ref, _) {
              final rates = ref.watch(ratesProvider);
              return AppCard(
                padding: const EdgeInsets.all(14),
                child: Row(
                  children: [
                    const Icon(Icons.sync_rounded),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Text(
                        rates.when(
                          loading: () => 'Fetching exchange rates…',
                          error: (_, _) => 'Exchange rates unavailable; foreign amounts use 1:1.',
                          data: (t) => t.isOffline
                              ? 'Exchange rates unavailable; foreign amounts use 1:1 until you are online.'
                              : 'Exchange rates (ECB via Frankfurter) updated ${t.fetchedAt == null ? '' : t.fetchedAt!.toLocal().toString().substring(0, 16)}.',
                        ),
                        style: context.text.bodySmall,
                      ),
                    ),
                    IconButton(
                      icon: const Icon(Icons.refresh_rounded),
                      onPressed: () => ref.invalidate(ratesProvider),
                    ),
                  ],
                ),
              );
            },
          ),
        ],
      ),
    );
  }
}

class SecurityScreen extends ConsumerWidget {
  const SecurityScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final settings = ref.watch(appSettingsProvider);
    final notifier = ref.read(appSettingsProvider.notifier);
    return Scaffold(
      appBar: AppBar(title: const Text('Privacy & security')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          SwitchListTile(
            contentPadding: EdgeInsets.zero,
            title: const Text('Mask amounts'),
            subtitle: const Text('Hide balances on the dashboard until you tap the eye icon'),
            value: settings.hideAmounts,
            onChanged: notifier.setHideAmounts,
          ),
          const Divider(height: 32),
          ListTile(
            contentPadding: EdgeInsets.zero,
            leading: const Icon(Icons.password_rounded),
            title: const Text('Change password'),
            subtitle: const Text('For email sign-in accounts'),
            onTap: () => _changePassword(context, ref),
          ),
          ListTile(
            contentPadding: EdgeInsets.zero,
            leading: const Icon(Icons.devices_rounded),
            title: const Text('Sign out'),
            subtitle: const Text('Ends this browser session'),
            onTap: () => ref.read(authServiceProvider).signOut(),
          ),
          const Divider(height: 32),
          ListTile(
            contentPadding: EdgeInsets.zero,
            leading: Icon(Icons.delete_forever_rounded, color: context.colors.error),
            title: Text('Delete my account', style: TextStyle(color: context.colors.error)),
            subtitle: const Text('Removes your sign-in. Household data you shared stays with your family.'),
            onTap: () async {
              final ok = await confirmDialog(
                context,
                title: 'Delete account?',
                message: 'This cannot be undone. You may be asked to sign in again first.',
                confirmLabel: 'Delete',
              );
              if (!ok) return;
              try {
                await ref.read(authServiceProvider).deleteAccount();
              } on AuthFailure catch (e) {
                if (context.mounted) context.showSnack(e.message, error: true);
              }
            },
          ),
        ],
      ),
    );
  }

  Future<void> _changePassword(BuildContext context, WidgetRef ref) async {
    final controller = TextEditingController();
    final pw = await showDialog<String>(
      context: context,
      builder: (dialog) => AlertDialog(
        title: const Text('New password'),
        content: TextField(controller: controller, obscureText: true, autofocus: true, decoration: const InputDecoration(labelText: 'At least 6 characters')),
        actions: [
          TextButton(onPressed: () => Navigator.pop(dialog), child: const Text('Cancel')),
          FilledButton(style: FilledButton.styleFrom(minimumSize: const Size(0, 44)), onPressed: () => Navigator.pop(dialog, controller.text), child: const Text('Update')),
        ],
      ),
    );
    if (pw == null || pw.length < 6) return;
    try {
      await ref.read(authServiceProvider).changePassword(pw);
      if (context.mounted) context.showSnack('Password updated');
    } on AuthFailure catch (e) {
      if (context.mounted) context.showSnack(e.message, error: true);
    }
  }
}

class AboutScreen extends StatelessWidget {
  const AboutScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('About')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Center(
            child: Container(
              width: 72,
              height: 72,
              decoration: BoxDecoration(
                gradient: LinearGradient(colors: [context.colors.primary, context.colors.tertiary]),
                borderRadius: BorderRadius.circular(20),
              ),
              child: const Icon(Icons.account_balance_wallet_rounded, color: Colors.white, size: 36),
            ),
          ),
          const SizedBox(height: 12),
          Center(child: Text('Expense & Budget Manager', style: context.text.titleLarge)),
          Center(child: Text('Version 1.0.0 · Web', style: context.text.bodySmall?.copyWith(color: context.colors.onSurfaceVariant))),
          const SizedBox(height: 24),
          AppCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('Your data', style: context.text.titleSmall),
                const SizedBox(height: 6),
                Text(
                  'Everything you enter is stored in your own Firebase project (Firestore for records, Storage for receipts) '
                  'and cached in this browser so the app works offline. Nothing is sent to third parties except anonymous '
                  'exchange-rate lookups to api.frankfurter.app.',
                  style: context.text.bodySmall?.copyWith(color: context.colors.onSurfaceVariant),
                ),
              ],
            ),
          ),
          const SizedBox(height: 12),
          AppCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('Keyboard shortcuts', style: context.text.titleSmall),
                const SizedBox(height: 6),
                const _Shortcut('N', 'New transaction'),
                const _Shortcut('/', 'Search'),
                const _Shortcut('1 – 5', 'Switch tabs'),
              ],
            ),
          ),
          const SizedBox(height: 12),
          ListTile(
            contentPadding: EdgeInsets.zero,
            leading: const Icon(Icons.description_outlined),
            title: const Text('Open-source licences'),
            onTap: () => showLicensePage(context: context, applicationName: 'Expense & Budget Manager', applicationVersion: '1.0.0'),
          ),
        ],
      ),
    );
  }
}

class _Shortcut extends StatelessWidget {
  const _Shortcut(this.key_, this.label);
  final String key_;
  final String label;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 6),
      child: Row(
        children: [
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
            decoration: BoxDecoration(
              color: context.colors.surfaceContainerHighest,
              borderRadius: BorderRadius.circular(6),
              border: Border.all(color: context.colors.outlineVariant),
            ),
            child: Text(key_, style: context.text.labelMedium?.copyWith(fontFamily: 'monospace')),
          ),
          const SizedBox(width: 10),
          Text(label, style: context.text.bodySmall),
        ],
      ),
    );
  }
}

