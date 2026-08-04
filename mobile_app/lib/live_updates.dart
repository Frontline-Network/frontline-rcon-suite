import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'crcon_api.dart';
import 'models.dart';
import 'secure_store.dart';

class CrconLiveUpdates {
  CrconLiveUpdates(this.profile, this.store);

  final ConnectionProfile profile;
  final SecureConnectionStore store;
  bool _stopped = false;
  WebSocket? _socket;

  Future<void> start(
    void Function(Map<String, dynamic> incident) onIncident,
  ) async {
    int? cursor;
    var retrySeconds = 1;
    while (!_stopped) {
      try {
        final api = CrconApi(profile, store);
        if (cursor == null) {
          final bootstrap = await api.bootstrap();
          final snapshot = await api.listIncidents();
          if (snapshot.isNotEmpty) onIncident(snapshot.first);
          cursor = (bootstrap['incident_cursor'] as num).toInt();
        } else {
          // Refresh the snapshot and an expired access token before reconnecting.
          final snapshot = await api.listIncidents();
          if (snapshot.isNotEmpty) onIncident(snapshot.first);
        }
        final accessToken = await store.accessToken(profile.id);
        if (accessToken == null) return;
        final base = Uri.parse(profile.baseUrl);
        final prefix = base.path.endsWith('/')
            ? base.path.substring(0, base.path.length - 1)
            : base.path;
        final uri = base.replace(
          scheme: base.scheme == 'https' ? 'wss' : 'ws',
          path: '$prefix/ws/mobile/v1/incidents',
          query: null,
          fragment: null,
        );
        _socket = await WebSocket.connect(
          uri.toString(),
          headers: {'Authorization': 'Bearer $accessToken'},
        );
        _socket!.add(jsonEncode({'cursor': cursor}));
        retrySeconds = 1;
        await for (final raw in _socket!) {
          if (_stopped) return;
          final message = jsonDecode(raw.toString()) as Map<String, dynamic>;
          if (message['cursor'] is num) {
            cursor = (message['cursor'] as num).toInt();
          }
          for (final item
              in message['incidents'] as List<dynamic>? ?? const []) {
            onIncident(Map<String, dynamic>.from(item as Map));
          }
        }
      } catch (_) {
        if (_stopped) return;
      } finally {
        _socket = null;
      }
      await Future<void>.delayed(Duration(seconds: retrySeconds));
      retrySeconds = (retrySeconds * 2).clamp(1, 30);
    }
  }

  Future<void> dispose() async {
    _stopped = true;
    await _socket?.close();
  }
}
