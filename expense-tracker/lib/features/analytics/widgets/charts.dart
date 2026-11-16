import 'dart:math' as math;

import 'package:fl_chart/fl_chart.dart';
import 'package:intl/intl.dart';
import 'package:material_ui/material_ui.dart';

import '../../../core/theme/app_theme.dart';
import '../../../core/utils/money.dart';
import '../analytics_engine.dart';

/// Daily expense line with a soft gradient fill.
class DailySpendChart extends StatelessWidget {
  const DailySpendChart({
    super.key,
    required this.points,
    required this.currency,
    this.height = 160,
    this.cumulative = false,
    this.compareTo,
  });

  final List<DailyPoint> points;
  final String currency;
  final double height;
  final bool cumulative;

  /// Optional previous-period series to draw as a dashed reference.
  final List<DailyPoint>? compareTo;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final text = Theme.of(context).textTheme;
    if (points.isEmpty) return SizedBox(height: height);
    final series = cumulative ? AnalyticsEngine.cumulativeSeries(points) : points;
    final spots = [
      for (var i = 0; i < series.length; i++) FlSpot(i.toDouble(), series[i].expense),
    ];
    List<FlSpot>? compareSpots;
    if (compareTo != null && compareTo!.isNotEmpty) {
      final c = cumulative ? AnalyticsEngine.cumulativeSeries(compareTo!) : compareTo!;
      compareSpots = [for (var i = 0; i < c.length; i++) FlSpot(i.toDouble(), c[i].expense)];
    }
    final maxY = [
      ...spots.map((s) => s.y),
      ...?compareSpots?.map((s) => s.y),
    ].fold<double>(0, math.max);
    final labelEvery = math.max(1, (series.length / 5).ceil());

    return SizedBox(
      height: height,
      child: LineChart(
        LineChartData(
          minY: 0,
          maxY: maxY <= 0 ? 10 : maxY * 1.15,
          gridData: FlGridData(
            drawVerticalLine: false,
            horizontalInterval: maxY <= 0 ? 5 : maxY / 3,
            getDrawingHorizontalLine: (_) => FlLine(
              color: scheme.outlineVariant.withValues(alpha: 0.4),
              strokeWidth: 1,
              dashArray: [4, 4],
            ),
          ),
          borderData: FlBorderData(show: false),
          titlesData: FlTitlesData(
            topTitles: const AxisTitles(),
            rightTitles: const AxisTitles(),
            leftTitles: AxisTitles(
              sideTitles: SideTitles(
                showTitles: true,
                reservedSize: 44,
                interval: maxY <= 0 ? 5 : maxY / 3,
                getTitlesWidget: (value, meta) => SideTitleWidget(
                  meta: meta,
                  child: Text(
                    Money.format(value, currency, compact: true),
                    style: text.labelSmall?.copyWith(color: scheme.onSurfaceVariant, fontSize: 10),
                  ),
                ),
              ),
            ),
            bottomTitles: AxisTitles(
              sideTitles: SideTitles(
                showTitles: true,
                reservedSize: 24,
                interval: labelEvery.toDouble(),
                getTitlesWidget: (value, meta) {
                  final i = value.round();
                  if (i < 0 || i >= series.length) return const SizedBox.shrink();
                  return SideTitleWidget(
                    meta: meta,
                    child: Text(
                      DateFormat('d MMM').format(series[i].date),
                      style: text.labelSmall?.copyWith(color: scheme.onSurfaceVariant, fontSize: 10),
                    ),
                  );
                },
              ),
            ),
          ),
          lineTouchData: LineTouchData(
            touchTooltipData: LineTouchTooltipData(
              getTooltipColor: (_) => scheme.inverseSurface,
              tooltipBorderRadius: BorderRadius.circular(10),
              getTooltipItems: (touched) => touched.map((s) {
                final i = s.x.round().clamp(0, series.length - 1);
                final isCompare = compareSpots != null && s.barIndex == 1;
                return LineTooltipItem(
                  '${isCompare ? 'Prev · ' : ''}${DateFormat('d MMM').format(series[i].date)}\n'
                  '${Money.format(s.y, currency)}',
                  text.labelMedium!.copyWith(color: scheme.onInverseSurface),
                );
              }).toList(),
            ),
          ),
          lineBarsData: [
            LineChartBarData(
              spots: spots,
              isCurved: true,
              curveSmoothness: 0.25,
              preventCurveOverShooting: true,
              color: scheme.primary,
              barWidth: 3,
              isStrokeCapRound: true,
              dotData: const FlDotData(show: false),
              belowBarData: BarAreaData(
                show: true,
                gradient: LinearGradient(
                  colors: [scheme.primary.withValues(alpha: 0.28), scheme.primary.withValues(alpha: 0)],
                  begin: Alignment.topCenter,
                  end: Alignment.bottomCenter,
                ),
              ),
            ),
            if (compareSpots != null)
              LineChartBarData(
                spots: compareSpots,
                isCurved: true,
                curveSmoothness: 0.25,
                preventCurveOverShooting: true,
                color: scheme.onSurfaceVariant.withValues(alpha: 0.5),
                barWidth: 2,
                dashArray: [6, 4],
                dotData: const FlDotData(show: false),
              ),
          ],
        ),
        duration: const Duration(milliseconds: 350),
      ),
    );
  }
}

