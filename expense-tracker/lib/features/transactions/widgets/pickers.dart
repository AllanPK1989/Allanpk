import 'dart:typed_data';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:image_picker/image_picker.dart';
import 'package:material_ui/material_ui.dart';

import '../../../core/utils/extensions.dart';
import '../../../core/widgets/widgets.dart';
import '../../../models/models.dart';
import '../../household/household_providers.dart';

/// Grid of categories in a bottom sheet. Returns the chosen id.
Future<String?> showCategoryPicker(
  BuildContext context, {
  required List<Category> categories,
  String? selected,
}) {
  return showModalBottomSheet<String>(
    context: context,
    isScrollControlled: true,
    builder: (sheet) {
      final parents = categories.where((c) => c.parentId == null).toList();
      final children = <String, List<Category>>{};
      for (final c in categories.where((c) => c.parentId != null)) {
        children.putIfAbsent(c.parentId!, () => []).add(c);
      }
      return DraggableScrollableSheet(
        expand: false,
        initialChildSize: 0.7,
        maxChildSize: 0.95,
        builder: (context, controller) => ListView(
          controller: controller,
          padding: const EdgeInsets.fromLTRB(16, 0, 16, 24),
          children: [
            Row(
              children: [
                Text('Choose category', style: context.text.titleMedium),
                const Spacer(),
                TextButton.icon(
                  onPressed: () {
                    Navigator.pop(sheet);
                    context.push('/categories/new?kind=${categories.isNotEmpty ? categories.first.kind.storageKey : 'expense'}');
                  },
                  icon: const Icon(Icons.add_rounded, size: 18),
                  label: const Text('New'),
                ),
              ],
            ),
            const SizedBox(height: 8),
            if (parents.isEmpty)
              const EmptyState(icon: Icons.category_rounded, title: 'No categories yet', compact: true),
            GridView.builder(
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              gridDelegate: const SliverGridDelegateWithMaxCrossAxisExtent(
                maxCrossAxisExtent: 96,
                mainAxisSpacing: 8,
                crossAxisSpacing: 8,
                childAspectRatio: 0.82,
              ),
              itemCount: parents.length,
              itemBuilder: (context, i) {
                final c = parents[i];
                final isSelected = c.id == selected;
                final subs = children[c.id] ?? const [];
                return InkWell(
                  borderRadius: BorderRadius.circular(14),
                  onTap: () async {
                    if (subs.isEmpty) {
                      Navigator.pop(sheet, c.id);
                      return;
                    }
                    final sub = await _pickSubcategory(context, c, subs);
                    if (sub != null && sheet.mounted) Navigator.pop(sheet, sub);
                  },
                  child: Container(
                    decoration: BoxDecoration(
                      color: isSelected ? Color(c.color).withValues(alpha: 0.14) : Colors.transparent,
                      borderRadius: BorderRadius.circular(14),
                      border: Border.all(color: isSelected ? Color(c.color) : Colors.transparent, width: 1.5),
                    ),
                    padding: const EdgeInsets.symmetric(vertical: 8, horizontal: 4),
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        IconBadge(iconKey: c.iconKey, color: c.color, size: 42),
                        const SizedBox(height: 6),
                        Text(
                          c.name,
                          style: context.text.labelSmall,
                          textAlign: TextAlign.center,
                          maxLines: 2,
                          overflow: TextOverflow.ellipsis,
                        ),
                        if (subs.isNotEmpty)
                          Text('${subs.length} sub', style: context.text.labelSmall?.copyWith(color: context.colors.onSurfaceVariant, fontSize: 9)),
                      ],
                    ),
                  ),
                );
              },
            ),
          ],
        ),
      );
    },
  );
}

Future<String?> _pickSubcategory(BuildContext context, Category parent, List<Category> subs) {
  return showModalBottomSheet<String>(
    context: context,
    builder: (sheet) => SafeArea(
      child: ListView(
        shrinkWrap: true,
        padding: const EdgeInsets.only(bottom: 12),
        children: [
          ListTile(
            leading: IconBadge(iconKey: parent.iconKey, color: parent.color, size: 36),
            title: Text(parent.name, style: context.text.titleSmall),
            subtitle: const Text('General'),
            onTap: () => Navigator.pop(sheet, parent.id),
          ),
          const Divider(),
          for (final s in subs)
            ListTile(
              leading: IconBadge(iconKey: s.iconKey, color: s.color, size: 36),
              title: Text(s.name),
              onTap: () => Navigator.pop(sheet, s.id),
            ),
        ],
      ),
    ),
  );
}

Future<String?> showAccountPicker(
  BuildContext context, {
  required List<Account> accounts,
  String? selected,
}) {
  return showModalBottomSheet<String>(
    context: context,
    builder: (sheet) => Consumer(
      builder: (context, ref, _) {
        final balances = {for (final b in ref.watch(balancesProvider)) b.account.id: b.balance};
        final currency = ref.watch(baseCurrencyProvider);
        return SafeArea(
          child: ListView(
            shrinkWrap: true,
            padding: const EdgeInsets.only(bottom: 12),
            children: [
              Padding(
                padding: const EdgeInsets.fromLTRB(20, 0, 12, 4),
                child: Row(
                  children: [
                    Text('Choose account', style: context.text.titleMedium),
                    const Spacer(),
                    TextButton.icon(
                      onPressed: () {
                        Navigator.pop(sheet);
                        context.push('/accounts/new');
                      },
                      icon: const Icon(Icons.add_rounded, size: 18),
                      label: const Text('New'),
                    ),
                  ],
                ),
              ),
              for (final a in accounts)
                ListTile(
                  leading: IconBadge(iconKey: a.resolvedIconKey, color: a.color, size: 40),
                  title: Text(a.name),
                  subtitle: Text(a.type.label),
                  trailing: AmountText(balances[a.id] ?? 0, currency: currency, style: context.text.labelLarge, colored: false),
                  selected: a.id == selected,
                  onTap: () => Navigator.pop(sheet, a.id),
                ),
            ],
          ),
        );
      },
    ),
  );
}

