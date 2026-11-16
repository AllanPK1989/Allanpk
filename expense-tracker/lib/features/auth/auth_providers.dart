import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:firebase_storage/firebase_storage.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:material_ui/material_ui.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../../data/firestore_refs.dart';
import '../../data/user_repository.dart';
import '../../services/app_settings.dart';
import '../../services/auth_service.dart';
import '../../services/currency_service.dart';
import '../../services/platform/notifier.dart';
import '../../services/storage_service.dart';

/// Overridden in main() with the real instance.
final sharedPrefsProvider = Provider<SharedPreferences>((ref) {
  throw UnimplementedError('sharedPrefsProvider must be overridden');
});

final firebaseAuthProvider = Provider<FirebaseAuth>((ref) => FirebaseAuth.instance);
final firestoreProvider = Provider<FirebaseFirestore>((ref) => FirebaseFirestore.instance);
final firestoreRefsProvider =
    Provider<FirestoreRefs>((ref) => FirestoreRefs(ref.watch(firestoreProvider)));

final authServiceProvider =
    Provider<AuthService>((ref) => AuthService(ref.watch(firebaseAuthProvider)));
final userRepositoryProvider =
    Provider<UserRepository>((ref) => UserRepository(ref.watch(firestoreRefsProvider)));
final storageServiceProvider =
    Provider<StorageService>((ref) => StorageService(FirebaseStorage.instance));
final currencyServiceProvider =
    Provider<CurrencyService>((ref) => CurrencyService(ref.watch(sharedPrefsProvider)));
final notifierProvider = Provider<AppNotifier>((ref) => AppNotifier());

/// Firebase user stream. `null` means signed out.
final authStateProvider = StreamProvider<User?>((ref) {
  return ref.watch(authServiceProvider).authStateChanges;
});

final currentUidProvider = Provider<String?>((ref) {
  return ref.watch(authStateProvider).value?.uid;
});

class AppSettingsNotifier extends Notifier<AppSettings> {
  @override
  AppSettings build() => AppSettings.load(ref.watch(sharedPrefsProvider));

  Future<void> update(AppSettings Function(AppSettings) change) async {
    state = change(state);
    await state.persist(ref.read(sharedPrefsProvider));
  }

  Future<void> setThemeMode(ThemeMode mode) => update((s) => s.copyWith(themeMode: mode));
  Future<void> setAccent(int index) => update((s) => s.copyWith(accentIndex: index));
  Future<void> setHideAmounts(bool hide) => update((s) => s.copyWith(hideAmounts: hide));
  Future<void> setBudgetAlerts(bool on) => update((s) => s.copyWith(budgetAlerts: on));
  Future<void> setBrowserNotifications(bool on) =>
      update((s) => s.copyWith(browserNotifications: on));
  Future<void> setCompactLayout(bool on) => update((s) => s.copyWith(compactLayout: on));
}

final appSettingsProvider =
    NotifierProvider<AppSettingsNotifier, AppSettings>(AppSettingsNotifier.new);
