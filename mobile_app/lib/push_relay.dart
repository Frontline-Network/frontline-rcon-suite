import 'dart:io';

import 'package:dio/dio.dart';
import 'package:firebase_messaging/firebase_messaging.dart';

class PushRelayIdentity {
  const PushRelayIdentity({required this.handle, required this.capability});
  final String handle;
  final String capability;
}

class PushRelay {
  static const baseUrl = String.fromEnvironment('PUSH_RELAY_URL');

  static Future<PushRelayIdentity?> register() async {
    if (baseUrl.isEmpty) return null;
    final token = await FirebaseMessaging.instance.getToken();
    if (token == null) return null;
    final response = await Dio().post<Map<String, dynamic>>(
      '${baseUrl.replaceFirst(RegExp(r'/$'), '')}/v1/devices',
      data: {
        'platform': Platform.isIOS ? 'ios' : 'android',
        'push_token': token,
      },
    );
    final body = response.data!;
    return PushRelayIdentity(
      handle: body['handle'].toString(),
      capability: body['notify_capability'].toString(),
    );
  }
}
