import 'package:firebase_core/firebase_core.dart' show FirebaseOptions;

import '../../firebase_options.dart';

/// Kept separate from `firebase_options.dart` so that `flutterfire configure`
/// can overwrite that file without breaking the app.

/// `--dart-define=USE_EMULATORS=true` points the app at the local Firebase
/// emulator suite instead of a real project (see SETUP.md).
const bool kUseEmulators = bool.fromEnvironment('USE_EMULATORS');
const String kEmulatorHost = String.fromEnvironment('EMULATOR_HOST', defaultValue: 'localhost');

/// `--dart-define=APPLE_SIGN_IN=true` shows the "Sign in with Apple" button.
/// Leave it off until Apple is configured in Firebase (see GO_LIVE.md).
const bool kAppleSignInEnabled = bool.fromEnvironment('APPLE_SIGN_IN');

/// Options used with the emulators; any project id starting with `demo-` works.
const FirebaseOptions kEmulatorOptions = FirebaseOptions(
  apiKey: 'demo-api-key',
  appId: '1:000000000000:web:demo',
  messagingSenderId: '000000000000',
  projectId: 'demo-expense-budget',
  authDomain: 'demo-expense-budget.firebaseapp.com',
  storageBucket: 'demo-expense-budget.appspot.com',
);

/// True once `firebase_options.dart` holds real project settings.
bool get isFirebaseConfigured {
  try {
    final o = DefaultFirebaseOptions.currentPlatform;
    return !o.apiKey.contains('REPLACE_ME') && !o.projectId.contains('REPLACE_ME');
  } catch (_) {
    return false;
  }
}
