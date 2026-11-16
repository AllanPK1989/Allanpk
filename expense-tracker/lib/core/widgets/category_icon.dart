import 'package:material_ui/material_ui.dart';

import '../constants/app_icons.dart';

/// Coloured rounded square holding a category / account / goal icon.
class IconBadge extends StatelessWidget {
  const IconBadge({
    super.key,
    required this.iconKey,
    required this.color,
    this.size = 44,
    this.radius,
    this.icon,
  });

  final String? iconKey;
  final int color;
  final double size;
  final double? radius;
  final IconData? icon;

  @override
  Widget build(BuildContext context) {
    final c = Color(color);
    return Container(
      width: size,
      height: size,
      decoration: BoxDecoration(
        color: c.withValues(alpha: 0.16),
        borderRadius: BorderRadius.circular(radius ?? size * 0.32),
      ),
      child: Icon(icon ?? iconFor(iconKey), color: c, size: size * 0.5),
    );
  }
}

class MemberAvatar extends StatelessWidget {
  const MemberAvatar({
    super.key,
    required this.initials,
    required this.color,
    this.photoUrl,
    this.size = 36,
  });

  final String initials;
  final int color;
  final String? photoUrl;
  final double size;

  @override
  Widget build(BuildContext context) {
    final c = Color(color);
    final hasPhoto = photoUrl != null && photoUrl!.isNotEmpty;
    return CircleAvatar(
      radius: size / 2,
      backgroundColor: c.withValues(alpha: 0.2),
      foregroundImage: hasPhoto ? NetworkImage(photoUrl!, webHtmlElementStrategy: WebHtmlElementStrategy.fallback) : null,
      child: Text(
        initials,
        style: TextStyle(
          color: c,
          fontWeight: FontWeight.w700,
          fontSize: size * 0.38,
        ),
      ),
    );
  }
}
