abstract class AppLogPersistence {
  Future<List<String>> readLines();
  Future<void> writeText(String contents);
}

class _MemoryAppLogPersistence implements AppLogPersistence {
  const _MemoryAppLogPersistence();

  @override
  Future<List<String>> readLines() async => const [];

  @override
  Future<void> writeText(String _) async {}
}

Future<AppLogPersistence> openAppLogPersistence() async =>
    const _MemoryAppLogPersistence();

String get appLogPlatform => 'web';
