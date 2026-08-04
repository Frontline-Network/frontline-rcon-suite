import 'package:crcon_mobile_admin/app_logger.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('redacts credentials before they enter the diagnostic log', () {
    const input =
        'Authorization=Bearer abc.def secret=pairing-secret '
        'refresh_token=refresh-value '
        '{"push_token":"firebase-value","password":"hunter2"}';

    final sanitized = AppLogger.sanitize(input);

    expect(sanitized, isNot(contains('abc.def')));
    expect(sanitized, isNot(contains('pairing-secret')));
    expect(sanitized, isNot(contains('refresh-value')));
    expect(sanitized, isNot(contains('firebase-value')));
    expect(sanitized, isNot(contains('hunter2')));
    expect(sanitized, contains('[REDACTED]'));
  });

  test('truncates excessive messages', () {
    final sanitized = AppLogger.sanitize(
      List.filled(100, 'x').join(),
      maximumLength: 20,
    );
    expect(sanitized, startsWith(List.filled(20, 'x').join()));
    expect(sanitized, endsWith('[TRUNCATED]'));
  });
}
