import 'package:firebase_auth/firebase_auth.dart';

/// Thin wrapper over FirebaseAuth that normalises error messages. Social
/// sign-in uses Firebase's popup flow, which needs no extra SDKs on the web.
class AuthService {
  AuthService(this._auth);

  final FirebaseAuth _auth;

  Stream<User?> get authStateChanges => _auth.authStateChanges();
  User? get currentUser => _auth.currentUser;

  Future<UserCredential> signInWithEmail(String email, String password) async {
    try {
      return await _auth.signInWithEmailAndPassword(email: email.trim(), password: password);
    } on FirebaseAuthException catch (e) {
      throw AuthFailure.fromCode(e.code);
    }
  }

  Future<UserCredential> signUpWithEmail(String name, String email, String password) async {
    try {
      final cred = await _auth.createUserWithEmailAndPassword(
        email: email.trim(),
        password: password,
      );
      await cred.user?.updateDisplayName(name.trim());
      await cred.user?.reload();
      return cred;
    } on FirebaseAuthException catch (e) {
      throw AuthFailure.fromCode(e.code);
    }
  }

  Future<void> sendPasswordReset(String email) async {
    try {
      await _auth.sendPasswordResetEmail(email: email.trim());
    } on FirebaseAuthException catch (e) {
      throw AuthFailure.fromCode(e.code);
    }
  }

  Future<UserCredential> signInWithGoogle() => _popup(GoogleAuthProvider()..addScope('email'));

  Future<UserCredential> signInWithApple() => _popup(
        OAuthProvider('apple.com')
          ..addScope('email')
          ..addScope('name'),
      );

  Future<UserCredential> _popup(AuthProvider provider) async {
    try {
      return await _auth.signInWithPopup(provider);
    } on FirebaseAuthException catch (e) {
      if (e.code == 'popup-closed-by-user' || e.code == 'cancelled-popup-request') {
        throw const AuthFailure('Sign-in cancelled');
      }
      throw AuthFailure.fromCode(e.code);
    }
  }

  Future<void> updateDisplayName(String name) async {
    await _auth.currentUser?.updateDisplayName(name.trim());
    await _auth.currentUser?.reload();
  }

  Future<void> changePassword(String newPassword) async {
    try {
      await _auth.currentUser?.updatePassword(newPassword);
    } on FirebaseAuthException catch (e) {
      throw AuthFailure.fromCode(e.code);
    }
  }

  Future<void> signOut() => _auth.signOut();

  Future<void> deleteAccount() async {
    try {
      await _auth.currentUser?.delete();
    } on FirebaseAuthException catch (e) {
      throw AuthFailure.fromCode(e.code);
    }
  }
}

class AuthFailure implements Exception {
  const AuthFailure(this.message);

  final String message;

  factory AuthFailure.fromCode(String code) {
    return AuthFailure(switch (code) {
      'invalid-email' => 'That email address does not look right.',
      'user-disabled' => 'This account has been disabled.',
      'user-not-found' || 'wrong-password' || 'invalid-credential' =>
        'Incorrect email or password.',
      'email-already-in-use' => 'An account already exists for this email.',
      'weak-password' => 'Please choose a stronger password (at least 6 characters).',
      'too-many-requests' => 'Too many attempts. Please try again in a moment.',
      'network-request-failed' => 'No internet connection.',
      'requires-recent-login' => 'Please sign in again to perform this action.',
      'account-exists-with-different-credential' =>
        'This email is already linked to another sign-in method.',
      'popup-blocked' => 'Your browser blocked the sign-in window. Allow pop-ups and retry.',
      'operation-not-allowed' =>
        'This sign-in method is not enabled in the Firebase console yet.',
      'unauthorized-domain' =>
        'This domain is not authorised for sign-in. Add it under Authentication → Settings.',
      _ => 'Authentication failed ($code).',
    });
  }

  @override
  String toString() => message;
}
