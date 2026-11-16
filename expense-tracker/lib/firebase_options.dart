// Placeholder Firebase configuration.
//
// Replace this file with your project's settings, either by running
//   flutterfire configure --platforms=web
// from the expense-tracker/ folder (it overwrites this file), or by pasting the
// values from Firebase console → Project settings → Your apps → Web app →
// "SDK setup and configuration" → Config into the `web` constant below.
// See GO_LIVE.md. Until then the app shows a setup screen instead of crashing.

import 'package:firebase_core/firebase_core.dart' show FirebaseOptions;
import 'package:flutter/foundation.dart' show kIsWeb;

class DefaultFirebaseOptions {
  static FirebaseOptions get currentPlatform {
    if (kIsWeb) return web;
    throw UnsupportedError('This app is configured for the web only.');
  }

  static const FirebaseOptions web = FirebaseOptions(
    apiKey: 'REPLACE_ME',
    appId: 'REPLACE_ME',
    messagingSenderId: 'REPLACE_ME',
    projectId: 'REPLACE_ME',
    authDomain: 'REPLACE_ME.firebaseapp.com',
    storageBucket: 'REPLACE_ME.firebasestorage.app',
  );
}
