import 'package:cloud_firestore/cloud_firestore.dart' hide Transaction;

import '../core/utils/date_utils.dart';
import '../core/utils/money.dart';
import '../models/models.dart';
import 'firestore_refs.dart';

/// Everything that lives inside a household: accounts, categories,
/// transactions, budgets, goals, recurring rules and the activity feed.
class LedgerRepository {
  LedgerRepository(this._refs, this.householdId);

  final FirestoreRefs _refs;
  final String householdId;

  // ---------------------------------------------------------------- streams

  Stream<List<Account>> watchAccounts() => _refs
      .accounts(householdId)
      .snapshots()
      .map((s) => s.docs.map((d) => Account.fromMap(d.id, d.data())).toList()
        ..sort((a, b) => a.sortOrder.compareTo(b.sortOrder)));

  Stream<List<Category>> watchCategories() => _refs
      .categories(householdId)
      .snapshots()
      .map((s) => s.docs.map((d) => Category.fromMap(d.id, d.data())).toList()
        ..sort((a, b) => a.sortOrder.compareTo(b.sortOrder)));

  Stream<List<Budget>> watchBudgets() => _refs
      .budgets(householdId)
      .snapshots()
      .map((s) => s.docs.map((d) => Budget.fromMap(d.id, d.data())).toList());

  Stream<List<Goal>> watchGoals() => _refs
      .goals(householdId)
      .snapshots()
      .map((s) => s.docs.map((d) => Goal.fromMap(d.id, d.data())).toList());

  Stream<List<RecurringRule>> watchRecurring() => _refs
      .recurring(householdId)
      .snapshots()
      .map((s) => s.docs.map((d) => RecurringRule.fromMap(d.id, d.data())).toList()
        ..sort((a, b) => a.nextDue.compareTo(b.nextDue)));

  Stream<List<ActivityEntry>> watchActivity({int limit = 50}) => _refs
      .activity(householdId)
      .orderBy('at', descending: true)
      .limit(limit)
      .snapshots()
      .map((s) => s.docs.map((d) => ActivityEntry.fromMap(d.id, d.data())).toList());

  /// Transactions within [range] visible to [uid]: everything shared plus the
  /// caller's private entries.
  Stream<List<Transaction>> watchTransactions(DateRange range, String uid) {
    return _refs
        .transactions(householdId)
        .where(
          Filter.or(
            Filter('isPrivate', isEqualTo: false),
            Filter('createdBy', isEqualTo: uid),
          ),
        )
        .where('date', isGreaterThanOrEqualTo: Timestamp.fromDate(range.start))
        .where('date', isLessThanOrEqualTo: Timestamp.fromDate(range.end))
        .orderBy('date', descending: true)
        .snapshots()
        .map((s) => s.docs.map((d) => Transaction.fromMap(d.id, d.data())).toList());
  }

  /// All transactions visible to [uid], ordered newest first. Used for
  /// running balances and full exports. Firestore keeps this cached offline.
  Stream<List<Transaction>> watchAllTransactions(String uid) {
    return _refs
        .transactions(householdId)
        .where(
          Filter.or(
            Filter('isPrivate', isEqualTo: false),
            Filter('createdBy', isEqualTo: uid),
          ),
        )
        .orderBy('date', descending: true)
        .snapshots()
        .map((s) => s.docs.map((d) => Transaction.fromMap(d.id, d.data())).toList());
  }

  Stream<Transaction?> watchTransaction(String id) {
    return _refs.transactions(householdId).doc(id).snapshots().map((snap) {
      final data = snap.data();
      return data == null ? null : Transaction.fromMap(snap.id, data);
    });
  }

  // --------------------------------------------------------------- accounts

  String newId(String collection) => _refs.household(householdId).collection(collection).doc().id;

  Future<void> saveAccount(Account account) =>
      _refs.accounts(householdId).doc(account.id).set(account.toMap(), SetOptions(merge: true));

  Future<void> deleteAccount(String id) => _refs.accounts(householdId).doc(id).delete();

  // ------------------------------------------------------------- categories

  Future<void> saveCategory(Category category) => _refs
      .categories(householdId)
      .doc(category.id)
      .set(category.toMap(), SetOptions(merge: true));

  Future<void> deleteCategory(String id) => _refs.categories(householdId).doc(id).delete();

  Future<void> reorderCategories(List<Category> ordered) async {
    final batch = _refs.db.batch();
    for (var i = 0; i < ordered.length; i++) {
      batch.update(_refs.categories(householdId).doc(ordered[i].id), {'sortOrder': i});
    }
    await batch.commit();
  }

  // ----------------------------------------------------------- transactions

  Future<void> addTransaction(Transaction tx, {UserProfile? actor, String? categoryName}) async {
    final batch = _refs.db.batch();
    batch.set(_refs.transactions(householdId).doc(tx.id), tx.toMap());
    if (tx.goalId != null && tx.isTransfer) {
      batch.update(_refs.goals(householdId).doc(tx.goalId!), {
        'savedAmount': FieldValue.increment(tx.amount),
      });
    }
    if (actor != null && !tx.isPrivate) {
      _logActivity(
        batch,
        actor: actor,
        action: ActivityAction.created,
        entityType: 'transaction',
        entityId: tx.id,
        summary: _txSummary(actor.displayName, 'added', tx, categoryName),
        amount: tx.amount,
      );
    }
    await batch.commit();
  }