/// Payee text field with suggestions from previous transactions.
class PayeeField extends ConsumerWidget {
  const PayeeField({super.key, required this.controller, required this.label});
  final TextEditingController controller;
  final String label;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final suggestions = ref.watch(payeeSuggestionsProvider);
    return RawAutocomplete<String>(
      textEditingController: controller,
      focusNode: FocusNode(),
      optionsBuilder: (value) {
        final q = value.text.toLowerCase().trim();
        if (q.isEmpty) return const Iterable<String>.empty();
        return suggestions.where((s) => s.toLowerCase().contains(q)).take(6);
      },
      onSelected: (s) => controller.text = s,
      fieldViewBuilder: (context, textController, focusNode, onSubmit) => TextField(
        controller: textController,
        focusNode: focusNode,
        textCapitalization: TextCapitalization.words,
        decoration: InputDecoration(labelText: label, prefixIcon: const Icon(Icons.storefront_outlined)),
      ),
      optionsViewBuilder: (context, onSelected, options) => Align(
        alignment: Alignment.topLeft,
        child: Material(
          elevation: 4,
          borderRadius: BorderRadius.circular(12),
          clipBehavior: Clip.antiAlias,
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxHeight: 220, maxWidth: 360),
            child: ListView(
              shrinkWrap: true,
              padding: EdgeInsets.zero,
              children: [
                for (final o in options)
                  ListTile(dense: true, title: Text(o), onTap: () => onSelected(o)),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

/// Chip-based tag editor.
class TagEditor extends ConsumerWidget {
  const TagEditor({super.key, required this.tags, required this.controller, required this.onChanged});
  final List<String> tags;
  final TextEditingController controller;
  final ValueChanged<List<String>> onChanged;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final suggestions = ref.watch(tagSuggestionsProvider).where((t) => !tags.contains(t)).take(8).toList();
    void add(String raw) {
      final t = raw.trim().replaceAll('#', '').toLowerCase();
      if (t.isEmpty || tags.contains(t)) return;
      onChanged([...tags, t]);
      controller.clear();
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        TextField(
          controller: controller,
          decoration: InputDecoration(
            labelText: 'Tags (optional)',
            prefixIcon: const Icon(Icons.tag_rounded),
            suffixIcon: IconButton(icon: const Icon(Icons.add_rounded), onPressed: () => add(controller.text)),
            hintText: 'e.g. vacation, office',
          ),
          onSubmitted: add,
        ),
        if (tags.isNotEmpty || suggestions.isNotEmpty) const SizedBox(height: 8),
        Wrap(
          spacing: 6,
          runSpacing: 6,
          children: [
            for (final t in tags)
              InputChip(
                label: Text('#$t'),
                onDeleted: () => onChanged(tags.where((x) => x != t).toList()),
              ),
            for (final s in suggestions)
              ActionChip(
                label: Text('#$s'),
                avatar: const Icon(Icons.add_rounded, size: 16),
                onPressed: () => add(s),
              ),
          ],
        ),
      ],
    );
  }
}

/// Receipt attachments: existing URLs plus newly picked bytes.
class ReceiptPicker extends StatelessWidget {
  const ReceiptPicker({
    super.key,
    required this.existing,
    required this.pending,
    required this.onAdd,
    required this.onRemoveExisting,
    required this.onRemovePending,
  });

  final List<String> existing;
  final List<Uint8List> pending;
  final ValueChanged<ImageSource> onAdd;
  final ValueChanged<String> onRemoveExisting;
  final ValueChanged<int> onRemovePending;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Text('Receipts', style: context.text.titleSmall),
            const Spacer(),
            TextButton.icon(
              onPressed: () => onAdd(ImageSource.camera),
              icon: const Icon(Icons.photo_camera_outlined, size: 18),
              label: const Text('Camera'),
            ),
            TextButton.icon(
              onPressed: () => onAdd(ImageSource.gallery),
              icon: const Icon(Icons.photo_library_outlined, size: 18),
              label: const Text('Gallery'),
            ),
          ],
        ),
        if (existing.isNotEmpty || pending.isNotEmpty)
          SizedBox(
            height: 88,
            child: ListView(
              scrollDirection: Axis.horizontal,
              children: [
                for (final url in existing)
                  _Thumb(image: Image.network(url, fit: BoxFit.cover), onRemove: () => onRemoveExisting(url)),
                for (var i = 0; i < pending.length; i++)
                  _Thumb(image: Image.memory(pending[i], fit: BoxFit.cover), onRemove: () => onRemovePending(i)),
              ],
            ),
          ),
      ],
    );
  }
}

class _Thumb extends StatelessWidget {
  const _Thumb({required this.image, required this.onRemove});
  final Widget image;
  final VoidCallback onRemove;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(right: 10, top: 6),
      child: Stack(
        clipBehavior: Clip.none,
        children: [
          ClipRRect(
            borderRadius: BorderRadius.circular(12),
            child: SizedBox(width: 80, height: 80, child: image),
          ),
          Positioned(
            right: -6,
            top: -6,
            child: GestureDetector(
              onTap: onRemove,
              child: Container(
                padding: const EdgeInsets.all(3),
                decoration: BoxDecoration(color: context.colors.error, shape: BoxShape.circle),
                child: Icon(Icons.close_rounded, size: 14, color: context.colors.onError),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
