import 'package:flutter_animate/flutter_animate.dart';
import 'package:material_ui/material_ui.dart';

class EmptyState extends StatelessWidget {
  const EmptyState({
    super.key,
    required this.icon,
    required this.title,
    this.message,
    this.actionLabel,
    this.onAction,
    this.compact = false,
  });

  final IconData icon;
  final String title;
  final String? message;
  final String? actionLabel;
  final VoidCallback? onAction;
  final bool compact;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final text = Theme.of(context).textTheme;
    return Center(
      child: Padding(
        padding: EdgeInsets.all(compact ? 16 : 32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: compact ? 56 : 88,
              height: compact ? 56 : 88,
              decoration: BoxDecoration(
                color: scheme.primaryContainer.withValues(alpha: 0.5),
                shape: BoxShape.circle,
              ),
              child: Icon(icon, size: compact ? 28 : 40, color: scheme.primary),
            ).animate().scale(duration: 400.ms, curve: Curves.easeOutBack),
            SizedBox(height: compact ? 12 : 20),
            Text(
              title,
              style: compact ? text.titleSmall : text.titleMedium,
              textAlign: TextAlign.center,
            ),
            if (message != null) ...[
              const SizedBox(height: 6),
              Text(
                message!,
                style: text.bodySmall?.copyWith(color: scheme.onSurfaceVariant),
                textAlign: TextAlign.center,
              ),
            ],
            if (actionLabel != null) ...[
              const SizedBox(height: 16),
              FilledButton.tonal(onPressed: onAction, child: Text(actionLabel!)),
            ],
          ],
        ),
      ),
    );
  }
}

class ErrorState extends StatelessWidget {
  const ErrorState({super.key, required this.error, this.onRetry});

  final Object error;
  final VoidCallback? onRetry;

  @override
  Widget build(BuildContext context) {
    return EmptyState(
      icon: Icons.error_outline_rounded,
      title: 'Something went wrong',
      message: error.toString(),
      actionLabel: onRetry == null ? null : 'Retry',
      onAction: onRetry,
    );
  }
}

class LoadingState extends StatelessWidget {
  const LoadingState({super.key});

  @override
  Widget build(BuildContext context) {
    return const Center(child: CircularProgressIndicator());
  }
}
