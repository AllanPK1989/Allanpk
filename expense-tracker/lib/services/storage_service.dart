import 'dart:typed_data';

import 'package:firebase_storage/firebase_storage.dart';
import 'package:uuid/uuid.dart';

/// Receipt image uploads. Files live under the household so Storage rules can
/// mirror Firestore membership checks.
class StorageService {
  StorageService(this._storage);

  final FirebaseStorage _storage;

  Future<String> uploadReceipt({
    required String householdId,
    required String transactionId,
    required Uint8List bytes,
    String contentType = 'image/jpeg',
  }) async {
    final name = '${const Uuid().v4()}.jpg';
    final ref = _storage.ref('households/$householdId/receipts/$transactionId/$name');
    await ref.putData(bytes, SettableMetadata(contentType: contentType));
    return ref.getDownloadURL();
  }

  Future<void> deleteByUrl(String url) async {
    try {
      await _storage.refFromURL(url).delete();
    } on FirebaseException {
      // Already gone or permission denied: nothing more to do.
    }
  }
}
