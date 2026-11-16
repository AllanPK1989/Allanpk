import 'dart:js_interop';
import 'dart:typed_data';

import 'package:web/web.dart' as web;

Future<void> saveFile({
  required Uint8List bytes,
  required String filename,
  required String mimeType,
}) async {
  final blob = web.Blob(
    <JSAny>[bytes.toJS].toJS,
    web.BlobPropertyBag(type: mimeType),
  );
  final url = web.URL.createObjectURL(blob);
  final anchor = web.HTMLAnchorElement()
    ..href = url
    ..download = filename
    ..style.display = 'none';
  web.document.body?.append(anchor);
  anchor.click();
  anchor.remove();
  // Give the browser a moment to start the download before revoking.
  await Future<void>.delayed(const Duration(seconds: 2));
  web.URL.revokeObjectURL(url);
}