/// Donut of category shares with a centre label.
class CategoryDonut extends StatelessWidget {
  const CategoryDonut({
    super.key,
    required this.slices,
    required this.currency,
    required this.total,
    this.size = 180,
    this.selectedIndex,
    this.onSelect,
    this.centerLabel,
  });

  final List<CategorySpend> slices;
  final String currency;
  final double total;
  final double size;
  final int? selectedIndex;
  final ValueChanged<int?>? onSelect;
  final String? centerLabel;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final text = Theme.of(context).textTheme;
    final selected = selectedIndex != null && selectedIndex! < slices.length ? slices[selectedIndex!] : null;
    return SizedBox(
      width: size,
      height: size,
      child: Stack(
        alignment: Alignment.center,
        children: [
          PieChart(
            PieChartData(
              sectionsSpace: 2,
              centerSpaceRadius: size * 0.32,
              startDegreeOffset: -90,
              pieTouchData: PieTouchData(
                touchCallback: (event, response) {
                  if (onSelect == null) return;
                  if (!event.isInterestedForInteractions || response?.touchedSection == null) {
                    return;
                  }
                  final idx = response!.touchedSection!.touchedSectionIndex;
                  onSelect!(idx < 0 ? null : idx);
                },
              ),
              sections: [
                if (slices.isEmpty)
                  PieChartSectionData(
                    value: 1,
                    color: scheme.surfaceContainerHighest,
                    radius: size * 0.16,
                    showTitle: false,
                  ),
                for (var i = 0; i < slices.length; i++)
                  PieChartSectionData(
                    value: slices[i].amount,
                    color: Color(slices[i].color),
                    radius: selectedIndex == i ? size * 0.2 : size * 0.16,
                    showTitle: false,
                  ),
              ],
            ),
            duration: const Duration(milliseconds: 300),
          ),
          Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                selected?.name ?? centerLabel ?? 'Total',
                style: text.labelSmall?.copyWith(color: scheme.onSurfaceVariant),
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
              ),
              Text(
                Money.format(selected?.amount ?? total, currency, compact: true),
                style: text.titleMedium?.copyWith(fontWeight: FontWeight.w700),
              ),
              if (selected != null)
                Text(
                  Money.percent(selected.share),
                  style: text.labelSmall?.copyWith(color: Color(selected.color), fontWeight: FontWeight.w700),
                ),
            ],
          ),
        ],
      ),
    );
  }
}

/// Grouped bars of income vs expense per month.
class IncomeExpenseBars extends StatelessWidget {
  const IncomeExpenseBars({
    super.key,
    required this.months,
    required this.currency,
    this.height = 200,
    this.showNet = false,
  });

