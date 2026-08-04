import 'package:crcon_mobile_admin/app_logger.dart';
import 'package:crcon_mobile_admin/frontline_theme.dart';
import 'package:crcon_mobile_admin/main.dart';
import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  testWidgets('diagnostics screen shows redacted entries and export actions', (
    tester,
  ) async {
    await AppLogger.instance.clear();
    AppLogger.instance.error(
      'api',
      'Authorization=Bearer top-secret',
      message: 'GET rcon.example/api failed',
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
        theme: FrontlineTheme.dark,
        home: const DiagnosticsScreen(),
      ),
    );

    expect(find.text('Diagnoseprotokoll'), findsOneWidget);
    expect(find.textContaining('GET rcon.example/api failed'), findsOneWidget);
    expect(AppLogger.instance.exportText(), isNot(contains('top-secret')));
    expect(find.byIcon(Icons.copy_outlined), findsOneWidget);
    expect(find.byIcon(Icons.share_outlined), findsOneWidget);
    expect(find.byIcon(Icons.delete_outline), findsOneWidget);
  });
}
