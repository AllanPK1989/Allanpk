import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:material_ui/material_ui.dart';

import '../../core/utils/extensions.dart';
import '../../core/widgets/widgets.dart';
import '../auth/auth_providers.dart';
import '../household/household_providers.dart';

/// Hub for everything that is not a primary tab.
class MoreScreen extends ConsumerWidget {
  const MoreScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final profile = ref.watch(userProfileProvider).value;
    final household = ref.watch(activeHouseholdProvider).value;
    final goals = ref.watch(goalsProvider).value ?? const [];
    final recurring = ref.watch(recurringProvider).value ?? const [];
    final accounts = ref.watch(accountsProvider).value ?? const [];

    Widget tile(IconData icon, String title, String subtitle, String route, {Color? color}) => ListTile(
          leading: IconBadge(iconKey: null, icon: icon, color: (color ?? context.colors.primary).argb, size: 40),
          title: Text(title, style: context.text.titleSmall),
          subtitle: Text(subtitle, maxLines: 1, overflow: TextOverflow.ellipsis),
          trailing: const Icon(Icons.chevron_right_rounded),
          onTap: () => context.push(route),
        );

    return Scaffold(
      appBar: AppBar(title: const Text('More')),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(16, 4, 16, 40),
        children: [
          AppCard(
            onTap: () => context.push('/settings/profile'),
            child: Row(
              children: [
                MemberAvatar(
                  initials: profile?.initials ?? '?',
                  color: household?.members[profile?.uid]?.color ?? 0xFF4F46E5,
                  photoUrl: profile?.photoUrl,
                  size: 52,
                ),
                const SizedBox(width: 14),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(profile?.displayName ?? '', style: context.text.titleMedium),
                      Text(profile?.email ?? '', style: context.text.bodySmall?.copyWith(color: context.colors.onSurfaceVariant)),
                      if (household != null)
                        Text('${household.name} · ${ref.watch(myRoleProvider).label}', style: context.text.labelSmall?.copyWith(color: context.colors.primary)),
                    ],
                  ),
                ),
                const Icon(Icons.chevron_right_rounded),
              ],
            ),
          ),
          const SectionHeader(title: 'Manage'),
          AppCard(
            padding: const EdgeInsets.symmetric(vertical: 4),
            child: Column(
              children: [
                tile(Icons.account_balance_wallet_outlined, 'Accounts', '${accounts.where((a) => !a.isArchived).length} active', '/accounts'),
                tile(Icons.category_outlined, 'Categories', 'Icons, colours, sub-categories', '/categories', color: const Color(0xFFF4511E)),
                tile(Icons.repeat_rounded, 'Recurring', '${recurring.where((r) => r.isActive).length} active rules', '/recurring', color: const Color(0xFF8E24AA)),
                tile(Icons.savings_outlined, 'Savings goals', '${goals.where((g) => !g.isCompleted).length} in progress', '/goals', color: const Color(0xFF00897B)),
              ],
            ),
          ),
          const SectionHeader(title: 'Family'),
          AppCard(
            padding: const EdgeInsets.symmetric(vertical: 4),
            child: Column(
              children: [
                tile(Icons.family_restroom_rounded, 'Household & members', household == null ? '' : '${household.memberIds.length} members · invite code', '/family', color: const Color(0xFF039BE5)),
                tile(Icons.history_rounded, 'Activity feed', 'Who added what, and when', '/family/activity', color: const Color(0xFF546E7A)),
              ],
            ),
          ),
          const SectionHeader(title: 'Reports & data'),
          AppCard(
            padding: const EdgeInsets.symmetric(vertical: 4),
            child: Column(
              children: [
                tile(Icons.picture_as_pdf_outlined, 'Reports', 'PDF and Excel exports', '/reports', color: const Color(0xFFE53935)),
                tile(Icons.upload_file_outlined, 'Import CSV', 'Bring in bank statements or old data', '/reports/import', color: const Color(0xFF43A047)),
              ],
            ),
          ),
          const SectionHeader(title: 'Settings'),
          AppCard(
            padding: const EdgeInsets.symmetric(vertical: 4),
            child: Column(
              children: [
                tile(Icons.palette_outlined, 'Appearance', 'Theme and accent colour', '/settings/appearance', color: const Color(0xFF7C3AED)),
                tile(Icons.notifications_outlined, 'Alerts', 'Budget warnings and browser notifications', '/settings/notifications', color: const Color(0xFFF59E0B)),
                tile(Icons.home_work_outlined, 'Household settings', 'Name, currency, month start day', '/settings/household', color: const Color(0xFF0D9488)),
                tile(Icons.shield_outlined, 'Privacy & security', 'Amount masking, password, account', '/settings/security', color: const Color(0xFF475569)),
                tile(Icons.info_outline_rounded, 'About', 'Version, licences, data handling', '/settings/about', color: const Color(0xFF64748B)),
              ],
            ),
          ),
          const SizedBox(height: 16),
          TextButton.icon(
            style: TextButton.styleFrom(foregroundColor: context.colors.error),
            onPressed: () async {
              final ok = await confirmDialog(context, title: 'Sign out?', message: 'Your data stays safely in the cloud.', confirmLabel: 'Sign out', destructive: false);
              if (ok) await ref.read(authServiceProvider).signOut();
            },
            icon: const Icon(Icons.logout_rounded),
            label: const Text('Sign out'),
          ),
        ],
      ),
    );
  }
}
