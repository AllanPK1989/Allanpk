import 'package:cloud_firestore/cloud_firestore.dart';

/// Central place for Firestore collection paths so rules, indexes and code
/// never drift apart.
class FirestoreRefs {
  FirestoreRefs(this.db);

  final FirebaseFirestore db;

  CollectionReference<Map<String, dynamic>> get users => db.collection('users');
  CollectionReference<Map<String, dynamic>> get households => db.collection('households');
  CollectionReference<Map<String, dynamic>> get invites => db.collection('invites');

  DocumentReference<Map<String, dynamic>> user(String uid) => users.doc(uid);
  DocumentReference<Map<String, dynamic>> household(String hid) => households.doc(hid);

  CollectionReference<Map<String, dynamic>> accounts(String hid) =>
      household(hid).collection('accounts');
  CollectionReference<Map<String, dynamic>> categories(String hid) =>
      household(hid).collection('categories');
  CollectionReference<Map<String, dynamic>> transactions(String hid) =>
      household(hid).collection('transactions');
  CollectionReference<Map<String, dynamic>> budgets(String hid) =>
      household(hid).collection('budgets');
  CollectionReference<Map<String, dynamic>> goals(String hid) =>
      household(hid).collection('goals');
  CollectionReference<Map<String, dynamic>> recurring(String hid) =>
      household(hid).collection('recurring');
  CollectionReference<Map<String, dynamic>> activity(String hid) =>
      household(hid).collection('activity');
}
