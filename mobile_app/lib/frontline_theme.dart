import 'package:flutter/material.dart';

abstract final class FrontlineTheme {
  static const background = Color(0xff0b0d0c);
  static const surface = Color(0xff151812);
  static const surfaceHigh = Color(0xff202319);
  static const gold = Color(0xffc6a15b);
  static const chalk = Color(0xffebe7db);
  static const muted = Color(0xffa6a696);

  static ThemeData get dark {
    final scheme =
        ColorScheme.fromSeed(
          seedColor: gold,
          brightness: Brightness.dark,
          surface: surface,
        ).copyWith(
          primary: gold,
          onPrimary: const Color(0xff17130a),
          secondary: const Color(0xff9caa70),
          surface: surface,
          onSurface: chalk,
          outline: const Color(0xff4b4b3d),
          error: const Color(0xffe06f65),
        );
    return ThemeData(
      colorScheme: scheme,
      scaffoldBackgroundColor: background,
      useMaterial3: true,
      fontFamily: 'Roboto',
      appBarTheme: const AppBarTheme(
        backgroundColor: background,
        foregroundColor: chalk,
        elevation: 0,
        centerTitle: false,
      ),
      cardTheme: const CardThemeData(
        color: surface,
        elevation: 0,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.zero,
          side: BorderSide(color: Color(0xff3d3f32)),
        ),
      ),
      inputDecorationTheme: const InputDecorationTheme(
        filled: true,
        fillColor: surfaceHigh,
        border: OutlineInputBorder(borderRadius: BorderRadius.zero),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.zero,
          borderSide: BorderSide(color: Color(0xff4b4b3d)),
        ),
      ),
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(shape: const RoundedRectangleBorder()),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(shape: const RoundedRectangleBorder()),
      ),
      floatingActionButtonTheme: const FloatingActionButtonThemeData(
        shape: RoundedRectangleBorder(),
      ),
      dividerTheme: const DividerThemeData(color: Color(0xff3d3f32)),
    );
  }
}
