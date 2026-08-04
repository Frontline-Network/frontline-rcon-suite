import 'package:crcon_mobile_admin/frontline_theme.dart';
import 'package:crcon_mobile_admin/models.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('parses multiple incident subjects and selects the primary target', () {
    final incident = AdminIncident.fromJson({
      'id': 'incident',
      'server_number': 2,
      'source': 'chat',
      'status': 'new',
      'reason': 'Item has no communication',
      'revision': 3,
      'created_at': '2026-08-04T12:00:00Z',
      'updated_at': '2026-08-04T12:00:01Z',
      'reporter_context': {'team': 'Allies', 'unit_name': 'Able'},
      'subjects': [
        {
          'id': 'squad',
          'kind': 'squad',
          'state': 'confirmed',
          'is_primary': true,
          'display_name': 'Item',
          'team': 'Allies',
          'squad_name': 'Item',
          'leader_player_id': 'leader',
          'snapshot': {
            'players': [
              {'player_id': 'leader', 'name': 'Leader'},
            ],
          },
        },
        {
          'id': 'player',
          'kind': 'player',
          'state': 'suggested',
          'is_primary': false,
          'display_name': 'Leeder',
          'player_id': 'leader',
          'confidence': 0.8,
        },
      ],
    }, 'connection');

    expect(incident.primarySubject?.displayName, 'Item');
    expect(incident.primarySubject?.actionPlayerId, isNull);
    expect(incident.suggestedCount, 1);
    expect(incident.reporterContext['unit_name'], 'Able');
  });

  testWidgets('uses the Frontline visual system', (tester) async {
    await tester.pumpWidget(
      MaterialApp(
        theme: FrontlineTheme.dark,
        home: const Scaffold(body: Card(child: Text('Incident'))),
      ),
    );

    final context = tester.element(find.byType(Scaffold));
    expect(
      Theme.of(context).scaffoldBackgroundColor,
      FrontlineTheme.background,
    );
    expect(Theme.of(context).colorScheme.primary, FrontlineTheme.gold);
    expect(Theme.of(context).cardTheme.shape, isA<RoundedRectangleBorder>());
  });
}
