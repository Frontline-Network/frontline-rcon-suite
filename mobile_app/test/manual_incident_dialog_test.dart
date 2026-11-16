import 'package:crcon_mobile_admin/main.dart';
import 'package:crcon_mobile_admin/models.dart';
import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  testWidgets('French incident dialog remains usable above the keyboard', (
    tester,
  ) async {
    tester.view.devicePixelRatio = 1;
    tester.view.physicalSize = const Size(592, 800);
    tester.view.viewInsets = const FakeViewPadding(bottom: 300);
    addTearDown(tester.view.reset);
    const connection = ConnectionProfile(
      id: 'connection',
      baseUrl: 'https://crcon.example.org',
      name: 'Frontline Network',
      username: 'admin',
      deviceId: 'device',
    );
    await tester.pumpWidget(
      const MaterialApp(
        locale: Locale('fr'),
        supportedLocales: [Locale('de'), Locale('en'), Locale('fr')],
        localizationsDelegates: [
          GlobalMaterialLocalizations.delegate,
          GlobalCupertinoLocalizations.delegate,
          GlobalWidgetsLocalizations.delegate,
        ],
        home: Scaffold(
          body: ManualIncidentDialog(
            profiles: [connection],
            servers: {
              'connection': [
                {'server_number': 1, 'name': 'Frontline Network #1'},
              ],
            },
          ),
        ),
      ),
    );
    await tester.enterText(find.byType(TextField), 'Signalement de test');
    await tester.pump();
    expect(find.text('Créer un incident'), findsOneWidget);
    expect(find.text('Créer'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets('manual incident dialog remains usable above the keyboard', (
    tester,
  ) async {
    tester.view.devicePixelRatio = 1;
    tester.view.physicalSize = const Size(592, 800);
    tester.view.viewInsets = const FakeViewPadding(bottom: 300);
    addTearDown(tester.view.reset);

    const connection = ConnectionProfile(
      id: 'connection',
      baseUrl: 'https://crcon.example.org',
      name: 'Frontline Network with a very long installation name',
      username: 'admin',
      deviceId: 'device',
    );
    await tester.pumpWidget(
      MaterialApp(
        locale: const Locale('de'),
        supportedLocales: const [Locale('de'), Locale('en')],
        localizationsDelegates: const [
          GlobalMaterialLocalizations.delegate,
          GlobalCupertinoLocalizations.delegate,
          GlobalWidgetsLocalizations.delegate,
        ],
        home: const Scaffold(
          body: ManualIncidentDialog(
            profiles: [connection],
            servers: {
              'connection': [
                {
                  'server_number': 1,
                  'name': 'Frontline Network #1 with a long server name',
                },
              ],
            },
          ),
        ),
      ),
    );

    await tester.enterText(find.byType(TextField), 'Testmeldung');
    await tester.pump();

    expect(find.text('Vorfall erstellen'), findsOneWidget);
    expect(find.text('Erstellen'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });
}
