import 'package:material_ui/material_ui.dart';

import '../constants/app_icons.dart';
import '../constants/currencies.dart';

/// Horizontal colour swatch picker.
class ColorPicker extends StatelessWidget {
  const ColorPicker({super.key, required this.selected, required this.onChanged});

  final int selected;
  final ValueChanged<int> onChanged;

  @override
  Widget build(BuildContext context) {
    return Wrap(
      spacing: 10,
      runSpacing: 10,
      children: [
        for (final c in kPalette)
          GestureDetector(
            onTap: () => onChanged(c),
            child: AnimatedContainer(
              duration: const Duration(milliseconds: 180),
              width: 36,
              height: 36,
              decoration: BoxDecoration(
                color: Color(c),
                shape: BoxShape.circle,
                border: Border.all(
                  color: selected == c ? Theme.of(context).colorScheme.onSurface : Colors.transparent,
                  width: 3,
                ),
              ),
              child: selected == c ? const Icon(Icons.check, color: Colors.white, size: 18) : null,
            ),
          ),
      ],
    );
  }
}

/// Grid of icons from the catalogue.
class IconPicker extends StatelessWidget {
  const IconPicker({
    super.key,
    required this.selected,
    required this.onChanged,
    required this.color,
  });

  final String selected;
  final ValueChanged<String> onChanged;
  final int color;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Wrap(
      spacing: 8,
      runSpacing: 8,
      children: [
        for (final entry in kIconCatalog.entries)
          InkWell(
            borderRadius: BorderRadius.circular(12),
            onTap: () => onChanged(entry.key),
            child: AnimatedContainer(
              duration: const Duration(milliseconds: 150),
              width: 44,
              height: 44,
              decoration: BoxDecoration(
                color: selected == entry.key
                    ? Color(color).withValues(alpha: 0.18)
                    : scheme.surfaceContainerHighest.withValues(alpha: 0.5),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(
                  color: selected == entry.key ? Color(color) : Colors.transparent,
                  width: 1.5,
                ),
              ),
              child: Icon(
                entry.value,
                color: selected == entry.key ? Color(color) : scheme.onSurfaceVariant,
                size: 22,
              ),
            ),
          ),
      ],
    );
  }
}

/// Searchable currency picker shown as a bottom sheet.
Future<String?> showCurrencyPicker(BuildContext context, {String? selected}) {
  return showModalBottomSheet<String>(
    context: context,
    isScrollControlled: true,
    builder: (context) => _CurrencySheet(selected: selected),
  );
}

class _CurrencySheet extends StatefulWidget {
  const _CurrencySheet({this.selected});
  final String? selected;

  @override
  State<_CurrencySheet> createState() => _CurrencySheetState();
}

class _CurrencySheetState extends State<_CurrencySheet> {
  String _query = '';

  @override
  Widget build(BuildContext context) {
    final items = kCurrencies
        .where(
          (c) =>
              _query.isEmpty ||
              c.code.toLowerCase().contains(_query) ||
              c.name.toLowerCase().contains(_query),
        )
        .toList();
    return DraggableScrollableSheet(
      expand: false,
      initialChildSize: 0.75,
      maxChildSize: 0.95,
      builder: (context, controller) => Column(
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(20, 0, 20, 12),
            child: TextField(
              autofocus: false,
              decoration: const InputDecoration(
                hintText: 'Search currency',
                prefixIcon: Icon(Icons.search_rounded),
              ),
              onChanged: (v) => setState(() => _query = v.toLowerCase()),
            ),
          ),
          Expanded(
            child: ListView.builder(
              controller: controller,
              itemCount: items.length,
              itemBuilder: (context, i) {
                final c = items[i];
                final selected = c.code == widget.selected;
                return ListTile(
                  leading: CircleAvatar(
                    backgroundColor: Theme.of(context).colorScheme.primaryContainer,
                    child: Text(c.symbol, style: const TextStyle(fontWeight: FontWeight.w700)),
                  ),
                  title: Text(c.code),
                  subtitle: Text(c.name),
                  trailing: selected ? const Icon(Icons.check_circle_rounded) : null,
                  onTap: () => Navigator.of(context).pop(c.code),
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}

/// Simple confirm dialog returning true when confirmed.
Future<bool> confirmDialog(
  BuildContext context, {
  required String title,
  required String message,
  String confirmLabel = 'Delete',
  bool destructive = true,
}) async {
  final result = await showDialog<bool>(
    context: context,
    builder: (context) => AlertDialog(
      title: Text(title),
      content: Text(message),
      actions: [
        TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('Cancel')),
        FilledButton(
          style: destructive
              ? FilledButton.styleFrom(
                  backgroundColor: Theme.of(context).colorScheme.error,
                  foregroundColor: Theme.of(context).colorScheme.onError,
                  minimumSize: const Size(0, 44),
                )
              : FilledButton.styleFrom(minimumSize: const Size(0, 44)),
          onPressed: () => Navigator.pop(context, true),
          child: Text(confirmLabel),
        ),
      ],
    ),
  );
  return result ?? false;
}

/// Opens the platform date picker constrained to a sensible range.
Future<DateTime?> pickDate(BuildContext context, {DateTime? initial, DateTime? first, DateTime? last}) {
  return showDatePicker(
    context: context,
    initialDate: initial ?? DateTime.now(),
    firstDate: first ?? DateTime(2000),
    lastDate: last ?? DateTime(2100),
  );
}
