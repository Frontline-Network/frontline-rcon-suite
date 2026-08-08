import 'dart:io';

bool get appIsWindows => Platform.isWindows;
bool get appIsWeb => false;

String get appDevicePlatform => Platform.isIOS
    ? 'ios'
    : Platform.isWindows
    ? 'windows'
    : 'android';

String appDeviceName(String fallback) =>
    Platform.localHostname.isEmpty ? fallback : Platform.localHostname;
