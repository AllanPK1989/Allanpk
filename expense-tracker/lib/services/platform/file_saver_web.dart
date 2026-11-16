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
  // Revoke later so the browser has time to start the download, without
  // keeping the caller (and its busy indicator) waiting.
  Future<void>.delayed(const Duration(seconds: 30), () => web.URL.revokeObjectURL(url));
}
