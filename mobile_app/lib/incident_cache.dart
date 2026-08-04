import 'dart:convert';
import 'dart:io';
import 'dart:math';

import 'package:drift/drift.dart';
import 'package:drift/native.dart';
import 'package:path/path.dart' as path;
import 'package:path_provider/path_provider.dart';

import 'models.dart';
import 'secure_store.dart';

class IncidentCache extends GeneratedDatabase {
  IncidentCache._(super.executor);

  static Future<IncidentCache> open(SecureConnectionStore store) async {
    final directory = await getApplicationSupportDirectory();
    var key = await store.readCacheKey();
    if (key == null) {
      key = List<int>.generate(
        32,
        (_) => Random.secure().nextInt(256),
      ).map((byte) => byte.toRadixString(16).padLeft(2, '0')).join();
      await store.writeCacheKey(key);
    }
    final file = File(path.join(directory.path, 'incidents.sqlite'));
    final executor = NativeDatabase.createInBackground(
      file,
      setup: (database) {
        database.execute("PRAGMA key = \"x'$key'\"");
        database.execute('PRAGMA foreign_keys = ON');
      },
    );
    return IncidentCache._(executor);
  }

  @override
  int get schemaVersion => 1;

  @override
  Iterable<TableInfo<Table, Object?>> get allTables => const [];

  @override
  MigrationStrategy get migration => MigrationStrategy(
    onCreate: (_) async {
      await customStatement('''
        CREATE TABLE incident_cache (
          connection_id TEXT NOT NULL,
          incident_id TEXT NOT NULL,
          payload TEXT NOT NULL,
          cached_at TEXT NOT NULL,
          PRIMARY KEY (connection_id, incident_id)
        )
      ''');
    },
  );

  Future<void> replaceConnectionIncidents(
    String connectionId,
    List<Map<String, dynamic>> incidents,
  ) async {
    await transaction(() async {
      await customUpdate(
        'DELETE FROM incident_cache WHERE connection_id = ?',
        variables: [Variable.withString(connectionId)],
      );
      for (final incident in incidents) {
        await customInsert(
          'INSERT INTO incident_cache '
          '(connection_id, incident_id, payload, cached_at) VALUES (?, ?, ?, ?)',
          variables: [
            Variable.withString(connectionId),
            Variable.withString(incident['id'].toString()),
            Variable.withString(jsonEncode(incident)),
            Variable.withString(DateTime.now().toUtc().toIso8601String()),
          ],
        );
      }
    });
  }

  Future<List<AdminIncident>> readConnectionIncidents(
    String connectionId,
  ) async {
    final rows = await customSelect(
      'SELECT payload FROM incident_cache WHERE connection_id = ?',
      variables: [Variable.withString(connectionId)],
    ).get();
    return rows
        .map(
          (row) => AdminIncident.fromJson(
            Map<String, dynamic>.from(
              jsonDecode(row.read<String>('payload')) as Map,
            ),
            connectionId,
            stale: true,
          ),
        )
        .toList();
  }

  Future<void> deleteConnection(String connectionId) => customUpdate(
    'DELETE FROM incident_cache WHERE connection_id = ?',
    variables: [Variable.withString(connectionId)],
  );
}