  Future<void> addTransactions(List<Transaction> txs) async {
    // Firestore batches cap at 500 writes.
    for (var i = 0; i < txs.length; i += 400) {
      final chunk = txs.sublist(i, i + 400 > txs.length ? txs.length : i + 400);
      final batch = _refs.db.batch();
      for (final tx in chunk) {
        batch.set(_refs.transactions(householdId).doc(tx.id), tx.toMap());
      }
      await batch.commit();
    }
  }

  Future<void> updateTransaction(
    Transaction tx, {
    UserProfile? actor,
    String? categoryName,
    Transaction? previous,
  }) async {
    final batch = _refs.db.batch();
    batch.set(_refs.transactions(householdId).doc(tx.id), tx.toMap());
    // Keep goal balances in sync when a goal contribution changes.
    if (previous != null && previous.goalId != null && previous.isTransfer) {
      batch.update(_refs.goals(householdId).doc(previous.goalId!), {
        'savedAmount': FieldValue.increment(-previous.amount),
      });
    }
    if (tx.goalId != null && tx.isTransfer) {
      batch.update(_refs.goals(householdId).doc(tx.goalId!), {
        'savedAmount': FieldValue.increment(tx.amount),
      });
    }
    if (actor != null && !tx.isPrivate) {
      _logActivity(
        batch,
        actor: actor,
        action: ActivityAction.updated,
        entityType: 'transaction',
        entityId: tx.id,
        summary: _txSummary(actor.displayName, 'updated', tx, categoryName),
        amount: tx.amount,
      );
    }
    await batch.commit();
  }

  Future<void> deleteTransaction(Transaction tx, {UserProfile? actor, String? categoryName}) async {
    final batch = _refs.db.batch();
    batch.delete(_refs.transactions(householdId).doc(tx.id));
    if (tx.goalId != null && tx.isTransfer) {
      batch.update(_refs.goals(householdId).doc(tx.goalId!), {
        'savedAmount': FieldValue.increment(-tx.amount),
      });
    }
    if (actor != null && !tx.isPrivate) {
      _logActivity(
        batch,
        actor: actor,
        action: ActivityAction.deleted,
        entityType: 'transaction',
        entityId: tx.id,
        summary: _txSummary(actor.displayName, 'deleted', tx, categoryName),
        amount: tx.amount,
      );
    }
    await batch.commit();
  }

  Future<void> deleteTransactions(List<Transaction> txs) async {
    for (var i = 0; i < txs.length; i += 400) {
      final chunk = txs.sublist(i, i + 400 > txs.length ? txs.length : i + 400);
      final batch = _refs.db.batch();
      for (final tx in chunk) {
        batch.delete(_refs.transactions(householdId).doc(tx.id));
      }
      await batch.commit();
    }
  }

  // ---------------------------------------------------------------- budgets

  Future<void> saveBudget(Budget budget, {UserProfile? actor, bool isNew = false}) async {
    final batch = _refs.db.batch();
    batch.set(_refs.budgets(householdId).doc(budget.id), budget.toMap(), SetOptions(merge: true));
    if (actor != null && budget.isShared) {
      _logActivity(
        batch,
        actor: actor,
        action: isNew ? ActivityAction.created : ActivityAction.updated,
        entityType: 'budget',
        entityId: budget.id,
        summary:
            '${actor.displayName} ${isNew ? 'created' : 'updated'} budget "${budget.name}"',
        amount: budget.amount,
      );
    }
    await batch.commit();
  }

  Future<void> deleteBudget(Budget budget, {UserProfile? actor}) async {
    final batch = _refs.db.batch();
    batch.delete(_refs.budgets(householdId).doc(budget.id));
    if (actor != null && budget.isShared) {
      _logActivity(
        batch,
        actor: actor,
        action: ActivityAction.deleted,
        entityType: 'budget',
        entityId: budget.id,
        summary: '${actor.displayName} deleted budget "${budget.name}"',
      );
    }
    await batch.commit();
  }

  // ------------------------------------------------------------------ goals

  Future<void> saveGoal(Goal goal, {UserProfile? actor, bool isNew = false}) async {
    final batch = _refs.db.batch();
    batch.set(_refs.goals(householdId).doc(goal.id), goal.toMap(), SetOptions(merge: true));
    if (actor != null && goal.isShared) {
      _logActivity(
        batch,
        actor: actor,
        action: isNew ? ActivityAction.created : ActivityAction.updated,
        entityType: 'goal',
        entityId: goal.id,
        summary: '${actor.displayName} ${isNew ? 'created' : 'updated'} goal "${goal.name}"',
        amount: goal.targetAmount,
      );
    }
    await batch.commit();
  }

  Future<void> deleteGoal(Goal goal) => _refs.goals(householdId).doc(goal.id).delete();

