import 'package:intl/intl.dart';

/// Inclusive date range helper used by analytics, budgets and reports.
class DateRange {
  const DateRange(this.start, this.end);

  final DateTime start;
  final DateTime end;

  factory DateRange.month(DateTime anchor, {int startDay = 1}) {
    if (startDay <= 1) {
      final start = DateTime(anchor.year, anchor.month, 1);
      final end = DateTime(anchor.year, anchor.month + 1, 0, 23, 59, 59, 999);
      return DateRange(start, end);
    }
    // Custom month start, e.g. salary day on the 25th.
    DateTime start;
    if (anchor.day >= startDay) {
      start = DateTime(anchor.year, anchor.month, startDay);
    } else {
      start = DateTime(anchor.year, anchor.month - 1, startDay);
    }
    final next = DateTime(start.year, start.month + 1, startDay);
    return DateRange(start, next.subtract(const Duration(milliseconds: 1)));
  }

  factory DateRange.week(DateTime anchor) {
    final day = DateTime(anchor.year, anchor.month, anchor.day);
    final start = day.subtract(Duration(days: day.weekday - 1));
    final end = start.add(const Duration(days: 7)).subtract(const Duration(milliseconds: 1));
    return DateRange(start, end);
  }

  factory DateRange.year(DateTime anchor) {
    return DateRange(
      DateTime(anchor.year, 1, 1),
      DateTime(anchor.year, 12, 31, 23, 59, 59, 999),
    );
  }

  factory DateRange.quarter(DateTime anchor) {
    final q = (anchor.month - 1) ~/ 3;
    final start = DateTime(anchor.year, q * 3 + 1, 1);
    final end = DateTime(anchor.year, q * 3 + 4, 0, 23, 59, 59, 999);
    return DateRange(start, end);
  }

  factory DateRange.lastDays(int days, {DateTime? now}) {
    final today = now ?? DateTime.now();
    final end = DateTime(today.year, today.month, today.day, 23, 59, 59, 999);
    final start = DateTime(today.year, today.month, today.day).subtract(Duration(days: days - 1));
    return DateRange(start, end);
  }

  factory DateRange.custom(DateTime start, DateTime end) {
    return DateRange(
      DateTime(start.year, start.month, start.day),
      DateTime(end.year, end.month, end.day, 23, 59, 59, 999),
    );
  }

  bool contains(DateTime d) => !d.isBefore(start) && !d.isAfter(end);

  int get days => end.difference(start).inDays + 1;

  /// Days elapsed so far if the range includes today, else the full length.
  int elapsedDays(DateTime now) {
    if (now.isBefore(start)) return 0;
    if (now.isAfter(end)) return days;
    return now.difference(start).inDays + 1;
  }

  DateRange previous() {
    final length = end.difference(start);
    final prevEnd = start.subtract(const Duration(milliseconds: 1));
    return DateRange(prevEnd.subtract(length), prevEnd);
  }

  String label() {
    if (start.day == 1 && end.day == DateTime(end.year, end.month + 1, 0).day &&
        start.month == end.month && start.year == end.year) {
      return DateFormat('MMMM yyyy').format(start);
    }
    if (start.year == end.year) {
      return '${DateFormat('d MMM').format(start)} – ${DateFormat('d MMM yyyy').format(end)}';
    }
    return '${DateFormat('d MMM yyyy').format(start)} – ${DateFormat('d MMM yyyy').format(end)}';
  }

  @override
  bool operator ==(Object other) =>
      other is DateRange && other.start == start && other.end == end;

  @override
  int get hashCode => Object.hash(start, end);
}

class AppDates {
  AppDates._();

  static final DateFormat dayMonth = DateFormat('d MMM');
  static final DateFormat dayMonthYear = DateFormat('d MMM yyyy');
  static final DateFormat monthYear = DateFormat('MMM yyyy');
  static final DateFormat fullMonthYear = DateFormat('MMMM yyyy');
  static final DateFormat weekdayDate = DateFormat('EEE, d MMM');
  static final DateFormat time = DateFormat('h:mm a');
  static final DateFormat iso = DateFormat('yyyy-MM-dd');
  static final DateFormat fileStamp = DateFormat('yyyyMMdd_HHmm');

  static DateTime dateOnly(DateTime d) => DateTime(d.year, d.month, d.day);

  static bool sameDay(DateTime a, DateTime b) =>
      a.year == b.year && a.month == b.month && a.day == b.day;

  static String relativeDay(DateTime d, {DateTime? now}) {
    final today = dateOnly(now ?? DateTime.now());
    final target = dateOnly(d);
    final diff = target.difference(today).inDays;
    if (diff == 0) return 'Today';
    if (diff == -1) return 'Yesterday';
    if (diff == 1) return 'Tomorrow';
    if (target.year == today.year) return weekdayDate.format(d);
    return dayMonthYear.format(d);
  }

  static String timeAgo(DateTime d, {DateTime? now}) {
    final diff = (now ?? DateTime.now()).difference(d);
    if (diff.inSeconds < 60) return 'just now';
    if (diff.inMinutes < 60) return '${diff.inMinutes}m ago';
    if (diff.inHours < 24) return '${diff.inHours}h ago';
    if (diff.inDays < 7) return '${diff.inDays}d ago';
    return dayMonth.format(d);
  }

  static DateTime addMonths(DateTime d, int months) {
    final total = d.month - 1 + months;
    // Floor division so negative offsets cross year boundaries correctly.
    final year = d.year + (total - total % 12) ~/ 12;
    final month = total % 12 + 1;
    final lastDay = DateTime(year, month + 1, 0).day;
    return DateTime(year, month, d.day > lastDay ? lastDay : d.day);
  }
}
