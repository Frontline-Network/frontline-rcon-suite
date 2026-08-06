import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:uuid/uuid.dart';

import 'app_logger.dart';
import 'models.dart';
import 'secure_store.dart';

class CrconApiException implements Exception {
  const CrconApiException(this.message, {this.statusCode});
  final String message;
  final int? statusCode;
  @override
  String toString() => message;
}

class CrconAuthException extends CrconApiException {
  const CrconAuthException(super.message, {super.statusCode});
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

class DesktopAuthorizationSession {
  const DesktopAuthorizationSession({
    required this.baseUrl,
    required this.pairingId,
    required this.deviceCode,
    required this.userCode,
    required this.verificationUri,
    required this.interval,
  });

  final String baseUrl;
  final String pairingId;
  final String deviceCode;
  final String userCode;
  final Uri verificationUri;
  final Duration interval;
}

class CrconApi {
  CrconApi(this.profile, this.store)
    : _dio = _diagnosticDio(
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
  static final Map<String, Future<void>> _refreshes = {};

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
    final response = await _diagnosticDio().post<Map<String, dynamic>>(
      '${payload.baseUrl}/api/mobile/v1/pairings/${payload.pairingId}/scan',
      data: {
        'secret': payload.secret,
        'device_name': deviceName,
        'platform': platform,
        'app_version': '0.1.8',
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

  static Future<DesktopAuthorizationSession> startDesktopAuthorization(
    String baseUrl, {
    required String deviceName,
  }) async {
    final normalizedBaseUrl = baseUrl.trim().replaceFirst(RegExp(r'/+$'), '');
    validateProductionUrl(normalizedBaseUrl);
    final response = await _diagnosticDio().post<Map<String, dynamic>>(
      '$normalizedBaseUrl/api/mobile/v1/desktop-authorizations',
      data: {
        'device_name': deviceName,
        'platform': 'windows',
        'app_version': '0.1.8',
      },
      options: Options(
        validateStatus: (status) => status != null && status < 500,
      ),
    );
    final result = decodeCrconResponse(response) as Map;
    final interval = (result['interval'] as num?)?.toInt() ?? 2;
    return DesktopAuthorizationSession(
      baseUrl: normalizedBaseUrl,
      pairingId: result['id'].toString(),
      deviceCode: result['device_code'].toString(),
      userCode: result['user_code'].toString(),
      verificationUri: Uri.parse(result['verification_uri'].toString()),
      interval: Duration(seconds: interval.clamp(1, 10)),
    );
  }

  static Future<ConnectionProfile?> exchangeDesktopAuthorization(
    DesktopAuthorizationSession session,
    SecureConnectionStore store,
  ) async {
    final response = await _diagnosticDio().post<Map<String, dynamic>>(
      '${session.baseUrl}/api/mobile/v1/desktop-authorizations/'
      '${session.pairingId}/exchange',
      data: {'device_code': session.deviceCode},
      options: Options(
        validateStatus: (status) => status != null && status < 500,
      ),
    );
    if (response.statusCode == HttpStatus.accepted) return null;
    final result = decodeCrconResponse(response) as Map;
    final profile = ConnectionProfile(
      id: result['installation_id'].toString(),
      baseUrl: session.baseUrl,
      name: Uri.parse(session.baseUrl).host,
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

  static Future<ConnectionProfile?> exchangePairing(
    PairingSession session,
    SecureConnectionStore store,
  ) async {
    final response = await _diagnosticDio().post<Map<String, dynamic>>(
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

  Future<Map<String, List<Map<String, dynamic>>>> actionTemplates() async {
    final result = Map<String, dynamic>.from(
      await _authorized('GET', 'templates') as Map,
    );
    List<Map<String, dynamic>> entries(String category) =>
        (result[category] as List? ?? const [])
            .whereType<Map>()
            .map((item) => Map<String, dynamic>.from(item))
            .toList();
    return {'message': entries('message'), 'reason': entries('reason')};
  }

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
    final values = result is List
        ? result
        : result is Map
        ? result.values.toList()
        : const <dynamic>[];
    return values
        .whereType<Map>()
        .map((item) => Map<String, dynamic>.from(item))
        .toList();
  }

  Future<Map<String, dynamic>> playerProfile(
    String playerId, {
    int? serverNumber,
  }) async {
    final result = await _authorized(
      'GET',
      'players/$playerId',
      queryParameters: {'server_number': ?serverNumber},
    );
    if (result is! Map) {
      throw const CrconApiException(
        'CRCON hat kein gültiges Spielerprofil geliefert.',
      );
    }
    return Map<String, dynamic>.from(result);
  }

  Future<Map<String, dynamic>> playerContext(
    String incidentId,
    String playerId, {
    int limit = 5,
  }) async {
    final result = await _authorized(
      'GET',
      'incidents/$incidentId/player-context',
      queryParameters: {'player_id': playerId, 'limit': limit},
    );
    if (result is! Map) {
      throw const CrconApiException(
        'CRCON hat keinen gültigen Fallauszug geliefert.',
      );
    }
    return Map<String, dynamic>.from(result);
  }

  Future<List<Map<String, dynamic>>> watchlist({int? serverNumber}) async {
    final result = await _authorized(
      'GET',
      'watchlist',
      queryParameters: {'server_number': ?serverNumber},
    );
    final map = result is Map ? Map<String, dynamic>.from(result) : const {};
    return (map['players'] as List? ?? const [])
        .whereType<Map>()
        .map((item) => Map<String, dynamic>.from(item))
        .toList();
  }

  Future<void> watchPlayer(
    String playerId, {
    required String reason,
    int? serverNumber,
    String? playerName,
    String? incidentId,
  }) async {
    await _authorized(
      'PUT',
      'players/${Uri.encodeComponent(playerId)}/watch',
      data: {
        'reason': reason,
        'server_number': ?serverNumber,
        'player_name': ?playerName,
        'incident_id': ?incidentId,
      },
      headers: {'Idempotency-Key': const Uuid().v4()},
    );
  }

  Future<void> unwatchPlayer(
    String playerId, {
    int? serverNumber,
    String? incidentId,
  }) async {
    await _authorized(
      'DELETE',
      'players/${Uri.encodeComponent(playerId)}/watch',
      data: {'server_number': ?serverNumber, 'incident_id': ?incidentId},
      headers: {'Idempotency-Key': const Uuid().v4()},
    );
  }

  Future<Map<String, dynamic>> roster(int serverNumber) async {
    final result = await _authorized('GET', 'servers/$serverNumber/roster');
    if (result is! Map) {
      throw const CrconApiException(
        'CRCON hat keinen gültigen Spielerkader geliefert.',
      );
    }
    return Map<String, dynamic>.from(result);
  }

  Future<Map<String, dynamic>> squad(
    int serverNumber,
    String team,
    String squadName,
  ) async {
    final result = await _authorized(
      'GET',
      'servers/$serverNumber/squads/'
          '${Uri.encodeComponent(team)}/${Uri.encodeComponent(squadName)}',
    );
    if (result is! Map) {
      throw const CrconApiException(
        'CRCON hat keine gültigen Squad-Daten geliefert.',
      );
    }
    return Map<String, dynamic>.from(result);
  }

  Future<Map<String, dynamic>> autobalancerStatus(int serverNumber) async {
    final result = await _authorized(
      'GET',
      'autobalancer',
      queryParameters: {'server_number': serverNumber},
    );
    if (result is! Map) {
      throw const CrconApiException(
        'CRCON hat keinen gültigen Autobalancer-Status geliefert.',
      );
    }
    return Map<String, dynamic>.from(result);
  }

  Future<Map<String, dynamic>> liveStatus(int serverNumber) async {
    final result = await _authorized(
      'GET',
      'servers/$serverNumber/live-status',
    );
    if (result is! Map) {
      throw const CrconApiException(
        'CRCON hat keinen gültigen Serverstatus geliefert.',
      );
    }
    return Map<String, dynamic>.from(result);
  }

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
    final inFlight = _refreshes[profile.id];
    if (inFlight != null) return inFlight;
    final refresh = _refreshTokens();
    _refreshes[profile.id] = refresh;
    try {
      await refresh;
    } finally {
      if (identical(_refreshes[profile.id], refresh)) {
        _refreshes.remove(profile.id);
      }
    }
  }

  Future<void> _refreshTokens() async {
    final refreshToken = await store.refreshToken(profile.id);
    try {
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
    } on CrconApiException catch (error) {
      if (error.statusCode == HttpStatus.unauthorized) {
        throw CrconAuthException(
          'Die CRCON-Kopplung ist abgelaufen. Bitte dieses Gerät neu koppeln.',
          statusCode: error.statusCode,
        );
      }
      rethrow;
    }
  }
}

dynamic decodeCrconResponse(Response<dynamic> response) {
  dynamic payload = response.data;
  if (payload is String) {
    try {
      payload = jsonDecode(payload);
    } on FormatException {
      final status = response.statusCode;
      AppLogger.instance.warning(
        'api',
        'CRCON returned non-JSON data for ${response.requestOptions.method} '
            '${response.requestOptions.uri.path} (HTTP ${status ?? 'unknown'})',
      );
      throw CrconApiException(
        status == HttpStatus.notFound
            ? 'CRCON Mobile API ist noch nicht auf dem benötigten Stand.'
            : 'CRCON hat eine ungültige Antwort geliefert${status == null ? '' : ' (HTTP $status)'}.',
        statusCode: status,
      );
    }
  }
  if (payload is! Map) {
    AppLogger.instance.warning(
      'api',
      'CRCON returned ${payload.runtimeType} instead of an envelope for '
          '${response.requestOptions.method} ${response.requestOptions.uri.path}',
    );
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

Dio _diagnosticDio([BaseOptions? options]) {
  final dio = Dio(options);
  dio.interceptors.add(_DiagnosticInterceptor());
  return dio;
}

class _DiagnosticInterceptor extends Interceptor {
  static const _startedAtKey = 'diagnostics_started_at';

  String _requestLabel(RequestOptions options) =>
      '${options.method.toUpperCase()} ${options.uri.host}${options.uri.path}';

  int? _elapsedMilliseconds(RequestOptions options) {
    final startedAt = options.extra[_startedAtKey];
    return startedAt is int
        ? DateTime.now().millisecondsSinceEpoch - startedAt
        : null;
  }

  @override
  void onRequest(RequestOptions options, RequestInterceptorHandler handler) {
    options.extra[_startedAtKey] = DateTime.now().millisecondsSinceEpoch;
    AppLogger.instance.info('api', '${_requestLabel(options)} started');
    handler.next(options);
  }

  @override
  void onResponse(
    Response<dynamic> response,
    ResponseInterceptorHandler handler,
  ) {
    final elapsed = _elapsedMilliseconds(response.requestOptions);
    AppLogger.instance.info(
      'api',
      '${_requestLabel(response.requestOptions)} -> '
          'HTTP ${response.statusCode ?? 'unknown'}'
          '${elapsed == null ? '' : ' in ${elapsed}ms'}',
    );
    handler.next(response);
  }

  @override
  void onError(DioException error, ErrorInterceptorHandler handler) {
    final elapsed = _elapsedMilliseconds(error.requestOptions);
    final message =
        '${_requestLabel(error.requestOptions)} failed'
        '${error.response?.statusCode == null ? '' : ' with HTTP ${error.response!.statusCode}'}'
        '${elapsed == null ? '' : ' after ${elapsed}ms'}';
    if (error.type == DioExceptionType.connectionError ||
        error.type == DioExceptionType.connectionTimeout ||
        error.type == DioExceptionType.receiveTimeout) {
      AppLogger.instance.warning('api', '$message (network unavailable)');
    } else {
      AppLogger.instance.error(
        'api',
        error.type,
        message: message,
        stackTrace: error.stackTrace,
      );
    }
    handler.next(error);
  }
}
