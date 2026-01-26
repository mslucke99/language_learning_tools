import 'dart:io';
import 'package:google_sign_in/google_sign_in.dart';
import 'package:googleapis/drive/v3.dart' as drive;
import 'package:extension_google_sign_in_as_googleapis_auth/extension_google_sign_in_as_googleapis_auth.dart';
import 'package:path_provider/path_provider.dart';
import 'package:path/path.dart' as path;

class DriveService {
  final GoogleSignIn _googleSignIn = GoogleSignIn(
    scopes: [drive.DriveApi.driveFileScope],
  );

  drive.DriveApi? _driveApi;
  GoogleSignInAccount? _currentUser;

  Future<GoogleSignInAccount?> signIn() async {
    try {
      _currentUser = await _googleSignIn.signIn();
      if (_currentUser != null) {
        final httpClient = await _googleSignIn.authenticatedClient();
        if (httpClient != null) {
          _driveApi = drive.DriveApi(httpClient);
        }
      }
      return _currentUser;
    } catch (e) {
      print('Sign in failed: $e');
      return null;
    }
  }

  Future<void> signOut() async {
    await _googleSignIn.signOut();
    _currentUser = null;
    _driveApi = null;
  }

  Future<String?> _getFolderId(String folderName) async {
    if (_driveApi == null) return null;

    final fileList = await _driveApi!.files.list(
      q: "mimeType = 'application/vnd.google-apps.folder' and name = '$folderName' and trashed = false",
      $fields: "files(id, name)",
    );

    if (fileList.files != null && fileList.files!.isNotEmpty) {
      return fileList.files!.first.id;
    }
    return null; // Folder not found
  }

  Future<void> downloadDatabase() async {
    if (_driveApi == null) throw Exception('Not signed in');

    // 1. Find App Folder
    final folderId = await _getFolderId('LanguageLearningSuite');
    if (folderId == null) {
      throw Exception('Cloud folder not found. Please sync from PC first.');
    }

    // 2. Find Database File
    final fileList = await _driveApi!.files.list(
      q: "'$folderId' in parents and name = 'flashcards.db' and trashed = false",
      $fields: "files(id, name)",
    );

    if (fileList.files == null || fileList.files!.isEmpty) {
      throw Exception('flashcards.db not found in cloud.');
    }

    final fileId = fileList.files!.first.id!;

    // 3. Download Content
    final media =
        await _driveApi!.files.get(
              fileId,
              downloadOptions: drive.DownloadOptions.fullMedia,
            )
            as drive.Media;

    // 4. Save to Local App Documents
    final appDir = await getApplicationDocumentsDirectory();
    final dbPath = path.join(appDir.path, 'flashcards.db');
    final saveFile = File(dbPath);

    final List<int> dataStore = [];
    await media.stream.listen((data) {
      dataStore.addAll(data);
    }).asFuture();

    await saveFile.writeAsBytes(dataStore);
    print('Database downloaded to $dbPath');
  }

  Future<void> uploadDatabase() async {
    if (_driveApi == null) throw Exception('Not signed in');

    final appDir = await getApplicationDocumentsDirectory();
    final dbPath = path.join(appDir.path, 'flashcards.db');
    final localFile = File(dbPath);

    if (!await localFile.exists()) {
      throw Exception('No local database found to upload.');
    }

    // 1. Find App Folder
    var folderId = await _getFolderId('LanguageLearningSuite');
    // Note: We assume folder exists because PC creates it.
    // If we want mobile to create it, we'd add logic here.
    if (folderId == null) {
      throw Exception('Cloud folder not found.');
    }

    // 2. Find Existing File to Update
    String? existingFileId;
    final fileList = await _driveApi!.files.list(
      q: "'$folderId' in parents and name = 'flashcards.db' and trashed = false",
      $fields: "files(id, name)",
    );

    if (fileList.files != null && fileList.files!.isNotEmpty) {
      existingFileId = fileList.files!.first.id;
    }

    // 3. Upload/Update
    final media = drive.Media(localFile.openRead(), localFile.lengthSync());

    if (existingFileId != null) {
      // Update existing
      await _driveApi!.files.update(
        drive.File(),
        existingFileId,
        uploadMedia: media,
      );
    } else {
      // Create new
      await _driveApi!.files.create(
        drive.File(name: 'flashcards.db', parents: [folderId]),
        uploadMedia: media,
      );
    }
    print('Database uploaded successfully.');
  }
}
