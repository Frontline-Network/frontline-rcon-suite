import 'package:dio/dio.dart';
import 'package:firebase_messaging/firebase_messaging.dart';

import 'app_logger.dart';
import 'platform_info.dart' if (dart.library.html) 'platform_info_web.dart';

class PushRelayIdentity {
  const PushRelayIdentity({required this.handle, required this.capability});
  final String handle;
  final String capability;
}

class PushRelay {
  static const baseUrl = String.fromEnvironment('PUSH_RELAY_URL');
  static const webVapidKey = String.fromEnvironment('FIREBASE_WEB_VAPID_KEY');

  static Future<PushRelayIdentity?> register() async {
    if (baseUrl.isEmpty) return null;
    final token = await FirebaseMessaging.instance.getToken(
      vapidKey: webVapidKey.isEmpty ? null : webVapidKey,
    );
    if (token == null) return null;
    final endpoint = '${baseUrl.replaceFirst(RegExp(r'/$'), '')}/v1/devices';
    try {
      AppLogger.instance.info(
        'push',
        'POST ${Uri.parse(endpoint).host}${Uri.parse(endpoint).path} started',
      );
      final response = await Dio().post<Map<String, dynamic>>(
        endpoint,
        data: {'platform': appDevicePlatform, 'push_token': token},
      );
      AppLogger.instance.info(
        'push',
        'Push relay registration completed with HTTP ${response.statusCode}',
      );
      final body = response.data!;
      return PushRelayIdentity(
        handle: body['handle'].toString(),
        capability: body['notify_capability'].toString(),
      );
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
}
