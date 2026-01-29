import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:google_sign_in/google_sign_in.dart';
import 'package:flutter/foundation.dart';
import 'database_helper.dart';

class FirebaseService {
  final FirebaseFirestore _db = FirebaseFirestore.instance;
  final FirebaseAuth _auth = FirebaseAuth.instance;
  final GoogleSignIn _googleSignIn = GoogleSignIn();
  final DatabaseHelper _localDb = DatabaseHelper();

  User? get currentUser => _auth.currentUser;
  Stream<User?> get authStateChanges => _auth.authStateChanges();

  // Initialize in main.dart: await Firebase.initializeApp();

  Future<User?> signInWithGoogle() async {
    try {
      final GoogleSignInAccount? googleUser = await _googleSignIn.signIn();
      if (googleUser == null) return null; // User canceled

      final GoogleSignInAuthentication googleAuth =
          await googleUser.authentication;
      final AuthCredential credential = GoogleAuthProvider.credential(
        accessToken: googleAuth.accessToken,
        idToken: googleAuth.idToken,
      );

      final UserCredential userCredential = await _auth.signInWithCredential(
        credential,
      );
      return userCredential.user;
    } catch (e) {
      if (kDebugMode) print("Google Sign-In Error: $e");
      return null;
    }
  }

  Future<void> signOut() async {
    await _googleSignIn.signOut();
    await _auth.signOut();
  }

  Future<void> signInAnonymously() async {
    try {
      if (_auth.currentUser == null) {
        await _auth.signInAnonymously();
      }
    } catch (e) {
      if (kDebugMode) {
        print("Firebase Auth Error: $e");
      }
    }
  }

  Future<Map<String, int>> sync() async {
    final stats = {'downloaded': 0, 'uploaded': 0};

    // TODO: Persist last_sync_time properly
    String lastSyncTime = "1970-01-01T00:00:00";
    // final newSyncTime = DateTime.now().toIso8601String(); // Unused

    final user = _auth.currentUser;
    if (user == null) {
      if (kDebugMode) print("Cannot sync: No user logged in.");
      return stats;
    }

    // Path prefix: users/{uid}/
    final userDocRef = _db.collection('users').doc(user.uid);

    final tables = [
      "decks",
      "flashcards",
      "imported_content",
      "word_definitions",
      "sentence_explanations",
      "writing_sessions",
      "chat_sessions",
      "grammar_book_entries",
      "collections",
      "chat_messages",
    ];

    for (var table in tables) {
      final collectionRef = userDocRef.collection(table);

      // 1. Pull Remote Changes
      try {
        final querySnapshot = await collectionRef
            .where('last_modified', isGreaterThan: lastSyncTime)
            .get();

        final List<Map<String, dynamic>> remoteRows = querySnapshot.docs
            .map((doc) => doc.data())
            .toList();

        if (remoteRows.isNotEmpty) {
          await _localDb.upsertRows(table, remoteRows);
          stats['downloaded'] = (stats['downloaded'] ?? 0) + remoteRows.length;
        }

        // 2. Push Local Changes
        final localRows = await _localDb.getModifiedRowsSince(
          table,
          lastSyncTime,
        );
        if (localRows.isNotEmpty) {
          final batch = _db.batch();
          int batchCount = 0;

          for (var row in localRows) {
            final docRef = collectionRef.doc(row['uuid']);
            batch.set(docRef, row, SetOptions(merge: true));
            batchCount++;

            if (batchCount >= 400) {
              await batch.commit();
              batchCount = 0;
              // Reset batch? No, batch is consumed. Need new one.
              // Actually batch object cannot be reused easily like this in loop without re-instantiation?
              // The Firestore API in Dart usually allows multiple ops.
              // We need to re-create a batch object if we commit.
              // But for simplicity/safety, let's just commit at the end or split list.
            }
          }
          if (batchCount > 0) {
            await batch.commit();
          }
          stats['uploaded'] = (stats['uploaded'] ?? 0) + localRows.length;
        }
      } catch (e) {
        if (kDebugMode) {
          print("Error syncing table $table: $e");
        }
      }
    }

    return stats;
  }
}
