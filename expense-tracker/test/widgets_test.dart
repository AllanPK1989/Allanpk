import 'package:expense_budget_manager/core/theme/app_theme.dart';
import 'package:expense_budget_manager/core/widgets/widgets.dart';
import 'package:expense_budget_manager/features/analytics/analytics_engine.dart';
import 'package:expense_budget_manager/features/analytics/widgets/charts.dart';
import 'package:expense_budget_manager/models/models.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:material_ui/material_ui.dart';

Widget wrap(Widget child) => MaterialApp(
      theme: AppTheme.light(kAccentOptions.first.seed),
      home: Scaffold(body: Center(child: child)),
    );

void main() {
  testWidgets('AmountText colours income and expense', (tester) async {
    await tester.pumpWidget(
      wrap(
        const Column(
          children: [
            AmountText(1200, currency: 'INR', type: TransactionType.expense, signed: true),
            AmountText(800, currency: 'INR', type: TransactionType.income, signed: true),
          ],
        ),
      ),
    );
    final expense = tester.widget<Text>(find.text('-₹1,200.00'));
    final income = tester.widget<Text>(find.text('+₹800.00'));
    expect(expense.style?.color, AppTheme.expense);
    expect(income.style?.color, AppTheme.income);
  });

  testWidgets('EmptyState shows title, message and action', (tester) async {
    var tapped = false;
    await tester.pumpWidget(
      wrap(
        EmptyState(
          icon: Icons.receipt_long_rounded,
          title: 'Nothing here',
          message: 'Add something',
          actionLabel: 'Add',
          onAction: () => tapped = true,
        ),
      ),
    );
    await tester.pumpAndSettle();
    expect(find.text('Nothing here'), findsOneWidget);
    expect(find.text('Add something'), findsOneWidget);
    await tester.tap(find.text('Add'));
    expect(tapped, isTrue);
  });

  testWidgets('charts render without data and with data', (tester) async {
    final points = [
      for (var d = 1; d <= 7; d++) DailyPoint(DateTime(2026, 11, d), d * 100.0, 0),
    ];
    await tester.pumpWidget(
      wrap(
        SizedBox(
          width: 360,
          child: Column(
            children: [
              DailySpendChart(points: points, currency: 'INR'),
              const CategoryDonut(slices: [], currency: 'INR', total: 0, size: 120),
              const ProgressRing(fraction: 0.6, color: Colors.green, child: Text('60%')),
              const BudgetBar(fraction: 1.2, color: Colors.red),
            ],
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();
    expect(find.text('60%'), findsOneWidget);
    expect(find.byType(DailySpendChart), findsOneWidget);
  });

  testWidgets('confirmDialog resolves true on confirm', (tester) async {
    late Future<bool> result;
    await tester.pumpWidget(
      wrap(
        Builder(
          builder: (context) => FilledButton(
            onPressed: () => result = confirmDialog(context, title: 'Delete?', message: 'Sure?'),
            child: const Text('Go'),
          ),
        ),
      ),
    );
    await tester.tap(find.text('Go'));
    await tester.pumpAndSettle();
    expect(find.text('Delete?'), findsOneWidget);
    await tester.tap(find.text('Delete'));
    await tester.pumpAndSettle();
    expect(await result, isTrue);
  });
}
