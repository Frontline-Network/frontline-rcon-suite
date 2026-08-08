import 'package:crcon_mobile_admin/firebase_options.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('uses the registered Frontline Firebase web app', () {
    expect(webFirebaseOptions.projectId, 'frontline-6cb8a');
    expect(webFirebaseOptions.appId, startsWith('1:1050619413922:web:'));
  });
}
