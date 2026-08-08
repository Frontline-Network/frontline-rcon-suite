import 'dart:convert';

import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import 'models.dart';

abstract interface class PushRelayIdentityStore {
  Future<Map<String, String>?> readPushRelayIdentity();

  Future<void> writePushRelayIdentity({
    required String baseUrl,
    required String pushToken,
    required String handle,
    required String capability,
  });
}

class SecureConnectionStore implements PushRelayIdentityStore {
  SecureConnectionStore([FlutterSecureStorage? storage])
    : _storage = storage ?? const FlutterSecureStorage();

  final FlutterSecureStorage _storage;
  static const _connectionIndex = 'crcon.connections.v1';
  static const _pushRelayIdentity = 'crcon.push-relay.identity.v1';

  Future<List<ConnectionProfile>> readConnections() async {
    final raw = await _storage.read(key: _connectionIndex);
    if (raw == null || raw.isEmpty) return [];
    return (jsonDecode(raw) as List<dynamic>)
        .map(
          (value) => ConnectionProfile.fromJson(
            Map<String, dynamic>.from(value as Map),
          ),
        )
        .toList();
  }

  Future<void> saveConnection(
    ConnectionProfile profile, {
    required String accessToken,
    required String refreshToken,
  }) async {
    final connections = await readConnections();
    connections.removeWhere((item) => item.id == profile.id);
    connections.add(profile);
    await _storage.write(
      key: _connectionIndex,
      value: jsonEncode(connections.map((item) => item.toJson()).toList()),
    );
    await _storage.write(
      key: _tokenKey(profile.id, 'access'),
      value: accessToken,
    );
    await _storage.write(
      key: _tokenKey(profile.id, 'refresh'),
      value: refreshToken,
    );
  }

  Future<String?> accessToken(String connectionId) =>
      _storage.read(key: _tokenKey(connectionId, 'access'));

  Future<String?> refreshToken(String connectionId) =>
      _storage.read(key: _tokenKey(connectionId, 'refresh'));

  Future<void> replaceTokens(
    String connectionId, {
    required String accessToken,
    required String refreshToken,
  }) async {
    await _storage.write(
      key: _tokenKey(connectionId, 'access'),
      value: accessToken,
    );
    await _storage.write(
      key: _tokenKey(connectionId, 'refresh'),
      value: refreshToken,
    );
  }

  Future<void> removeConnection(String connectionId) async {
    final connections = await readConnections();
    connections.removeWhere((item) => item.id == connectionId);
    await _storage.write(
      key: _connectionIndex,
      value: jsonEncode(connections.map((item) => item.toJson()).toList()),
    );
    await _storage.delete(key: _tokenKey(connectionId, 'access'));
    await _storage.delete(key: _tokenKey(connectionId, 'refresh'));
  }

  Future<String?> readCacheKey() => _storage.read(key: 'crcon.cache.key.v1');

  Future<void> writeCacheKey(String value) =>
      _storage.write(key: 'crcon.cache.key.v1', value: value);

  Future<String?> readLanguage() => _storage.read(key: 'crcon.language.v1');

  Future<void> writeLanguage(String languageCode) =>
      _storage.write(key: 'crcon.language.v1', value: languageCode);

  @override
  Future<Map<String, String>?> readPushRelayIdentity() async {
    final raw = await _storage.read(key: _pushRelayIdentity);
    if (raw == null || raw.isEmpty) return null;
    try {
      final value = Map<String, dynamic>.from(jsonDecode(raw) as Map);
      final identity = value.map(
        (key, value) => MapEntry(key, value?.toString() ?? ''),
      );
      if ((identity['base_url'] ?? '').isEmpty ||
          (identity['push_token'] ?? '').isEmpty ||
          (identity['handle'] ?? '').isEmpty ||
          (identity['capability'] ?? '').isEmpty) {
        return null;
      }
      return identity;
    } on FormatException {
      return null;
    } on TypeError {
      return null;
    }
  }

  @override
  Future<void> writePushRelayIdentity({
    required String baseUrl,
    required String pushToken,
    required String handle,
    required String capability,
  }) => _storage.write(
    key: _pushRelayIdentity,
    value: jsonEncode({
      'base_url': baseUrl,
      'push_token': pushToken,
      'handle': handle,
      'capability': capability,
    }),
  );

  String _tokenKey(String connectionId, String kind) =>
      'crcon.$connectionId.$kind.v1';
}
