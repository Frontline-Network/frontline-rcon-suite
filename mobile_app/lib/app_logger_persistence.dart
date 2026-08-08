import 'dart:io';

import 'package:path_provider/path_provider.dart';

abstract class AppLogPersistence {
  Future<List<String>> readLines();
  Future<void> writeText(String contents);
}

class _FileAppLogPersistence implements AppLogPersistence {
  const _FileAppLogPersistence(this._file);

  final File _file;

  @override
  Future<List<String>> readLines() async =>
      await _file.exists() ? _file.readAsLines() : const [];

  @override
  Future<void> writeText(String contents) =>
      _file.writeAsString(contents, flush: true);
}

Future<AppLogPersistence> openAppLogPersistence() async {
  final directory = await getApplicationSupportDirectory();
  return _FileAppLogPersistence(
    File('${directory.path}${Platform.pathSeparator}diagnostics-v1.jsonl'),
  );
}

String get appLogPlatform => Platform.operatingSystem;
