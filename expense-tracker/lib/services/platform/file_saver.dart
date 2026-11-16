import 'dart:typed_data';

import 'file_saver_io.dart' if (dart.library.js_interop) 'file_saver_web.dart' as impl;

/// Hands a generated file to the user: a browser download on the web, the
/// system share sheet elsewhere.
Future<void> saveFile({
  required Uint8List bytes,
  required String filename,
  required String mimeType,
}) =>
    impl.saveFile(bytes: bytes, filename: filename, mimeType: mimeType);
