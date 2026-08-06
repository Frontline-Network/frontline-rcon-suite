import 'models.dart';
import 'secure_store.dart';

/// Browser cache deliberately lives in memory only.
///
/// Native clients use SQLCipher for their encrypted offline cache. Browsers do
/// not provide an equivalent OS-keystore-backed database, so the PWA never
/// persists incident payloads or queues writes while offline.
class IncidentCache {
  IncidentCache._();

  final Map<String, List<Map<String, dynamic>>> _incidents = {};

  static Future<IncidentCache> open(SecureConnectionStore _) async =>
      IncidentCache._();

  Future<void> replaceConnectionIncidents(
    String connectionId,
    List<Map<String, dynamic>> incidents,
  ) async {
    _incidents[connectionId] = incidents
        .map((incident) => Map<String, dynamic>.from(incident))
        .toList(growable: false);
  }

  Future<List<AdminIncident>> readConnectionIncidents(
    String connectionId,
  ) async => (_incidents[connectionId] ?? const [])
      .map(
        (incident) =>
            AdminIncident.fromJson(incident, connectionId, stale: true),
      )
      .toList(growable: false);

  Future<void> deleteConnection(String connectionId) async {
    _incidents.remove(connectionId);
  }

  Future<void> close() async {}
}
