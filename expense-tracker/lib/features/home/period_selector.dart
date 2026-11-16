import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:material_ui/material_ui.dart';

import '../../core/utils/date_utils.dart';
import '../../core/utils/extensions.dart';
import '../household/household_providers.dart';

/// Month navigator with a quick-range menu.
class PeriodSelector extends ConsumerWidget {
  const PeriodSelector({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final range = ref.watch(selectedPeriodProvider);
    final notifier = ref.read(selectedPeriodProvider.notifier);
    final scheme = context.colors;
    return Row(
      children: [
        IconButton.filledTonal(
          onPressed: notifier.previousMonth,
          icon: const Icon(Icons.chevron_left_rounded),
          visualDensity: VisualDensity.compact,
        ),
        Expanded(
          child: InkWell(
            borderRadius: BorderRadius.circular(12),
            onTap: () => _showRangeMenu(context, ref),
            child: Padding(
              padding: const EdgeInsets.symmetric(vertical: 8),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(Icons.calendar_month_rounded, size: 18, color: scheme.primary),
                  const SizedBox(width: 6),
                  Flexible(
                    child: Text(
                      range.label(),
                      style: context.text.titleSmall,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                  Icon(Icons.arrow_drop_down_rounded, color: scheme.onSurfaceVariant),
                ],
              ),
            ),
          ),
        ),
        IconButton.filledTonal(
          onPressed: notifier.nextMonth,
          icon: const Icon(Icons.chevron_right_rounded),
          visualDensity: VisualDensity.compact,
        ),
      ],
    );
  }

  Future<void> _showRangeMenu(BuildContext context, WidgetRef ref) async {
    final notifier = ref.read(selectedPeriodProvider.notifier);
    final now = DateTime.now();
    await showModalBottomSheet<void>(
      context: context,
      builder: (sheet) => SafeArea(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            ListTile(
              leading: const Icon(Icons.today_rounded),
              title: const Text('This month'),
              onTap: () {
                notifier.thisMonth();
                Navigator.pop(sheet);
              },
            ),
            ListTile(
              leading: const Icon(Icons.history_rounded),
              title: const Text('Last 30 days'),
              onTap: () {
                notifier.set(DateRange.lastDays(30));
                Navigator.pop(sheet);
              },
            ),
            ListTile(
              leading: const Icon(Icons.view_week_rounded),
              title: const Text('This week'),
              onTap: () {
                notifier.set(DateRange.week(now));
                Navigator.pop(sheet);
              },
            ),
            ListTile(
              leading: const Icon(Icons.calendar_view_month_rounded),
              title: const Text('This quarter'),
              onTap: () {
                notifier.set(DateRange.quarter(now));
                Navigator.pop(sheet);
              },
            ),
            ListTile(
              leading: const Icon(Icons.event_note_rounded),
              title: const Text('This year'),
              onTap: () {
                notifier.set(DateRange.year(now));
                Navigator.pop(sheet);
              },
            ),
            ListTile(
              leading: const Icon(Icons.date_range_rounded),
              title: const Text('Custom range…'),
              onTap: () async {
                Navigator.pop(sheet);
                final picked = await showDateRangePicker(
                  context: context,
                  firstDate: DateTime(2000),
                  lastDate: DateTime(2100),
                  initialDateRange: DateTimeRange(
                    start: ref.read(selectedPeriodProvider).start,
                    end: ref.read(selectedPeriodProvider).end,
                  ),
                );
                if (picked != null) notifier.set(DateRange.custom(picked.start, picked.end));
              },
            ),
            const SizedBox(height: 8),
          ],
        ),
      ),
    );
  }
}

