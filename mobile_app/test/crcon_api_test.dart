import 'package:crcon_mobile_admin/crcon_api.dart';
import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('decodes a normal CRCON response envelope', () {
    final result = decodeCrconResponse(
      Response<dynamic>(
        requestOptions: RequestOptions(path: '/api/mobile/v1/players/search'),
        statusCode: 200,
        data: '{"failed":false,"result":[{"player_id":"biene"}]}',
      ),
    );

    expect((result as List).single['player_id'], 'biene');
  });

  test('turns an HTML 404 into an actionable backend error', () {
    expect(
      () => decodeCrconResponse(
        Response<dynamic>(
          requestOptions: RequestOptions(path: '/api/mobile/v1/players/search'),
          statusCode: 404,
          data: '<!doctype html><title>Not Found</title>',
        ),
      ),
      throwsA(
        isA<CrconApiException>().having(
          (error) => error.statusCode,
          'statusCode',
          404,
        ),
      ),
    );
  });
}
