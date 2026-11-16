import 'package:material_ui/material_ui.dart';

/// Flat, rounded surface used for every dashboard tile and list block.
class AppCard extends StatelessWidget {
  const AppCard({
    super.key,
    required this.child,
    this.padding = const EdgeInsets.all(16),
    this.onTap,
    this.color,
    this.gradient,
    this.borderRadius = 20,
    this.margin,
  });

  final Widget child;
  final EdgeInsetsGeometry padding;
  final VoidCallback? onTap;
  final Color? color;
  final Gradient? gradient;
  final double borderRadius;
  final EdgeInsetsGeometry? margin;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final radius = BorderRadius.circular(borderRadius);
    final content = Container(
      decoration: BoxDecoration(
        color: gradient == null ? (color ?? scheme.surfaceContainerLowest) : null,
        gradient: gradient,
        borderRadius: radius,
        border: gradient == null
            ? Border.all(color: scheme.outlineVariant.withValues(alpha: isDark ? 0.4 : 0.6))
            : null,
      ),
      padding: padding,
      child: child,
    );
    final body = onTap == null
        ? content
        : Material(
            color: Colors.transparent,
            borderRadius: radius,
            child: InkWell(onTap: onTap, borderRadius: radius, child: content),
          );
    if (margin != null) return Padding(padding: margin!, child: body);
    return body;
  }
}

class SectionHeader extends StatelessWidget {
  const SectionHeader({
    super.key,
    required this.title,
    this.subtitle,
    this.actionLabel,
    this.onAction,
    this.padding = const EdgeInsets.fromLTRB(4, 8, 0, 10),
  });

  final String title;
  final String? subtitle;
  final String? actionLabel;
  final VoidCallback? onAction;
  final EdgeInsetsGeometry padding;

  @override
  Widget build(BuildContext context) {
    final text = Theme.of(context).textTheme;
    final scheme = Theme.of(context).colorScheme;
    return Padding(
      padding: padding,
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(title, style: text.titleMedium),
                if (subtitle != null)
                  Text(subtitle!, style: text.bodySmall?.copyWith(color: scheme.onSurfaceVariant)),
              ],
            ),
          ),
          if (actionLabel != null)
            TextButton(
              onPressed: onAction,
              style: TextButton.styleFrom(
                padding: const EdgeInsets.symmetric(horizontal: 10),
                visualDensity: VisualDensity.compact,
              ),
              child: Text(actionLabel!),
            ),
        ],
      ),
    );
  }
}
