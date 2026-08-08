import 'package:dio/dio.dart';
import 'package:firebase_messaging/firebase_messaging.dart';

import 'app_logger.dart';
import 'platform_info.dart' if (dart.library.html) 'platform_info_web.dart';
import 'secure_store.dart';

class PushRelayIdentity {
  const PushRelayIdentity({required this.handle, required this.capability});
  final String handle;
  final String capability;
}

class PushRelay {
  static const baseUrl = String.fromEnvironment('PUSH_RELAY_URL');
  static const webVapidKey = String.fromEnvironment('FIREBASE_WEB_VAPID_KEY');

  static Future<PushRelayIdentity?> register(
    PushRelayIdentityStore store, {
    String? relayBaseUrl,
    Future<String?> Function()? tokenProvider,
    Future<Map<String, dynamic>> Function(String endpoint, String token)?
    registrar,
  }) async {
    final normalizedBaseUrl = (relayBaseUrl ?? baseUrl).replaceFirst(
      RegExp(r'/$'),
      '',
    );
    if (normalizedBaseUrl.isEmpty) return null;
    final token =
        await (tokenProvider ??
            () => FirebaseMessaging.instance.getToken(
              vapidKey: webVapidKey.isEmpty ? null : webVapidKey,
            ))();
    if (token == null) return null;
    final cached = await store.readPushRelayIdentity();
    if (cached?['base_url'] == normalizedBaseUrl &&
        cached?['push_token'] == token) {
      return PushRelayIdentity(
        handle: cached!['handle']!,
        capability: cached['capability']!,
      );
    }
    final endpoint = '$normalizedBaseUrl/v1/devices';
    try {
      AppLogger.instance.info(
        'push',
        'POST ${Uri.parse(endpoint).host}${Uri.parse(endpoint).path} started',
      );
      final body = registrar != null
          ? await registrar(endpoint, token)
          : await _registerWithRelay(endpoint, token);
      final identity = PushRelayIdentity(
        handle: body['handle'].toString(),
        capability: body['notify_capability'].toString(),
      );
      if (identity.handle.isEmpty ||
          identity.handle == 'null' ||
          identity.capability.isEmpty ||
          identity.capability == 'null') {
        throw const FormatException('Push relay returned an invalid identity');
      }
      await store.writePushRelayIdentity(
        baseUrl: normalizedBaseUrl,
        pushToken: token,
        handle: identity.handle,
        capability: identity.capability,
      );
      return identity;
    } catch (error, stackTrace) {
      AppLogger.instance.error(
        'push',
        error,
        message: 'Push relay registration failed',
        stackTrace: stackTrace,
      );
      rethrow;
    }
  }

  static Future<Map<String, dynamic>> _registerWithRelay(
    String endpoint,
    String token,
  ) async {
    final dio = Dio(
      BaseOptions(
        connectTimeout: const Duration(seconds: 5),
        sendTimeout: const Duration(seconds: 5),
        receiveTimeout: const Duration(seconds: 8),
      ),
    );
    final response = await dio.post<Map<String, dynamic>>(
      endpoint,
      data: {'platform': appDevicePlatform, 'push_token': token},
    );
    AppLogger.instance.info(
      'push',
      'Push relay registration completed with HTTP ${response.statusCode}',
    );
    final body = response.data;
    if (body == null) {
      throw const FormatException('Push relay returned an empty response');
    }
    return body;
  }
}
