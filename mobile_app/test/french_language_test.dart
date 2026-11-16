import 'package:crcon_mobile_admin/main.dart';
import 'package:crcon_mobile_admin/models.dart';
import 'package:crcon_mobile_admin/providers.dart';
import 'package:crcon_mobile_admin/secure_store.dart';
import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';

class MemoryLanguageStore extends SecureConnectionStore {
  String? language;

  @override
  Future<String?> readLanguage() async => language;

  @override
  Future<void> writeLanguage(String languageCode) async {
    language = languageCode;
  }

  @override
  Future<List<ConnectionProfile>> readConnections() async => [];
}

void main() {
  testWidgets('known errors are translated while server details stay intact', (
    tester,
  ) async {
    await tester.pumpWidget(
      MaterialApp(
        locale: const Locale('fr'),
        supportedLocales: const [Locale('de'), Locale('en'), Locale('fr')],
        localizationsDelegates: const [
          GlobalMaterialLocalizations.delegate,
          GlobalCupertinoLocalizations.delegate,
          GlobalWidgetsLocalizations.delegate,
        ],
        home: Builder(
          builder: (context) => Scaffold(
            body: Column(
              children: [
                Text(
                  context.localizeError(
                    'CRCON hat kein gültiges Spielerprofil geliefert.',
                  ),
                ),
                Text(
                  context.localizeError(
                    'CRCON hat eine ungültige Antwort geliefert (HTTP 502).',
                  ),
                ),
                Text(context.localizeError('Unrecognized server error 123')),
                Text(
                  context.localizeError(
                    const FormatException('Incomplete CRCON pairing code.'),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();
    expect(
      find.text('CRCON n’a pas renvoyé de profil de joueur valide.'),
      findsOneWidget,
    );
    expect(
      find.text('CRCON a renvoyé une réponse invalide (HTTP 502).'),
      findsOneWidget,
    );
    expect(find.text('Unrecognized server error 123'), findsOneWidget);
    expect(
      find.text('Le code d’association CRCON est incomplet.'),
      findsOneWidget,
    );
  });

  testWidgets('restores saved French when the app starts', (tester) async {
    final storage = MemoryLanguageStore()..language = 'fr';
    final container = ProviderContainer(
      overrides: [secureStoreProvider.overrideWithValue(storage)],
    );
    addTearDown(container.dispose);
    await tester.pumpWidget(
      UncontrolledProviderScope(
        container: container,
        child: const CrconMobileApp(),
      ),
    );
    await tester.pump();
    await tester.pump(const Duration(seconds: 1));
    expect(container.read(localeProvider).languageCode, 'fr');
    expect(tester.takeException(), isNull);
  });

  testWidgets('settings select French and persist the choice', (tester) async {
    final storage = MemoryLanguageStore();
    final router = GoRouter(
      routes: [
        GoRoute(path: '/', builder: (context, state) => const SettingsScreen()),
      ],
    );
    addTearDown(router.dispose);
    await tester.binding.setSurfaceSize(const Size(1400, 1000));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    await tester.pumpWidget(
      ProviderScope(
        overrides: [secureStoreProvider.overrideWithValue(storage)],
        child: Consumer(
          builder: (context, ref, _) => MaterialApp.router(
            locale: ref.watch(localeProvider),
            supportedLocales: const [Locale('de'), Locale('en'), Locale('fr')],
            localizationsDelegates: const [
              GlobalMaterialLocalizations.delegate,
              GlobalCupertinoLocalizations.delegate,
              GlobalWidgetsLocalizations.delegate,
            ],
            routerConfig: router,
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();
    await tester.tap(find.byType(DropdownButtonFormField<String>));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Français').last);
    await tester.pumpAndSettle();

    expect(storage.language, 'fr');
    expect(find.text('Paramètres Frontline'), findsOneWidget);
    expect(find.text('Langue'), findsOneWidget);
    expect(await storage.readLanguage(), 'fr');
  });
}
