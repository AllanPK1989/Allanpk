import 'package:flutter/services.dart';
import 'package:go_router/go_router.dart';
import 'package:material_ui/material_ui.dart';

/// Navigation shell hosting the five main tabs: a bottom bar on phones and a
/// rail on wide screens, plus keyboard shortcuts for the web.
class HomeShell extends StatelessWidget {
  const HomeShell({super.key, required this.shell});

  final StatefulNavigationShell shell;

  static const _destinations = [
    _Dest('Home', Icons.home_outlined, Icons.home_rounded),
    _Dest('Transactions', Icons.receipt_long_outlined, Icons.receipt_long_rounded),
    _Dest('Budgets', Icons.pie_chart_outline_rounded, Icons.pie_chart_rounded),
    _Dest('Insights', Icons.insights_outlined, Icons.insights_rounded),
    _Dest('More', Icons.grid_view_outlined, Icons.grid_view_rounded),
  ];

  void _select(int index) => shell.goBranch(index, initialLocation: index == shell.currentIndex);

  /// Ignore shortcuts while the user is typing in a text field.
  static bool _typing() {
    final focus = FocusManager.instance.primaryFocus;
    final ctx = focus?.context;
    if (ctx == null) return false;
    return ctx.findAncestorWidgetOfExactType<EditableText>() != null;
  }

  @override
  Widget build(BuildContext context) {
    final wide = MediaQuery.sizeOf(context).width >= 840;

    final shortcuts = <ShortcutActivator, VoidCallback>{
      const SingleActivator(LogicalKeyboardKey.keyN): () {
        if (!_typing()) context.push('/transactions/new');
      },
      const SingleActivator(LogicalKeyboardKey.slash): () {
        if (!_typing()) context.push('/search');
      },
      for (var i = 0; i < _destinations.length; i++)
        SingleActivator(LogicalKeyboardKey(LogicalKeyboardKey.digit1.keyId + i)): () {
          if (!_typing()) _select(i);
        },
    };

    final fab = FloatingActionButton.extended(
      heroTag: 'add-transaction',
      tooltip: 'New transaction (N)',
      onPressed: () => context.push('/transactions/new'),
      icon: const Icon(Icons.add_rounded),
      label: const Text('Add'),
    );

    Widget body;
    if (wide) {
      body = Scaffold(
        body: Row(
          children: [
            NavigationRail(
              selectedIndex: shell.currentIndex,
              onDestinationSelected: _select,
              labelType: NavigationRailLabelType.all,
              groupAlignment: -0.9,
              leading: Padding(
                padding: const EdgeInsets.only(bottom: 16, top: 8),
                child: FloatingActionButton(
                  heroTag: 'add-transaction',
                  tooltip: 'New transaction (N)',
                  onPressed: () => context.push('/transactions/new'),
                  child: const Icon(Icons.add_rounded),
                ),
              ),
              destinations: [
                for (final d in _destinations)
                  NavigationRailDestination(
                    icon: Icon(d.icon),
                    selectedIcon: Icon(d.selectedIcon),
                    label: Text(d.label),
                  ),
              ],
            ),
            const VerticalDivider(width: 1),
            Expanded(child: shell),
          ],
        ),
      );
    } else {
      body = Scaffold(
        body: shell,
        floatingActionButton: shell.currentIndex == 4 ? null : fab,
        bottomNavigationBar: NavigationBar(
          selectedIndex: shell.currentIndex,
          onDestinationSelected: _select,
          labelBehavior: NavigationDestinationLabelBehavior.alwaysShow,
          destinations: [
            for (final d in _destinations)
              NavigationDestination(
                icon: Icon(d.icon),
                selectedIcon: Icon(d.selectedIcon),
                label: d.label,
              ),
          ],
        ),
      );
    }

    return CallbackShortcuts(
      bindings: shortcuts,
      child: Focus(autofocus: true, child: body),
    );
  }
}

class _Dest {
  const _Dest(this.label, this.icon, this.selectedIcon);
  final String label;
  final IconData icon;
  final IconData selectedIcon;
}
