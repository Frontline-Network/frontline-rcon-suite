import 'package:crcon_mobile_admin/frontline_theme.dart';
import 'package:crcon_mobile_admin/main.dart';
import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  testWidgets('diagnostics screen uses French labels', (tester) async {
    await tester.pumpWidget(
      MaterialApp(
        locale: const Locale('fr'),
        supportedLocales: const [Locale('de'), Locale('en'), Locale('fr')],
        localizationsDelegates: const [
          GlobalMaterialLocalizations.delegate,
          GlobalCupertinoLocalizations.delegate,
          GlobalWidgetsLocalizations.delegate,
        ],
        theme: FrontlineTheme.dark,
        home: const DiagnosticsScreen(),
      ),
    );
    await tester.pumpAndSettle();
    expect(find.text('Journal des diagnostics'), findsOneWidget);
    expect(
      find.text('Aucune entrée de diagnostic pour le moment.'),
      findsOneWidget,
    );
  });
}
