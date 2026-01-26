import 'dart:convert';
import 'dart:io';
import 'dart:math';
import 'package:crypto/crypto.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:http/http.dart' as http;
import 'package:url_launcher/url_launcher.dart';
import 'package:app_links/app_links.dart';
import 'dart:async';
import 'package:path_provider/path_provider.dart';
import 'package:path/path.dart' as p;

class DropboxService {
  static const String clientId = 'ax4jmmkstls02hc';
  static const String redirectUri = 'languagelearning://auth_callback';

  final _storage = const FlutterSecureStorage();
  String? _accessToken;
  String? _refreshToken;
  String? _codeVerifier;

  StreamSubscription? _sub;

  // --- Auth Flow ---

  /// Generate a random string for PKCE
  String _generateRandomString(int length) {
    const charset =
        'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-._~';
    final random = Random.secure();
    return List.generate(
      length,
      (_) => charset[random.nextInt(charset.length)],
    ).join();
  }

  /// Create PKCE Code Challenge from Verifier
  String _generateCodeChallenge(String verifier) {
    var bytes = utf8.encode(verifier);
    var digest = sha256.convert(bytes);
    return base64Url.encode(digest.bytes).replaceAll('=', '');
  }

  Future<void> login() async {
    _codeVerifier = _generateRandomString(64);
    final challenge = _generateCodeChallenge(_codeVerifier!);

    final url = Uri.https('www.dropbox.com', '/oauth2/authorize', {
      'client_id': clientId,
      'response_type': 'code',
      'redirect_uri': redirectUri,
      'code_challenge': challenge,
      'code_challenge_method': 'S256',
      'token_access_type': 'offline',
    });

    if (await canLaunchUrl(url)) {
      await launchUrl(url, mode: LaunchMode.externalApplication);
    } else {
      throw 'Could not launch $url';
    }

    // Listen for the deep link callback
    _sub = AppLinks().uriLinkStream.listen(
      (Uri? uri) async {
        if (uri != null &&
            uri.scheme == 'languagelearning' &&
            uri.host == 'auth_callback') {
          final code = uri.queryParameters['code'];
          if (code != null) {
            await _exchangeCodeForToken(code);
          }
          _sub?.cancel();
        }
      },
      onError: (err) {
        print('Deep link error: $err');
      },
    );
  }

  Future<void> _exchangeCodeForToken(String code) async {
    final url = Uri.https('api.dropboxapi.com', '/oauth2/token');

    final response = await http.post(
      url,
      body: {
        'code': code,
        'grant_type': 'authorization_code',
        'client_id': clientId,
        'code_verifier': _codeVerifier,
        'redirect_uri': redirectUri,
      },
    );

    if (response.statusCode == 200) {
      final data = json.decode(response.body);
      _accessToken = data['access_token'];
      _refreshToken = data['refresh_token'];

      await _storage.write(key: 'dropbox_refresh_token', value: _refreshToken);
    } else {
      throw 'Failed to exchange token: ${response.body}';
    }
  }

  Future<bool> init() async {
    _refreshToken = await _storage.read(key: 'dropbox_refresh_token');
    if (_refreshToken != null) {
      // Try to get a fresh access token
      try {
        await refreshAccessToken();
        return true;
      } catch (e) {
        print('Initial token refresh failed: $e');
        return false;
      }
    }
    return false;
  }

  Future<void> refreshAccessToken() async {
    if (_refreshToken == null) throw 'No refresh token available';

    final url = Uri.https('api.dropboxapi.com', '/oauth2/token');
    final response = await http.post(
      url,
      body: {
        'grant_type': 'refresh_token',
        'refresh_token': _refreshToken,
        'client_id': clientId,
      },
    );

    if (response.statusCode == 200) {
      final data = json.decode(response.body);
      _accessToken = data['access_token'];
    } else {
      throw 'Failed to refresh token: ${response.body}';
    }
  }

  Future<void> logout() async {
    await _storage.delete(key: 'dropbox_refresh_token');
    _accessToken = null;
    _refreshToken = null;
  }

  // --- File Operations ---

  Future<void> uploadDatabase(String localPath) async {
    if (_accessToken == null) await refreshAccessToken();

    final file = File(localPath);
    final bytes = await file.readAsBytes();

    final url = Uri.https('content.dropboxapi.com', '/2/files/upload');

    final response = await http.post(
      url,
      headers: {
        'Authorization': 'Bearer $_accessToken',
        'Dropbox-API-Arg': json.encode({
          'path': '/flashcards.db',
          'mode': 'overwrite',
          'mute': true,
        }),
        'Content-Type': 'application/octet-stream',
      },
      body: bytes,
    );

    if (response.statusCode != 200) {
      if (response.statusCode == 401) {
        await refreshAccessToken();
        return uploadDatabase(localPath); // Retry once
      }
      throw 'Upload failed: ${response.body}';
    }
  }

  Future<String> downloadDatabase() async {
    if (_accessToken == null) await refreshAccessToken();

    final url = Uri.https('content.dropboxapi.com', '/2/files/download');

    final response = await http.post(
      url,
      headers: {
        'Authorization': 'Bearer $_accessToken',
        'Dropbox-API-Arg': json.encode({'path': '/flashcards.db'}),
      },
    );

    if (response.statusCode == 200) {
      final directory = await getTemporaryDirectory();
      final path = p.join(directory.path, 'temp_cloud_flashcards.db');
      final file = File(path);
      await file.writeAsBytes(response.bodyBytes);
      return path;
    } else {
      if (response.statusCode == 401) {
        await refreshAccessToken();
        return downloadDatabase(); // Retry once
      }
      throw 'Download failed: ${response.body}';
    }
  }

  Future<void> createCloudCheckpoint(String localPath) async {
    if (_accessToken == null) await refreshAccessToken();

    final file = File(localPath);
    final bytes = await file.readAsBytes();

    final timestamp = DateTime.now()
        .toIso8601String()
        .replaceAll(':', '')
        .replaceAll('.', '');
    final checkpointPath = '/checkpoints/flashcards_$timestamp.db';

    final url = Uri.https('content.dropboxapi.com', '/2/files/upload');

    final response = await http.post(
      url,
      headers: {
        'Authorization': 'Bearer $_accessToken',
        'Dropbox-API-Arg': json.encode({
          'path': checkpointPath,
          'mode': 'add',
          'mute': true,
        }),
        'Content-Type': 'application/octet-stream',
      },
      body: bytes,
    );

    if (response.statusCode != 200) {
      if (response.statusCode == 401) {
        await refreshAccessToken();
        return createCloudCheckpoint(localPath);
      }
      throw 'Cloud checkpoint failed: ${response.body}';
    }
  }

  bool get isAuthenticated => _accessToken != null;
}
