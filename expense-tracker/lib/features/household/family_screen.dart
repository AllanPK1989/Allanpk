import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:material_ui/material_ui.dart';
import 'package:share_plus/share_plus.dart';

import '../../core/utils/date_utils.dart';
import '../../core/utils/extensions.dart';
import '../../core/widgets/widgets.dart';
import '../../models/models.dart';
import '../../router.dart';
import '../auth/auth_providers.dart';
import 'household_providers.dart';

/// Household members, invite code, switching and leaving.
class FamilyScreen extends ConsumerWidget {
  const FamilyScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final household = ref.watch(activeHouseholdProvider).value;
    final profile = ref.watch(userProfileProvider).value;
    final households = ref.watch(householdsProvider).value ?? const [];
    final role = ref.watch(myRoleProvider);
    if (household == null || profile == null) {
      return Scaffold(appBar: AppBar(title: const Text('Family')), body: const LoadingState());
    }
    final code = _pretty(household.inviteCode);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Family'),
        actions: [
          IconButton(
            tooltip: 'Activity',
            icon: const Icon(Icons.history_rounded),
            onPressed: () => context.push('/family/activity'),
          ),
          IconButton(
            tooltip: 'Household settings',
            icon: const Icon(Icons.settings_outlined),
            onPressed: () => context.push('/settings/household'),
          ),
          const SizedBox(width: 4),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(16, 4, 16, 40),
        children: [
          AppCard(
            padding: const EdgeInsets.all(20),
            gradient: LinearGradient(
              colors: [context.colors.primaryContainer, context.colors.tertiaryContainer],
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(household.name, style: context.text.headlineSmall),
                Text(
                  '${household.memberIds.length} ${household.memberIds.length == 1 ? 'member' : 'members'} · ${household.baseCurrency} · since ${AppDates.monthYear.format(household.createdAt)}',
                  style: context.text.bodyMedium?.copyWith(color: context.colors.onSurfaceVariant),
                ),
                const SizedBox(height: 18),
                Text('Invite code', style: context.text.labelMedium?.copyWith(color: context.colors.onSurfaceVariant)),
                const SizedBox(height: 4),
                Row(
                  children: [
                    Expanded(
                      child: SelectableText(code, style: context.text.headlineMedium?.copyWith(letterSpacing: 4)),
                    ),
                    IconButton.filledTonal(
                      tooltip: 'Copy',
                      icon: const Icon(Icons.copy_rounded),
                      onPressed: () async {
                        await Clipboard.setData(ClipboardData(text: household.inviteCode));
                        if (context.mounted) context.showSnack('Invite code copied');
                      },
                    ),
                    const SizedBox(width: 6),
                    IconButton.filledTonal(
                      tooltip: 'Share',
                      icon: const Icon(Icons.share_rounded),
                      onPressed: () => SharePlus.instance.share(
                        ShareParams(
                          text: 'Join our household "${household.name}" in Expense & Budget Manager. '
                              'Open the app, choose "Join a family" and enter the code ${household.inviteCode}.',
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 6),
                Text(
                  'Anyone with this code can join and see shared accounts, budgets and transactions.',
                  style: context.text.bodySmall?.copyWith(color: context.colors.onSurfaceVariant),
                ),
                if (role.canManageMembers)
                  Align(
                    alignment: Alignment.centerRight,
                    child: TextButton.icon(
                      onPressed: () async {
                        final ok = await confirmDialog(
                          context,
                          title: 'Regenerate code?',
                          message: 'The old code stops working immediately. Existing members are unaffected.',
                          confirmLabel: 'Regenerate',
                          destructive: false,
                        );
                        if (!ok) return;
                        await ref.read(userRepositoryProvider).regenerateInviteCode(household);
                      },
                      icon: const Icon(Icons.refresh_rounded, size: 18),
                      label: const Text('Regenerate'),
                    ),
                  ),
              ],
            ),
          ),
          const SectionHeader(title: 'Members'),
          AppCard(
            padding: const EdgeInsets.symmetric(vertical: 4),
            child: Column(
              children: [
                for (final m in household.sortedMembers)
                  ListTile(
                    leading: MemberAvatar(initials: m.initials, color: m.color, photoUrl: m.photoUrl, size: 42),
                    title: Row(
                      children: [
                        Text(m.name, style: context.text.titleSmall),
                        if (m.uid == profile.uid) ...[
                          const SizedBox(width: 6),
                          Text('(you)', style: context.text.bodySmall?.copyWith(color: context.colors.onSurfaceVariant)),
                        ],
                      ],
                    ),
                    subtitle: Text('${m.role.label} · joined ${AppDates.dayMonthYear.format(m.joinedAt)}'),
                    trailing: role.canManageMembers && m.uid != profile.uid
                        ? PopupMenuButton<String>(
                            onSelected: (v) => _memberAction(context, ref, household, profile, m, v),
                            itemBuilder: (_) => [
                              const PopupMenuItem(value: 'adult', child: Text('Make adult')),
                              const PopupMenuItem(value: 'child', child: Text('Make child')),
                              const PopupMenuItem(value: 'remove', child: Text('Remove from household')),
                            ],
                          )
                        : null,
                  ),
              ],
            ),
          ),
          const SizedBox(height: 8),
          AppCard(
            padding: const EdgeInsets.all(14),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('Roles', style: context.text.titleSmall),
                const SizedBox(height: 6),
                for (final r in MemberRole.values)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 4),
                    child: Text.rich(
                      TextSpan(
                        children: [
                          TextSpan(text: '${r.label}: ', style: const TextStyle(fontWeight: FontWeight.w700)),
                          TextSpan(text: r.description),
                        ],
                      ),
                      style: context.text.bodySmall?.copyWith(color: context.colors.onSurfaceVariant),
                    ),
                  ),
              ],
            ),
          ),
          if (households.length > 1) ...[
            const SectionHeader(title: 'Switch household'),
            AppCard(
              padding: const EdgeInsets.symmetric(vertical: 4),
              child: Column(
                children: [
                  for (final h in households)
                    ListTile(
                      leading: IconBadge(iconKey: 'home', color: h.id == household.id ? context.colors.primary.argb : 0xFF78909C, size: 38),
                      title: Text(h.name),
                      subtitle: Text('${h.memberIds.length} members · ${h.baseCurrency}'),
                      trailing: h.id == household.id ? const Icon(Icons.check_circle_rounded) : null,
                      onTap: h.id == household.id
                          ? null
                          : () => ref.read(userRepositoryProvider).switchHousehold(profile.uid, h.id),
                    ),
                ],
              ),
            ),
          ],
          const SizedBox(height: 16),
          OutlinedButton.icon(
            onPressed: () => context.push('/family/join'),
            icon: const Icon(Icons.group_add_outlined),
            label: const Text('Join another household with a code'),
          ),
          const SizedBox(height: 10),
          OutlinedButton.icon(
            onPressed: () => _createAnother(context, ref, profile),
            icon: const Icon(Icons.add_home_outlined),
            label: const Text('Create a new household'),
          ),
          if (household.ownerId != profile.uid) ...[
            const SizedBox(height: 10),
            TextButton.icon(
              style: TextButton.styleFrom(foregroundColor: context.colors.error),
              onPressed: () => _leave(context, ref, household, profile, households),
              icon: const Icon(Icons.logout_rounded),
              label: const Text('Leave this household'),
            ),
          ],
        ],
      ),
    );
  }

  static String _pretty(String code) => code.length == 8 ? '${code.substring(0, 4)}-${code.substring(4)}' : code;

  Future<void> _memberAction(
    BuildContext context,
    WidgetRef ref,
    Household household,
    UserProfile actor,
    HouseholdMember m,
    String action,
  ) async {
    final repo = ref.read(userRepositoryProvider);
    switch (action) {
      case 'adult':
        await repo.updateMember(household.id, m.copyWith(role: MemberRole.adult));
      case 'child':
        await repo.updateMember(household.id, m.copyWith(role: MemberRole.child));
      case 'remove':
        final ok = await confirmDialog(
          context,
          title: 'Remove ${m.name}?',
          message: 'They lose access to this household. Their transactions stay in the ledger.',
          confirmLabel: 'Remove',
        );
        if (!ok) return;
        await repo.removeMember(household: household, memberId: m.uid, actor: actor);
    }
  }

  Future<void> _leave(
    BuildContext context,
    WidgetRef ref,
    Household household,
    UserProfile profile,
    List<Household> households,
  ) async {
    final ok = await confirmDialog(
      context,
      title: 'Leave ${household.name}?',
      message: 'You will need a new invite code to rejoin.',
      confirmLabel: 'Leave',
    );
    if (!ok) return;
    final other = households.where((h) => h.id != household.id).firstOrNull;
    await ref
        .read(userRepositoryProvider)
        .leaveHousehold(household: household, profile: profile, nextActiveId: other?.id);
    if (context.mounted && context.canPop()) context.popOrHome();
  }

  Future<void> _createAnother(BuildContext context, WidgetRef ref, UserProfile profile) async {
    final controller = TextEditingController();
    final name = await showDialog<String>(
      context: context,
      builder: (dialog) => AlertDialog(
        title: const Text('New household'),
        content: TextField(
          controller: controller,
          autofocus: true,
          textCapitalization: TextCapitalization.words,
          decoration: const InputDecoration(labelText: 'Name'),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(dialog), child: const Text('Cancel')),
          FilledButton(
            style: FilledButton.styleFrom(minimumSize: const Size(0, 44)),
            onPressed: () => Navigator.pop(dialog, controller.text),
            child: const Text('Create'),
          ),
        ],
      ),
    );
    if (name == null || name.trim().isEmpty) return;
    final currency = ref.read(baseCurrencyProvider);
    await ref.read(userRepositoryProvider).createHousehold(profile: profile, name: name, currency: currency);
    if (context.mounted) context.showSnack('Switched to $name');
  }
}
