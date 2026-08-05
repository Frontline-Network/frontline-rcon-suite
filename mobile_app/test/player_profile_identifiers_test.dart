import 'package:crcon_mobile_admin/main.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  testWidgets('shows SteamID and EOS-ID as separate identifiers', (
    tester,
  ) async {
    await tester.pumpWidget(
      const MaterialApp(
        locale: Locale('de'),
        home: Scaffold(
          body: PlayerProfileDossier(
            playerId: '76561198036685843',
            incidentContext: null,
            dossier: {
              'player_id': '76561198036685843',
              'identifiers': {
                'steam_id': '76561198036685843',
                'eos_id': 'eos-7db4c0a9',
                'platform_player_id': null,
              },
              'history': {
                'soldier': {'name': 'Biene'},
                'received_actions': [],
                'sessions': [],
                'bans': [],
                'flags': [],
                'comments': [],
              },
              'live': {
                'name': 'Biene',
                'server_number': 2,
                'team': 'Allies',
                'unit_name': 'Able',
                'role': 'Officer',
                'kills': 42,
                'deaths': 18,
                'teamkills': 3,
              },
            },
          ),
        ),
      ),
    );

    expect(find.text('SteamID'), findsOneWidget);
    expect(find.text('EOS-ID'), findsOneWidget);
    expect(find.text('76561198036685843'), findsOneWidget);
    expect(find.text('eos-7db4c0a9'), findsOneWidget);
    expect(find.textContaining('Steam 765'), findsNothing);
  });
}