  final List<MonthPoint> months;
  final String currency;
  final double height;
  final bool showNet;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final text = Theme.of(context).textTheme;
    final maxY = months.fold<double>(0, (m, p) => math.max(m, math.max(p.income, p.expense)));
    return SizedBox(
      height: height,
      child: BarChart(
        BarChartData(
          maxY: maxY <= 0 ? 10 : maxY * 1.15,
          alignment: BarChartAlignment.spaceAround,
          gridData: FlGridData(
            drawVerticalLine: false,
            horizontalInterval: maxY <= 0 ? 5 : maxY / 3,
            getDrawingHorizontalLine: (_) => FlLine(
              color: scheme.outlineVariant.withValues(alpha: 0.4),
              strokeWidth: 1,
              dashArray: [4, 4],
            ),
          ),
          borderData: FlBorderData(show: false),
          titlesData: FlTitlesData(
            topTitles: const AxisTitles(),
            rightTitles: const AxisTitles(),
            leftTitles: AxisTitles(
              sideTitles: SideTitles(
                showTitles: true,
                reservedSize: 44,
                interval: maxY <= 0 ? 5 : maxY / 3,
                getTitlesWidget: (value, meta) => SideTitleWidget(
                  meta: meta,
                  child: Text(
                    Money.format(value, currency, compact: true),
                    style: text.labelSmall?.copyWith(color: scheme.onSurfaceVariant, fontSize: 10),
                  ),
                ),
              ),
            ),
            bottomTitles: AxisTitles(
              sideTitles: SideTitles(
                showTitles: true,
                reservedSize: 24,
                getTitlesWidget: (value, meta) {
                  final i = value.round();
                  if (i < 0 || i >= months.length) return const SizedBox.shrink();
                  return SideTitleWidget(
                    meta: meta,
                    child: Text(
                      DateFormat('MMM').format(months[i].month),
                      style: text.labelSmall?.copyWith(color: scheme.onSurfaceVariant),
                    ),
                  );
                },
              ),
            ),
          ),
          barTouchData: BarTouchData(
            touchTooltipData: BarTouchTooltipData(
              getTooltipColor: (_) => scheme.inverseSurface,
              tooltipBorderRadius: BorderRadius.circular(10),
              getTooltipItem: (group, gi, rod, ri) => BarTooltipItem(
                '${DateFormat('MMM yyyy').format(months[group.x].month)}\n'
                '${ri == 0 ? 'Income' : 'Expense'}: ${Money.format(rod.toY, currency)}',
                text.labelMedium!.copyWith(color: scheme.onInverseSurface),
              ),
            ),
          ),
          barGroups: [
            for (var i = 0; i < months.length; i++)
              BarChartGroupData(
                x: i,
                barsSpace: 4,
                barRods: [
                  BarChartRodData(
                    toY: months[i].income,
                    color: AppTheme.income,
                    width: 10,
                    borderRadius: const BorderRadius.vertical(top: Radius.circular(4)),
                  ),
                  BarChartRodData(
                    toY: months[i].expense,
                    color: AppTheme.expense,
                    width: 10,
                    borderRadius: const BorderRadius.vertical(top: Radius.circular(4)),
                  ),
                ],
              ),
          ],
        ),
        duration: const Duration(milliseconds: 350),
      ),
    );
  }
}

/// Simple single-series bar chart (weekday pattern, member comparison...).
class SimpleBars extends StatelessWidget {
  const SimpleBars({
    super.key,
    required this.labels,
    required this.values,
    required this.currency,
    this.colors,
    this.height = 170,
    this.highlightMax = true,
  });

