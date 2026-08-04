import 'package:crcon_mobile_admin/models.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('parses the versioned CRCON pairing URI', () {
    final payload = PairingPayload.parse(
      'crcon://pair?v=1&base=https%3A%2F%2Fcrcon.example.org'
      '&pairing_id=6e3669b4-2047-4b61-b57b-62ec107d4f63&secret=one-time',
    );

    expect(payload.baseUrl, 'https://crcon.example.org');
    expect(payload.pairingId, '6e3669b4-2047-4b61-b57b-62ec107d4f63');
    expect(payload.secret, 'one-time');
  });

  test('rejects a non-CRCON QR code', () {
    expect(
      () => PairingPayload.parse('https://example.org'),
      throwsFormatException,
    );
  });
}
