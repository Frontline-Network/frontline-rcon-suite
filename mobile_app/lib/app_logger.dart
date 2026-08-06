import 'dart:async';
import 'dart:convert';

import 'package:flutter/foundation.dart';

import 'app_logger_persistence.dart'
    if (dart.library.html) 'app_logger_persistence_web.dart';

enum AppLogLevel { info, warning, error }

class AppLogEntry {
  const AppLogEntry({
    required this.timestamp,
    required this.level,
    required this.category,
    required this.message,
    this.stackTrace,
  });

  final DateTime timestamp;
  final AppLogLevel level;
  final String category;
  final String message;
  final String? stackTrace;

  Map<String, dynamic> toJson() => {
    'timestamp': timestamp.toUtc().toIso8601String(),
    'level': level.name,
    'category': category,
    'message': message,
    'stack_trace': ?stackTrace,
  };

  factory AppLogEntry.fromJson(Map<String, dynamic> json) => AppLogEntry(
    timestamp: DateTime.parse(json['timestamp'].toString()).toLocal(),
    level: AppLogLevel.values.firstWhere(
      (level) => level.name == json['level'],
      orElse: () => AppLogLevel.info,
    ),
    category: json['category']?.toString() ?? 'app',
    message: json['message']?.toString() ?? '',
    stackTrace: json['stack_trace']?.toString(),
  );

  String get formatted {
    final local = timestamp.toLocal().toIso8601String();
    final details = stackTrace == null || stackTrace!.isEmpty
        ? ''
        : '\n$stackTrace';
    return '$local [${level.name.toUpperCase()}] [$category] $message$details';
  }
}

class AppLogger {
  AppLogger._();

  static final AppLogger instance = AppLogger._();
  static const int _maximumEntries = 400;

  final ValueNotifier<int> revision = ValueNotifier<int>(0);
  final List<AppLogEntry> _entries = [];
  Future<void> _writeQueue = Future<void>.value();
  AppLogPersistence? _persistence;

  List<AppLogEntry> get entries => List.unmodifiable(_entries.reversed);

  Future<void> initialize() async {
    try {
      _persistence = await openAppLogPersistence();
      final lines = await _persistence!.readLines();
      for (final line in lines.skip(
        lines.length > _maximumEntries ? lines.length - _maximumEntries : 0,
      )) {
        try {
          final value = jsonDecode(line);
          if (value is Map) {
            _entries.add(
              AppLogEntry.fromJson(Map<String, dynamic>.from(value)),
            );
          }
        } catch (_) {
          // A single damaged line must not make the diagnostics unavailable.
        }
      }
      revision.value++;
    } catch (_) {
      // Diagnostics remain available in memory when the file cannot be opened.
    }
  }

  void info(String category, String message) =>
      _record(AppLogLevel.info, category, message);

  void warning(String category, String message, {Object? error}) => _record(
    AppLogLevel.warning,
    category,
    error == null ? message : '$message: $error',
  );

  void error(
    String category,
    Object error, {
    String? message,
    StackTrace? stackTrace,
  }) => _record(
    AppLogLevel.error,
    category,
    message == null ? error.toString() : '$message: $error',
    stackTrace: stackTrace,
  );

  void _record(
    AppLogLevel level,
    String category,
    String message, {
    StackTrace? stackTrace,
  }) {
    _entries.add(
      AppLogEntry(
        timestamp: DateTime.now(),
        level: level,
        category: sanitize(category, maximumLength: 80),
        message: sanitize(message, maximumLength: 2000),
        stackTrace: stackTrace == null
            ? null
            : sanitize(stackTrace.toString(), maximumLength: 5000),
      ),
    );
    if (_entries.length > _maximumEntries) {
      _entries.removeRange(0, _entries.length - _maximumEntries);
    }
    revision.value++;
    _writeQueue = _writeQueue.then((_) => _persist()).catchError((_) {});
  }

  Future<void> clear() async {
    _entries.clear();
    revision.value++;
    await _writeQueue;
    await _persist();
  }

  String exportText() {
    final buffer = StringBuffer()
      ..writeln('Frontline CRCON Admin diagnostics')
      ..writeln('App: 0.1.18+19')
      ..writeln('Platform: $appLogPlatform')
      ..writeln('Exported: ${DateTime.now().toUtc().toIso8601String()}')
      ..writeln('Sensitive credentials are automatically redacted.')
      ..writeln();
    for (final entry in _entries) {
      buffer.writeln(entry.formatted);
    }
    return buffer.toString();
  }

  Future<void> _persist() async {
    final persistence = _persistence;
    if (persistence == null) return;
    final contents = _entries
        .map((entry) => jsonEncode(entry.toJson()))
        .join('\n');
    await persistence.writeText(contents.isEmpty ? '' : '$contents\n');
  }

  @visibleForTesting
  static String sanitize(String value, {int maximumLength = 5000}) {
    var clean = value;
    clean = clean.replaceAll(
      RegExp(r'Bearer\s+[^\s,;]+', caseSensitive: false),
      'Bearer [REDACTED]',
    );
    clean = clean.replaceAllMapped(
      RegExp(
        r'((?:access_token|refresh_token|exchange_token|token|secret|password|authorization|push_token|push_handle|push_capability)\s*[=:]\s*)([^\s&,;}]+)',
        caseSensitive: false,
      ),
      (match) => '${match.group(1)}[REDACTED]',
    );
    clean = clean.replaceAllMapped(
      RegExp(
        r'''(["'](?:access_token|refresh_token|exchange_token|token|secret|password|authorization|push_token|push_handle|push_capability)["']\s*:\s*)(["'][^"']*["'])''',
        caseSensitive: false,
      ),
      (match) => '${match.group(1)}"[REDACTED]"',
    );
    if (clean.length > maximumLength) {
      return '${clean.substring(0, maximumLength)}\n[TRUNCATED]';
    }
    return clean;
  }
}
