// Placeholder Firebase configuration.
//
// Run `flutterfire configure` from the project root to replace this file with
// the real options for your Firebase project (see SETUP.md). Until then the
// app shows a setup screen instead of crashing.

import 'package:firebase_core/firebase_core.dart' show FirebaseOptions;
import 'package:flutter/foundation.dart' show defaultTargetPlatform, kIsWeb, TargetPlatform;

class DefaultFirebaseOptions {
  static const String _placeholder = 'REPLACE_ME';

  static bool get isConfigured => !currentPlatform.apiKey.startsWith(_placeholder);

  static FirebaseOptions get currentPlatform {
    if (kIsWeb) return web;
    switch (defaultTargetPlatform) {
      case TargetPlatform.android:
        return android;
      case TargetPlatform.iOS:
        return ios;
      default:
        return android;
    }
  }

  /// Used only with `--dart-define=USE_EMULATORS=true`; the emulator suite
  /// accepts any project id prefixed with `demo-`.
  static const FirebaseOptions emulator = FirebaseOptions(
    apiKey: 'demo-api-key',
    appId: '1:000000000000:web:demo',
    messagingSenderId: '000000000000',
    projectId: 'demo-expense-budget',
    authDomain: 'demo-expense-budget.firebaseapp.com',
    storageBucket: 'demo-expense-budget.appspot.com',
  );

  static const FirebaseOptions web = FirebaseOptions(
    apiKey: '${_placeholder}_WEB_API_KEY',
    appId: '1:000000000000:web:0000000000000000000000',
    messagingSenderId: '000000000000',
    projectId: 'your-firebase-project',
    authDomain: 'your-firebase-project.firebaseapp.com',
    storageBucket: 'your-firebase-project.appspot.com',
  );

  static const FirebaseOptions android = FirebaseOptions(
    apiKey: '${_placeholder}_ANDROID_API_KEY',
    appId: '1:000000000000:android:0000000000000000000000',
    messagingSenderId: '000000000000',
    projectId: 'your-firebase-project',
    storageBucket: 'your-firebase-project.appspot.com',
  );

  static const FirebaseOptions ios = FirebaseOptions(
    apiKey: '${_placeholder}_IOS_API_KEY',
    appId: '1:000000000000:ios:0000000000000000000000',
    messagingSenderId: '000000000000',
    projectId: 'your-firebase-project',
    storageBucket: 'your-firebase-project.appspot.com',
    iosBundleId: 'com.allanpk.expensebudgetmanager',
  );
}
