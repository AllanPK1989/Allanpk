import 'notifier_io.dart' if (dart.library.js_interop) 'notifier_web.dart' as impl;

/// Browser notifications for budget alerts. No-op where unsupported.
class AppNotifier {
  Future<bool> requestPermission() => impl.requestPermission();
  bool get isGranted => impl.isGranted;
  bool get isSupported => impl.isSupported;
  Future<void> show(String title, String body) => impl.show(title, body);
}
