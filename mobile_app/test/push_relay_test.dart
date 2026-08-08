import 'package:flutter_test/flutter_test.dart';
import 'package:crcon_mobile_admin/push_relay.dart';
import 'package:crcon_mobile_admin/secure_store.dart';

class _MemoryPushRelayIdentityStore implements PushRelayIdentityStore {
  Map<String, String>? identity;

  @override
  Future<Map<String, String>?> readPushRelayIdentity() async => identity;

  @override
  Future<void> writePushRelayIdentity({
    required String baseUrl,
    required String pushToken,
    required String handle,
    required String capability,
  }) async {
    identity = {
      'base_url': baseUrl,
      'push_token': pushToken,
      'handle': handle,
      'capability': capability,
    };
  }
}

void main() {
  test('reuses a cached relay identity for an unchanged push token', () async {
    final store = _MemoryPushRelayIdentityStore();
    var registrations = 0;

    Future<Map<String, dynamic>> registrar(
      String endpoint,
      String token,
    ) async {
      registrations += 1;
      expect(endpoint, 'https://push.example.org/v1/devices');
      expect(token, 'push-token-a');
      return {
        'handle': 'device-handle',
        'notify_capability': 'notify-capability',
      };
    }

    final first = await PushRelay.register(
      store,
      relayBaseUrl: 'https://push.example.org/',
      tokenProvider: () async => 'push-token-a',
      registrar: registrar,
    );
    final second = await PushRelay.register(
      store,
      relayBaseUrl: 'https://push.example.org/',
      tokenProvider: () async => 'push-token-a',
      registrar: registrar,
    );

    expect(registrations, 1);
    expect(first?.handle, 'device-handle');
    expect(second?.handle, first?.handle);
    expect(second?.capability, first?.capability);
  });

  test('registers again after the push token changes', () async {
    final store = _MemoryPushRelayIdentityStore();
    var token = 'push-token-a';
    var registrations = 0;

    Future<Map<String, dynamic>> registrar(
      String endpoint,
      String value,
    ) async {
      registrations += 1;
      return {
        'handle': 'device-$value',
        'notify_capability': 'capability-$value',
      };
    }

    await PushRelay.register(
      store,
      relayBaseUrl: 'https://push.example.org',
      tokenProvider: () async => token,
      registrar: registrar,
    );
    token = 'push-token-b';
    final refreshed = await PushRelay.register(
      store,
      relayBaseUrl: 'https://push.example.org',
      tokenProvider: () async => token,
      registrar: registrar,
    );

    expect(registrations, 2);
    expect(refreshed?.handle, 'device-push-token-b');
  });
}
