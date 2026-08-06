import 'dart:async';

import 'app_logger.dart';
import 'crcon_api.dart';
import 'models.dart';
import 'secure_store.dart';

/// Browser live refresh uses short polling until the web gateway issues its
/// session cookie. Browsers cannot attach the native Bearer header while
/// opening a WebSocket, and putting an access token in its URL is unsafe.
class CrconLiveUpdates {
  CrconLiveUpdates(this.profile, this.store);

  final ConnectionProfile profile;
  final SecureConnectionStore store;
  Timer? _timer;
  bool _stopped = false;

  Future<void> start(
    void Function(Map<String, dynamic> incident) onIncident,
  ) async {
    await _refresh(onIncident);
    if (_stopped) return;
    _timer = Timer.periodic(const Duration(seconds: 12), (_) {
      unawaited(_refresh(onIncident));
    });
  }

  Future<void> _refresh(
    void Function(Map<String, dynamic> incident) onIncident,
  ) async {
    if (_stopped) return;
    try {
      final incidents = await CrconApi(profile, store).listIncidents();
      if (incidents.isNotEmpty) onIncident(incidents.first);
    } on CrconAuthException {
      AppLogger.instance.warning(
        'web',
        'Live refresh stopped; the Frontline Web session is no longer valid',
      );
      await dispose();
    } catch (error, stackTrace) {
      AppLogger.instance.warning(
        'web',
        'Live refresh unavailable: $error',
        error: stackTrace,
      );
    }
  }

  Future<void> dispose() async {
    _stopped = true;
    _timer?.cancel();
    _timer = null;
  }
}
