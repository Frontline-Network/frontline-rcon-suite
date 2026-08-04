import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:uuid/uuid.dart';

import 'models.dart';
import 'secure_store.dart';

class CrconApiException implements Exception {
  const CrconApiException(this.message, {this.statusCode});
  final String message;
  final int? statusCode;
  @override
  String toString() => message;
}

class PairingSession {
  const PairingSession({
    required this.payload,
    required this.exchangeToken,
    required this.verificationCode,
  });
  final PairingPayload payload;
  final String exchangeToken;
  final String verificationCode;
}

class CrconApi {
  CrconApi(this.profile, this.store)
    : _dio = Dio(
        BaseOptions(
          baseUrl: '${profile.baseUrl}/api/mobile/v1/',
          connectTimeout: const Duration(seconds: 8),
          receiveTimeout: const Duration(seconds: 12),
          validateStatus: (status) => status != null && status < 500,
        ),
      );

  final ConnectionProfile profile;
  final SecureConnectionStore store;
  final Dio _dio;

  static void validateProductionUrl(String baseUrl) {
    final uri = Uri.parse(baseUrl);
    if (!uri.hasAuthority || (!kDebugMode && uri.scheme != 'https')) {
      throw const CrconApiException('CRCON requires a public HTTPS URL.');
    }
    if (kDebugMode && !{'http', 'https'}.contains(uri.scheme)) {
      throw const CrconApiException('Unsupported CRCON URL.');
    }
  }

  static Future<PairingSession> scanPairing(
    PairingPayload payload, {
    required String deviceName,
    required String platform,
    String pushHandle = '',
    String pushCapability = '',
  }) async {
    validateProductionUrl(payload.baseUrl);
    final response = await Dio().post<Map<String, dynamic>>(
      '${payload.baseUrl}/api/mobile/v1/pairings/${payload.pairingId}/scan',
      data: {
        'secret': payload.secret,
        'device_name': deviceName,
        'platform': platform,
        'app_version': '0.1.1',
        'push_handle': pushHandle,
        'push_capability': pushCapability,
      },
      options: Options(
        validateStatus: (status) => status != null && status < 500,
      ),
    );
    final result = decodeCrconResponse(response);
    return PairingSession(
      payload: payload,
      exchangeToken: result['exchange_token'].toString(),
      verificationCode: result['verification_code'].toString(),
    );
  }

  static Future<ConnectionProfile?> exchangePairing(
    PairingSession session,
    SecureConnectionStore store,
  ) async {
    final response = await Dio().post<Map<String, dynamic>>(
      '${session.payload.baseUrl}/api/mobile/v1/pairings/'
      '${session.payload.pairingId}/exchange',
      data: {'exchange_token': session.exchangeToken},
      options: Options(
        validateStatus: (status) => status != null && status < 500,
      ),
    );
    if (response.statusCode == HttpStatus.accepted) return null;
    final result = decodeCrconResponse(response);
    final profile = ConnectionProfile(
      id: result['installation_id'].toString(),
      baseUrl: session.payload.baseUrl,
      name: Uri.parse(session.payload.baseUrl).host,
      username: result['username'].toString(),
      deviceId: result['device_id'].toString(),
    );
    await store.saveConnection(
      profile,
      accessToken: result['access_token'].toString(),
      refreshToken: result['refresh_token'].toString(),
    );
    return profile;
  }

  Future<List<Map<String, dynamic>>> listIncidents() async {
    final result = await _authorized('GET', 'incidents?limit=250');
    return (result as List<dynamic>)
        .map((item) => Map<String, dynamic>.from(item as Map))
        .toList();
  }

  Future<Map<String, dynamic>> incident(String id) async =>
      Map<String, dynamic>.from(
        await _authorized('GET', 'incidents/$id') as Map,
      );

  Future<Map<String, dynamic>> bootstrap() async =>
      Map<String, dynamic>.from(await _authorized('GET', 'bootstrap') as Map);

  Future<Map<String, dynamic>> createIncident({
    required int serverNumber,
    required String reason,
  }) async => Map<String, dynamic>.from(
    await _authorized(
          'POST',
          'incidents',
          data: {'server_number': serverNumber, 'reason': reason},
          headers: {'Idempotency-Key': const Uuid().v4()},
        )
        as Map,
  );

  Future<Map<String, dynamic>> mutateIncident(
    String id, {
    required String operation,
    required int revision,
    Map<String, dynamic> payload = const {},
  }) async => Map<String, dynamic>.from(
    await _authorized(
          'PATCH',
          'incidents/$id',
          data: {...payload, 'operation': operation, 'revision': revision},
          headers: {'Idempotency-Key': const Uuid().v4()},
        )
        as Map,
  );

  Future<Map<String, dynamic>> addNote(
    String incidentId, {
    required int revision,
    required String note,
  }) async => Map<String, dynamic>.from(
    await _authorized(
          'POST',
          'incidents/$incidentId/notes',
          data: {'revision': revision, 'note': note},
          headers: {'Idempotency-Key': const Uuid().v4()},
        )
        as Map,
  );

  Future<Map<String, dynamic>> runAction(
    String incidentId,
    Map<String, dynamic> action,
  ) async => Map<String, dynamic>.from(
    await _authorized(
          'POST',
          'incidents/$incidentId/actions',
          data: action,
          headers: {'Idempotency-Key': const Uuid().v4()},
        )
        as Map,
  );

