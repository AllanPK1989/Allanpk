import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:material_ui/material_ui.dart';

import '../../core/constants/app_icons.dart';
import '../../core/utils/date_utils.dart';
import '../../core/utils/extensions.dart';
import '../../core/widgets/widgets.dart';
import '../../models/models.dart';
import 'household_providers.dart';

/// Chronological feed of what every member did.
class ActivityScreen extends ConsumerWidget {
  const ActivityScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final activity = ref.watch(activityProvider);
    final household = ref.watch(activeHouseholdProvider).value;
    return Scaffold(
      appBar: AppBar(title: const Text('Family activity')),
      body: activity.when(
        loading: () => const LoadingState(),
        error: (e, _) => ErrorState(error: e),
        data: (entries) {
          if (entries.isEmpty) {
            return const EmptyState(
              icon: Icons.history_rounded,
              title: 'No activity yet',
              message: 'Shared transactions, budgets and goals show up here as your family adds them.',
            );
          }
          final groups = <DateTime, List<ActivityEntry>>{};
          for (final e in entries) {
            groups.putIfAbsent(AppDates.dateOnly(e.at), () => []).add(e);
          }
          return ListView(
            padding: const EdgeInsets.fromLTRB(16, 4, 16, 40),
            children: [
              for (final day in groups.keys) ...[
                Padding(
                  padding: const EdgeInsets.fromLTRB(4, 14, 4, 6),
                  child: Text(AppDates.relativeDay(day), style: context.text.labelLarge?.copyWith(color: context.colors.onSurfaceVariant)),
                ),
                AppCard(
                  padding: const EdgeInsets.symmetric(vertical: 4),
                  child: Column(
                    children: [
                      for (final e in groups[day]!)
                        ListTile(
                          leading: MemberAvatar(
                            initials: e.actorName.isEmpty ? '?' : e.actorName.trim().split(' ').map((p) => p[0]).take(2).join().toUpperCase(),
                            color: household?.members[e.actorId]?.color ?? kPalette[15],
                            photoUrl: household?.members[e.actorId]?.photoUrl,
                          ),
                          title: Text(e.summary, style: context.text.bodyMedium),
                          subtitle: Text(
                            '${AppDates.time.format(e.at)} · ${e.entityType}',
                            style: context.text.labelSmall?.copyWith(color: context.colors.onSurfaceVariant),
                          ),
                          trailing: Icon(
                            switch (e.action) {
                              ActivityAction.created => Icons.add_circle_outline_rounded,
                              ActivityAction.updated => Icons.edit_outlined,
                              ActivityAction.deleted => Icons.remove_circle_outline_rounded,
                              ActivityAction.joined => Icons.person_add_alt_1_outlined,
                              ActivityAction.left => Icons.person_remove_alt_1_outlined,
                            },
                            size: 18,
                            color: context.colors.onSurfaceVariant,
                          ),
                        ),
                    ],
                  ),
                ),
              ],
            ],
          );
        },
      ),
    );
  }
}
