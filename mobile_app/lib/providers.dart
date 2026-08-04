import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'crcon_api.dart';
import 'incident_cache.dart';
import 'models.dart';
import 'secure_store.dart';

final secureStoreProvider = Provider((ref) => SecureConnectionStore());

final cacheProvider = FutureProvider<IncidentCache>((ref) async {
  final cache = await IncidentCache.open(ref.read(secureStoreProvider));
  ref.onDispose(cache.close);
  return cache;
});

final connectionsProvider = FutureProvider<List<ConnectionProfile>>(
  (ref) => ref.read(secureStoreProvider).readConnections(),
);

class LiveIncidentUpdate {
  const LiveIncidentUpdate({
    required this.connectionId,
    required this.incident,
  });

  final String connectionId;
  final Map<String, dynamic> incident;
}

final liveIncidentUpdateProvider = StateProvider<LiveIncidentUpdate?>(
  (ref) => null,
);

final inboxProvider = FutureProvider<List<AdminIncident>>((ref) async {
  final profiles = await ref.watch(connectionsProvider.future);
  final cache = await ref.watch(cacheProvider.future);
  final incidents = <AdminIncident>[];
  for (final profile in profiles) {
    try {
      final payloads = await CrconApi(
        profile,
        ref.read(secureStoreProvider),
      ).listIncidents();
      await cache.replaceConnectionIncidents(profile.id, payloads);
      incidents.addAll(
        payloads.map((item) => AdminIncident.fromJson(item, profile.id)),
      );
    } catch (_) {
      incidents.addAll(await cache.readConnectionIncidents(profile.id));
    }
  }
  incidents.sort((a, b) => b.updatedAt.compareTo(a.updatedAt));
  return incidents;
});