  /// Adds money to a goal, optionally recording a transfer from [accountId].
  Future<void> contributeToGoal({
    required Goal goal,
    required double amount,
    required UserProfile actor,
    required String currency,
    String? accountId,
  }) async {
    final batch = _refs.db.batch();
    final now = DateTime.now();
    batch.update(_refs.goals(householdId).doc(goal.id), {
      'savedAmount': FieldValue.increment(amount),
      if (goal.savedAmount + amount >= goal.targetAmount) 'isCompleted': true,
    });
    if (accountId != null) {
      final id = newId('transactions');
      batch.set(
        _refs.transactions(householdId).doc(id),
        Transaction(
          id: id,
          type: TransactionType.transfer,
          amount: amount,
          currency: currency,
          originalAmount: amount,
          accountId: accountId,
          date: now,
          payee: 'Goal: ${goal.name}',
          note: 'Contribution to savings goal',
          isPrivate: !goal.isShared,
          createdBy: actor.uid,
          createdByName: actor.displayName,
          createdAt: now,
          updatedAt: now,
          goalId: goal.id,
        ).toMap(),
      );
    }
    if (goal.isShared) {
      _logActivity(
        batch,
        actor: actor,
        action: ActivityAction.updated,
        entityType: 'goal',
        entityId: goal.id,
        summary:
            '${actor.displayName} added ${Money.format(amount, currency)} to "${goal.name}"',
        amount: amount,
      );
    }
    await batch.commit();
  }

  // -------------------------------------------------------------- recurring

  Future<void> saveRecurring(RecurringRule rule) => _refs
      .recurring(householdId)
      .doc(rule.id)
      .set(rule.toMap(), SetOptions(merge: true));

  Future<void> deleteRecurring(String id) => _refs.recurring(householdId).doc(id).delete();

  /// Materialises due occurrences of every active rule. Runs inside a
  /// Firestore transaction per rule so two devices never double-post.
  Future<int> processRecurring(List<RecurringRule> rules, UserProfile actor, {DateTime? now}) async {
    final until = now ?? DateTime.now();
    var created = 0;
    for (final rule in rules) {
      if (!rule.isActive || rule.nextDue.isAfter(until)) continue;
      final ruleRef = _refs.recurring(householdId).doc(rule.id);
      final count = await _refs.db.runTransaction<int>((txn) async {
        final fresh = await txn.get(ruleRef);
        final data = fresh.data();
        if (data == null) return 0;
        final latest = RecurringRule.fromMap(fresh.id, data);
        if (!latest.isActive || latest.nextDue.isAfter(until)) return 0;
        final occurrences = latest.dueOccurrences(until);
        if (occurrences.isEmpty) return 0;
        var next = latest.nextDue;
        for (final when in occurrences) {
          if (latest.autoAdd) {
            final id = newId('transactions');
            final stamp = DateTime.now();
            txn.set(
              _refs.transactions(householdId).doc(id),
              Transaction(
                id: id,
                type: latest.type,
                amount: latest.amount,
                currency: latest.currency,
                originalAmount: latest.amount,
                accountId: latest.accountId,
                toAccountId: latest.toAccountId,
                categoryId: latest.categoryId,
                date: when,
                payee: latest.payee,
                note: latest.note,
                tags: latest.tags,
                isPrivate: latest.isPrivate,
                createdBy: latest.createdBy,
                createdByName: actor.uid == latest.createdBy ? actor.displayName : '',
                createdAt: stamp,
                updatedAt: stamp,
                recurringId: latest.id,
              ).toMap(),
            );
          }
          next = latest.nextAfter(when);
        }
        final finished = latest.endDate != null && next.isAfter(latest.endDate!);
        txn.update(ruleRef, {
          'nextDue': next,
          'lastGeneratedAt': until,
          if (finished) 'isActive': false,
        });
        return latest.autoAdd ? occurrences.length : 0;
      });
      created += count;
    }
    return created;
  }

  // --------------------------------------------------------------- activity

  void _logActivity(
    WriteBatch batch, {
    required UserProfile actor,
    required ActivityAction action,
    required String entityType,
    required String entityId,
    required String summary,
    double? amount,
  }) {
    final ref = _refs.activity(householdId).doc();
    batch.set(
      ref,
      ActivityEntry(
        id: ref.id,
        actorId: actor.uid,
        actorName: actor.displayName,
        action: action,
        entityType: entityType,
        entityId: entityId,
        summary: summary,
        at: DateTime.now(),
        amount: amount,
      ).toMap(),
    );
  }

  static String _txSummary(String actor, String verb, Transaction tx, String? categoryName) {
    final amount = Money.format(tx.amount, tx.currency);
    final what = switch (tx.type) {
      TransactionType.expense => 'expense',
      TransactionType.income => 'income',
      TransactionType.transfer => 'transfer',
    };
    final where = categoryName != null && categoryName.isNotEmpty
        ? ' in $categoryName'
        : (tx.payee.isNotEmpty ? ' at ${tx.payee}' : '');
    return '$actor $verb $what of $amount$where';
  }
}
