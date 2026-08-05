import 'package:crcon_mobile_admin/frontline_theme.dart';
import 'package:crcon_mobile_admin/l10n/generated/app_localizations.dart';
import 'package:crcon_mobile_admin/main.dart';
import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_test/flutter_test.dart';

Widget _harness() => MaterialApp(
  locale: const Locale('de'),
  theme: FrontlineTheme.dark,
  localizationsDelegates: const [
    AppLocalizations.delegate,
    GlobalMaterialLocalizations.delegate,
    GlobalWidgetsLocalizations.delegate,
    GlobalCupertinoLocalizations.delegate,
  ],
  supportedLocales: AppLocalizations.supportedLocales,
  home: Scaffold(
    body: PlayerDirectoryRow(
      player: const {
        'player_id': '76561198000000001',
        'name': 'Ein sehr langer Frontline-Spielername',
        'server_number': 12,
        'team': 'allies',
        'unit_name': 'Able',
        'role': 'automaticrifleman',
      },
      onTap: _noop,
    ),
  ),
);

void _noop() {}

void main() {
  for (final width in [320.0, 430.0, 900.0]) {
    testWidgets('player row remains usable at ${width.toInt()}px', (
      tester,
    ) async {
      await tester.binding.setSurfaceSize(Size(width, 760));
      addTearDown(() => tester.binding.setSurfaceSize(null));

      await tester.pumpWidget(_harness());
      await tester.pumpAndSettle();

      expect(
        find.text('Ein sehr langer Frontline-Spielername'),
        findsOneWidget,
      );
      expect(find.textContaining('Server 12'), findsOneWidget);
      expect(tester.takeException(), isNull);
    });
  }
}
