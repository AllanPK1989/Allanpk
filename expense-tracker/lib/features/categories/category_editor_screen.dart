import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:material_ui/material_ui.dart';

import '../../core/utils/extensions.dart';
import '../../core/widgets/widgets.dart';
import '../../models/models.dart';
import '../household/household_providers.dart';

class CategoryEditorScreen extends ConsumerStatefulWidget {
  const CategoryEditorScreen({super.key, this.editId, this.initialKind});
  final String? editId;
  final String? initialKind;

  @override
  ConsumerState<CategoryEditorScreen> createState() => _CategoryEditorScreenState();
}

class _CategoryEditorScreenState extends ConsumerState<CategoryEditorScreen> {
  final _name = TextEditingController();
  CategoryKind _kind = CategoryKind.expense;
  String _icon = 'category';
  int _color = 0xFF6750A4;
  String? _parentId;
  bool _archived = false;
  Category? _editing;
  bool _loaded = false;

  @override
  void initState() {
    super.initState();
    _kind = CategoryKind.fromKey(widget.initialKind);
  }

  @override
  void dispose() {
    _name.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final all = ref.watch(categoriesProvider).value ?? const [];
    if (!_loaded && widget.editId != null) {
      final c = all.where((c) => c.id == widget.editId).firstOrNull;
      if (c != null) {
        _editing = c;
        _name.text = c.name;
        _kind = c.kind;
        _icon = c.iconKey;
        _color = c.color;
        _parentId = c.parentId;
        _archived = c.isArchived;
        _loaded = true;
      }
    } else {
      _loaded = true;
    }
    final parents = all.where((c) => c.kind == _kind && c.parentId == null && c.id != _editing?.id && !c.isArchived).toList();
    final hasChildren = _editing != null && all.any((c) => c.parentId == _editing!.id);

    return Scaffold(
      appBar: AppBar(
        title: Text(_editing == null ? 'New category' : 'Edit category'),
        actions: [
          if (_editing != null && !_editing!.isDefault)
            IconButton(icon: const Icon(Icons.delete_outline_rounded), onPressed: _delete),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(16, 8, 16, 120),
        children: [
          Center(child: IconBadge(iconKey: _icon, color: _color, size: 72)),
          const SizedBox(height: 16),
          TextField(
            controller: _name,
            textCapitalization: TextCapitalization.words,
            decoration: const InputDecoration(labelText: 'Name', prefixIcon: Icon(Icons.label_outline_rounded)),
          ),
          const SizedBox(height: 12),
          if (_editing == null)
            SegmentedButton<CategoryKind>(
              segments: const [
                ButtonSegment(value: CategoryKind.expense, label: Text('Expense')),
                ButtonSegment(value: CategoryKind.income, label: Text('Income')),
              ],
              selected: {_kind},
              showSelectedIcon: false,
              onSelectionChanged: (s) => setState(() {
                _kind = s.first;
                _parentId = null;
              }),
            ),
          if (!hasChildren) ...[
            const SizedBox(height: 12),
            DropdownMenu<String?>(
              initialSelection: _parentId,
              expandedInsets: EdgeInsets.zero,
              label: const Text('Parent category (optional)'),
              leadingIcon: const Icon(Icons.account_tree_outlined),
              dropdownMenuEntries: [
                const DropdownMenuEntry<String?>(value: null, label: 'None — top level'),
                for (final p in parents) DropdownMenuEntry<String?>(value: p.id, label: p.name),
              ],
              onSelected: (v) => setState(() => _parentId = v),
            ),
          ],
          if (_editing != null)
            SwitchListTile(
              contentPadding: EdgeInsets.zero,
              title: const Text('Archived'),
              subtitle: const Text('Hidden from pickers; history is kept'),
              value: _archived,
              onChanged: (v) => setState(() => _archived = v),
            ),
          const SizedBox(height: 12),
          Text('Colour', style: context.text.titleSmall),
          const SizedBox(height: 8),
          ColorPicker(selected: _color, onChanged: (c) => setState(() => _color = c)),
          const SizedBox(height: 16),
          Text('Icon', style: context.text.titleSmall),
          const SizedBox(height: 8),
          IconPicker(selected: _icon, color: _color, onChanged: (k) => setState(() => _icon = k)),
        ],
      ),
      bottomNavigationBar: SafeArea(
        minimum: const EdgeInsets.fromLTRB(16, 8, 16, 16),
        child: FilledButton(onPressed: _save, child: Text(_editing == null ? 'Create category' : 'Save changes')),
      ),
    );
  }

  Future<void> _save() async {
    if (_name.text.trim().isEmpty) {
      context.showSnack('Enter a name', error: true);
      return;
    }
    final ledger = ref.read(ledgerProvider);
    if (ledger == null) return;
    final count = ref.read(categoriesProvider).value?.length ?? 0;
    final category = Category(
      id: _editing?.id ?? ledger.newId('categories'),
      name: _name.text.trim(),
      kind: _kind,
      iconKey: _icon,
      color: _color,
      parentId: _parentId,
      isArchived: _archived,
      sortOrder: _editing?.sortOrder ?? count,
      isDefault: _editing?.isDefault ?? false,
    );
    await ledger.saveCategory(category);
    if (mounted) context.pop();
  }

  Future<void> _delete() async {
    final c = _editing;
    if (c == null) return;
    final used = (ref.read(allTransactionsProvider).value ?? const []).any((t) => t.categoryId == c.id);
    if (used) {
      final archive = await confirmDialog(
        context,
        title: 'Category in use',
        message: 'Transactions reference this category. Archive it instead to keep your history accurate?',
        confirmLabel: 'Archive',
        destructive: false,
      );
      if (!archive || !mounted) return;
      await ref.read(ledgerProvider)?.saveCategory(c.copyWith(isArchived: true));
    } else {
      final ok = await confirmDialog(context, title: 'Delete category?', message: 'This cannot be undone.');
      if (!ok || !mounted) return;
      await ref.read(ledgerProvider)?.deleteCategory(c.id);
    }
    if (mounted) context.pop();
  }
}
