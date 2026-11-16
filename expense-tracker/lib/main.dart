import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_storage/firebase_storage.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:material_ui/material_ui.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'app.dart';
import 'features/auth/auth_providers.dart';
import 'features/setup/firebase_setup_screen.dart';
import 'firebase_options.dart';

/// `flutter run -d chrome --dart-define=USE_EMULATORS=true` points the app at
/// the local Firebase emulator suite (see SETUP.md) instead of a real project.
const bool kUseEmulators = bool.fromEnvironment('USE_EMULATORS');
const String kEmulatorHost = String.fromEnvironment('EMULATOR_HOST', defaultValue: 'localhost');

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final prefs = await SharedPreferences.getInstance();

  if (!kUseEmulators && !DefaultFirebaseOptions.isConfigured) {
    runApp(const FirebaseSetupApp());
    return;
  }

  await Firebase.initializeApp(
    options: kUseEmulators ? DefaultFirebaseOptions.emulator : DefaultFirebaseOptions.currentPlatform,
  );
  if (kUseEmulators) {
    await FirebaseAuth.instance.useAuthEmulator(kEmulatorHost, 9099);
    FirebaseFirestore.instance.useFirestoreEmulator(kEmulatorHost, 8080);
    await FirebaseStorage.instance.useStorageEmulator(kEmulatorHost, 9199);
  }
  // Offline-first: Firestore keeps a local cache (IndexedDB in the browser)
  // so the app keeps working without a connection and syncs later.
  FirebaseFirestore.instance.settings = const Settings(
    persistenceEnabled: true,
    cacheSizeBytes: Settings.CACHE_SIZE_UNLIMITED,
  );

  runApp(
    ProviderScope(
      overrides: [sharedPrefsProvider.overrideWithValue(prefs)],
      child: const ExpenseBudgetApp(),
    ),
  );
}
