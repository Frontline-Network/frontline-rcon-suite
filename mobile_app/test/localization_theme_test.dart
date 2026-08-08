import 'package:crcon_mobile_admin/frontline_theme.dart';
import 'package:crcon_mobile_admin/l10n/generated/app_localizations.dart';
import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_test/flutter_test.dart';

Widget localizedHarness(Locale locale) {
  return MaterialApp(
    locale: locale,
    theme: FrontlineTheme.dark,
    localizationsDelegates: const [
      AppLocalizations.delegate,
      GlobalMaterialLocalizations.delegate,
      GlobalWidgetsLocalizations.delegate,
      GlobalCupertinoLocalizations.delegate,
    ],
    supportedLocales: AppLocalizations.supportedLocales,
    home: Builder(
      builder: (context) {
        final strings = AppLocalizations.of(context);
        return Scaffold(
          body: Column(
            children: [
              Text(strings.incidentInbox),
              Text(strings.playerSearch),
              Text(strings.cancel),
              Text(strings.serverNumber(2)),
              Text(strings.punish),
              Text(strings.tempBan),
            ],
          ),
        );
      },
    ),
  );
}

void main() {
  testWidgets('renders the German admin vocabulary', (tester) async {
    await tester.pumpWidget(localizedHarness(const Locale('de')));
    await tester.pumpAndSettle();

    expect(find.text('Vorfall-Inbox'), findsOneWidget);
    expect(find.text('Spielersuche'), findsOneWidget);
    expect(find.text('Abbrechen'), findsOneWidget);
    expect(find.text('Server 2'), findsOneWidget);
    expect(find.text('Bestrafen'), findsOneWidget);
    expect(find.text('Temporär sperren'), findsOneWidget);
  });

  testWidgets('keeps the complete English fallback available', (tester) async {
    await tester.pumpWidget(localizedHarness(const Locale('en')));
    await tester.pumpAndSettle();

    expect(find.text('Incident inbox'), findsOneWidget);
    expect(find.text('Player search'), findsOneWidget);
    expect(find.text('Cancel'), findsOneWidget);
    expect(find.text('Server 2'), findsOneWidget);
    expect(find.text('Punish'), findsOneWidget);
    expect(find.text('Temporary ban'), findsOneWidget);
  });

  testWidgets('applies the central Frontline theme', (tester) async {
    await tester.pumpWidget(localizedHarness(const Locale('de')));
    await tester.pumpAndSettle();

    final scaffold = tester.widget<Scaffold>(find.byType(Scaffold));
    final context = tester.element(find.byType(Scaffold));

    expect(scaffold.backgroundColor, isNull);
    expect(
      Theme.of(context).scaffoldBackgroundColor,
      FrontlineTheme.background,
    );
    expect(Theme.of(context).colorScheme.primary, FrontlineTheme.gold);
  });
}