  final List<String> labels;
  final List<double> values;
  final String currency;
  final List<Color>? colors;
  final double height;
  final bool highlightMax;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final text = Theme.of(context).textTheme;
    final maxY = values.fold<double>(0, math.max);
    final maxIdx = values.indexOf(maxY);
    return SizedBox(
      height: height,
      child: BarChart(
        BarChartData(
          maxY: maxY <= 0 ? 10 : maxY * 1.2,
          alignment: BarChartAlignment.spaceAround,
          gridData: const FlGridData(show: false),
          borderData: FlBorderData(show: false),
          titlesData: FlTitlesData(
            topTitles: const AxisTitles(),
            rightTitles: const AxisTitles(),
            leftTitles: const AxisTitles(),
            bottomTitles: AxisTitles(
              sideTitles: SideTitles(
                showTitles: true,
                reservedSize: 26,
                getTitlesWidget: (value, meta) {
                  final i = value.round();
                  if (i < 0 || i >= labels.length) return const SizedBox.shrink();
                  return SideTitleWidget(
                    meta: meta,
                    child: Text(
                      labels[i],
                      style: text.labelSmall?.copyWith(color: scheme.onSurfaceVariant),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                  );
                },
              ),
            ),
          ),
          barTouchData: BarTouchData(
            touchTooltipData: BarTouchTooltipData(
              getTooltipColor: (_) => scheme.inverseSurface,
              tooltipBorderRadius: BorderRadius.circular(10),
              getTooltipItem: (group, gi, rod, ri) => BarTooltipItem(
                '${labels[group.x]}\n${Money.format(rod.toY, currency)}',
                text.labelMedium!.copyWith(color: scheme.onInverseSurface),
              ),
            ),
          ),
          barGroups: [
            for (var i = 0; i < values.length; i++)
              BarChartGroupData(
                x: i,
                barRods: [
                  BarChartRodData(
                    toY: values[i],
                    width: 18,
                    borderRadius: const BorderRadius.vertical(top: Radius.circular(6)),
                    color: colors != null && i < colors!.length
                        ? colors![i]
                        : (highlightMax && i == maxIdx && maxY > 0)
                            ? scheme.primary
                            : scheme.primary.withValues(alpha: 0.4),
                  ),
                ],
              ),
          ],
        ),
        duration: const Duration(milliseconds: 350),
      ),
    );
  }
}

/// Circular progress ring used for budgets and goals.
class ProgressRing extends StatelessWidget {
  const ProgressRing({
    super.key,
    required this.fraction,
    required this.color,
    this.size = 56,
    this.strokeWidth = 6,
    this.child,
  });

  final double fraction;
  final Color color;
  final double size;
  final double strokeWidth;
  final Widget? child;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return SizedBox(
      width: size,
      height: size,
      child: Stack(
        alignment: Alignment.center,
        children: [
          TweenAnimationBuilder<double>(
            tween: Tween(begin: 0, end: fraction.clamp(0, 1).toDouble()),
            duration: const Duration(milliseconds: 700),
            curve: Curves.easeOutCubic,
            builder: (context, value, _) => CustomPaint(
              size: Size.square(size),
              painter: _RingPainter(
                fraction: value,
                color: color,
                track: scheme.surfaceContainerHighest,
                strokeWidth: strokeWidth,
              ),
            ),
          ),
          ?child,
        ],
      ),
    );
  }
}

class _RingPainter extends CustomPainter {
  _RingPainter({
    required this.fraction,
    required this.color,
    required this.track,
    required this.strokeWidth,
  });

  final double fraction;
  final Color color;
  final Color track;
  final double strokeWidth;

  @override
  void paint(Canvas canvas, Size size) {
    final rect = Rect.fromLTWH(strokeWidth / 2, strokeWidth / 2, size.width - strokeWidth, size.height - strokeWidth);
    final paint = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = strokeWidth
      ..strokeCap = StrokeCap.round;
    paint.color = track;
    canvas.drawArc(rect, 0, math.pi * 2, false, paint);
    paint.color = color;
    canvas.drawArc(rect, -math.pi / 2, math.pi * 2 * fraction, false, paint);
  }

  @override
  bool shouldRepaint(covariant _RingPainter old) =>
      old.fraction != fraction || old.color != color || old.track != track;
}

/// Animated horizontal progress bar with budget colouring.
class BudgetBar extends StatelessWidget {
  const BudgetBar({super.key, required this.fraction, required this.color, this.height = 8});

  final double fraction;
  final Color color;
  final double height;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return ClipRRect(
      borderRadius: BorderRadius.circular(height),
      child: TweenAnimationBuilder<double>(
        tween: Tween(begin: 0, end: fraction.clamp(0, 1).toDouble()),
        duration: const Duration(milliseconds: 600),
        curve: Curves.easeOutCubic,
        builder: (context, value, _) => LinearProgressIndicator(
          value: value,
          minHeight: height,
          color: color,
          backgroundColor: scheme.surfaceContainerHighest,
        ),
      ),
    );
  }
}

Color budgetColor(BudgetStatus status) => switch (status) {
      BudgetStatus.onTrack => AppTheme.income,
      BudgetStatus.warning => AppTheme.warning,
      BudgetStatus.over => AppTheme.expense,
    };