  Future<Map<String, dynamic>> addIncidentSubject(
    String incidentId, {
    required int revision,
    required String kind,
    required String displayName,
    String? playerId,
    String? team,
    String? squadName,
  }) async => Map<String, dynamic>.from(
    await _authorized(
          'POST',
          'incidents/$incidentId/subjects',
          data: {
            'revision': revision,
            'kind': kind,
            'display_name': displayName,
            'player_id': ?playerId,
            'team': ?team,
            'squad_name': ?squadName,
          },
          headers: {'Idempotency-Key': const Uuid().v4()},
        )
        as Map,
  );

  Future<Map<String, dynamic>> mutateIncidentSubject(
    String incidentId,
    String subjectId, {
    required int revision,
    required String operation,
  }) async => Map<String, dynamic>.from(
    await _authorized(
          'PATCH',
          'incidents/$incidentId/subjects/$subjectId',
          data: {'revision': revision, 'operation': operation},
          headers: {'Idempotency-Key': const Uuid().v4()},
        )
        as Map,
  );

  Future<void> updatePushIdentity(String handle, String capability) async {
    await _authorized(
      'PATCH',
      'devices/${profile.deviceId}',
      data: {'push_handle': handle, 'push_capability': capability},
    );
  }

  Future<void> updateNotifications(bool enabled) async {
    await _authorized(
      'PATCH',
      'devices/${profile.deviceId}',
      data: {'notifications_enabled': enabled},
    );
  }

  Future<void> revokeDevice() async {
    await _authorized('DELETE', 'devices/${profile.deviceId}');
  }

  Future<List<Map<String, dynamic>>> searchPlayers(
    String query, {
    int? serverNumber,
  }) async {
    final result = await _authorized(
      'GET',
      'players/search',
      queryParameters: {'q': query, 'server_number': ?serverNumber},
    );
    return (result as List<dynamic>? ?? const [])
        .map((item) => Map<String, dynamic>.from(item as Map))
        .toList();
  }

  Future<Map<String, dynamic>> playerProfile(
    String playerId, {
    int? serverNumber,
  }) async => Map<String, dynamic>.from(
    await _authorized(
          'GET',
          'players/$playerId',
          queryParameters: {'server_number': ?serverNumber},
        )
        as Map,
  );

  Future<Map<String, dynamic>> roster(int serverNumber) async =>
      Map<String, dynamic>.from(
        await _authorized('GET', 'servers/$serverNumber/roster') as Map,
      );

  Future<Map<String, dynamic>> squad(
    int serverNumber,
    String team,
    String squadName,
  ) async => Map<String, dynamic>.from(
    await _authorized(
          'GET',
          'servers/$serverNumber/squads/'
              '${Uri.encodeComponent(team)}/${Uri.encodeComponent(squadName)}',
        )
        as Map,
  );

  Future<dynamic> _authorized(
    String method,
    String path, {
    Object? data,
    Map<String, dynamic>? headers,
    Map<String, dynamic>? queryParameters,
    bool refreshed = false,
  }) async {
    final token = await store.accessToken(profile.id);
    final response = await _dio.request<dynamic>(
      path,
      data: data,
      queryParameters: queryParameters,
      options: Options(
        method: method,
        headers: {...?headers, 'Authorization': 'Bearer $token'},
      ),
    );
    if (response.statusCode == 401 && !refreshed) {
      await _refresh();
      return _authorized(
        method,
        path,
        data: data,
        headers: headers,
        queryParameters: queryParameters,
        refreshed: true,
      );
    }
    return decodeCrconResponse(response);
  }

  Future<void> _refresh() async {
    final refreshToken = await store.refreshToken(profile.id);
    final response = await _dio.post<Map<String, dynamic>>(
      'tokens/refresh',
      data: {'device_id': profile.deviceId, 'refresh_token': refreshToken},
    );
    final result = decodeCrconResponse(response);
    await store.replaceTokens(
      profile.id,
      accessToken: result['access_token'].toString(),
      refreshToken: result['refresh_token'].toString(),
    );
  }
}

dynamic decodeCrconResponse(Response<dynamic> response) {
  dynamic payload = response.data;
  if (payload is String) {
    try {
      payload = jsonDecode(payload);
    } on FormatException {
      final status = response.statusCode;
      throw CrconApiException(
        status == HttpStatus.notFound
            ? 'CRCON Mobile API ist noch nicht auf dem benötigten Stand.'
            : 'CRCON hat eine ungültige Antwort geliefert${status == null ? '' : ' (HTTP $status)'}.',
        statusCode: status,
      );
    }
  }
  if (payload is! Map) {
    throw CrconApiException(
      'CRCON hat ein unerwartetes Antwortformat geliefert.',
      statusCode: response.statusCode,
    );
  }
  final envelope = Map<String, dynamic>.from(payload);
  if (response.statusCode == null ||
      response.statusCode! >= 400 ||
      envelope['failed'] == true) {
    throw CrconApiException(
      envelope['error']?.toString() ?? 'CRCON request failed',
      statusCode: response.statusCode,
    );
  }
  return envelope['result'];
}
