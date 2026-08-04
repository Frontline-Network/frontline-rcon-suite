import 'dart:convert';

import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import 'models.dart';

class SecureConnectionStore {
  SecureConnectionStore([FlutterSecureStorage? storage])
    : _storage = storage ?? const FlutterSecureStorage();

  final FlutterSecureStorage _storage;
  static const _connectionIndex = 'crcon.connections.v1';

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

  String _tokenKey(String connectionId, String kind) =>
      'crcon.$connectionId.$kind.v1';
}
