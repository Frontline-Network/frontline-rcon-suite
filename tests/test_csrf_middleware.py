import os
from unittest import TestCase
from unittest.mock import patch

os.environ.setdefault("HLL_MAINTENANCE_CONTAINER", "1")
os.environ.setdefault("RCONWEB_TEST_MODE", "1")
os.environ.setdefault("SERVER_NUMBER", "1")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "rconweb.rconweb.test_settings")

import django

django.setup()

from django.conf import settings
from django.http import HttpResponse
from django.test import RequestFactory
from django.views.decorators.csrf import csrf_exempt

from rconweb.api import auth
from rconweb.rconweb.csrf import csrf_failure
from rconweb.rconweb.middleware import SessionCsrfProtectionMiddleware


@csrf_exempt
def historically_exempt_view(_request):
    return HttpResponse("ok")


class SessionCsrfProtectionMiddlewareTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.middleware = SessionCsrfProtectionMiddleware(lambda request: HttpResponse())

    def test_exempt_view_rejects_unsafe_browser_session_request_without_token(self):
        request = self.factory.post("/api/change", data="{}", content_type="application/json")
        request.COOKIES[settings.SESSION_COOKIE_NAME] = "browser-session"

        response = self.middleware.process_view(
            request, historically_exempt_view, (), {}
        )

        self.assertEqual(response.status_code, 403)

    def test_exempt_view_keeps_non_session_service_contract(self):
        request = self.factory.post("/api/change", data="{}", content_type="application/json")

        response = self.middleware.process_view(
            request, historically_exempt_view, (), {}
        )

        self.assertIsNone(response)

    def test_read_only_post_routes_keep_browser_session_compatibility(self):
        request = self.factory.post(
            "/api/get_recent_logs", data="{}", content_type="application/json"
        )
        request.COOKIES[settings.SESSION_COOKIE_NAME] = "browser-session"

        response = self.middleware.process_view(
            request, historically_exempt_view, (), {}
        )

        self.assertIsNone(response)

    @patch("rconweb.api.auth.heartbeat")
    @patch("rconweb.api.auth.get_token")
    def test_authenticated_session_check_issues_a_csrf_cookie(
        self, get_token, _heartbeat
    ):
        request = self.factory.get("/api/is_logged_in")
        request.user = type(
            "User", (), {"is_authenticated": True, "username": "admin"}
        )()

        response = auth.is_logged_in(request)

        self.assertEqual(response.status_code, 200)
        get_token.assert_called_once_with(request)

    def test_csrf_failure_reissues_cookie_for_the_next_retry(self):
        request = self.factory.post("/api/change", data="{}", content_type="application/json")

        response = csrf_failure(request, reason="invalid token")
        response = self.middleware.process_response(request, response)

        self.assertEqual(response.status_code, 403)
        self.assertIn(settings.CSRF_COOKIE_NAME, response.cookies)
