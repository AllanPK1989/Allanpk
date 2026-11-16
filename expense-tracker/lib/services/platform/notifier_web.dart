import 'dart:js_interop';
import 'dart:js_interop_unsafe';

import 'package:web/web.dart' as web;

bool get isSupported {
  try {
    return web.window.hasProperty('Notification'.toJS).toDart;
  } catch (_) {
    return false;
  }
}

bool get isGranted => isSupported && web.Notification.permission == 'granted';

Future<bool> requestPermission() async {
  if (!isSupported) return false;
  if (web.Notification.permission == 'granted') return true;
  if (web.Notification.permission == 'denied') return false;
  final result = await web.Notification.requestPermission().toDart;
  return result.toDart == 'granted';
}

Future<void> show(String title, String body) async {
  if (!isGranted) return;
  web.Notification(title, web.NotificationOptions(body: body));
}
