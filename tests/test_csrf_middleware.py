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

try:
    # Django registers the historical application as ``api``. Import it under
    # that canonical name so model classes are not loaded a second time through
    # the repository-root ``rconweb.api`` namespace.
    from api import auth, views
    from api import urls as api_urls
    from api.decorators import ENDPOINT_HTTP_METHODS
    from rconweb.csrf import csrf_failure
    from rconweb.middleware import READ_ONLY_POST_PATHS, SessionCsrfProtectionMiddleware
except ModuleNotFoundError:
    from rconweb.api import auth, views
    from rconweb.api import urls as api_urls
    from rconweb.api.decorators import ENDPOINT_HTTP_METHODS
    from rconweb.rconweb.csrf import csrf_failure
    from rconweb.rconweb.middleware import (
        READ_ONLY_POST_PATHS,
        SessionCsrfProtectionMiddleware,
    )


@csrf_exempt
def historically_exempt_view(_request):
    return HttpResponse("ok")


class SessionCsrfProtectionMiddlewareTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.middleware = SessionCsrfProtectionMiddleware(
            lambda request: HttpResponse()
        )

    def test_exempt_view_rejects_unsafe_browser_session_request_without_token(self):
        request = self.factory.post(
            "/api/change", data="{}", content_type="application/json"
        )
        request.COOKIES[settings.SESSION_COOKIE_NAME] = "browser-session"

        response = self.middleware.process_view(
            request, historically_exempt_view, (), {}
        )
        response = self.middleware.process_response(request, response)

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response["X-CRCON-CSRF-Recovery"], "1")
        self.assertTrue(response["X-CRCON-CSRF-Token"])
        self.assertIn(settings.CSRF_COOKIE_NAME, response.cookies)

    def test_exempt_view_keeps_non_session_service_contract(self):
        request = self.factory.post(
            "/api/change", data="{}", content_type="application/json"
        )

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

    def test_every_registered_mutating_api_endpoint_rejects_missing_csrf(self):
        protected = []
        for endpoint_name, callback in api_urls.endpoints:
            methods = ENDPOINT_HTTP_METHODS.get(callback.__name__, [])
            if not any(
                method not in {"GET", "HEAD", "OPTIONS", "TRACE"}
                for method in methods
            ):
                continue

            request = self.factory.post(
                f"/api/{endpoint_name}", data="{}", content_type="application/json"
            )
            request.COOKIES[settings.SESSION_COOKIE_NAME] = "browser-session"
            response = self.middleware.process_view(request, callback, (), {})

            self.assertIsNotNone(response, endpoint_name)
            self.assertEqual(response.status_code, 403, endpoint_name)
            protected.append(endpoint_name)

        generated_unsafe = [
            (func, methods)
            for func, methods in views.RCON_ENDPOINT_HTTP_METHODS.items()
            if any(
                method not in {"GET", "HEAD", "OPTIONS", "TRACE"}
                for method in methods
            )
        ]
        for func, _methods in generated_unsafe:
            if f"/api/{func.__name__}" in READ_ONLY_POST_PATHS:
                continue
            callback = views.expose_api_endpoint(
                func=func,
                command_name=func.__name__,
                permissions=views.ENDPOINT_PERMISSIONS[func],
                endpoint_allowed_http_methods=views.RCON_ENDPOINT_HTTP_METHODS,
            )
            request = self.factory.post(
                f"/api/{func.__name__}", data="{}", content_type="application/json"
            )
            request.COOKIES[settings.SESSION_COOKIE_NAME] = "browser-session"
            response = self.middleware.process_view(request, callback, (), {})

            self.assertIsNotNone(response, func.__name__)
            self.assertEqual(response.status_code, 403, func.__name__)

        # Guard against an import/registration regression making this audit a
        # vacuous pass. Both the hand-written and generated browser APIs expose
        # many writes in production.
        self.assertGreaterEqual(len(protected), 15)
        self.assertGreaterEqual(len(generated_unsafe), 50)

    @patch.object(auth, "heartbeat")
    @patch.object(auth, "get_token")
    def test_authenticated_session_check_issues_a_csrf_cookie(
        self, get_token, _heartbeat
    ):
        request = self.factory.get("/api/is_logged_in")
        request.user = type(
            "User", (), {"is_authenticated": True, "username": "admin", "pk": 1}
        )()

        response = auth.is_logged_in(request)

        self.assertEqual(response.status_code, 200)
        get_token.assert_called_once_with(request)

    def test_csrf_failure_marks_response_and_reissues_cookie_for_retry(self):
        request = self.factory.post(
            "/api/change", data="{}", content_type="application/json"
        )

        response = csrf_failure(request, reason="invalid token")
        response = self.middleware.process_response(request, response)

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response["X-CRCON-CSRF-Recovery"], "1")
        self.assertTrue(response["X-CRCON-CSRF-Token"])
        self.assertIn(settings.CSRF_COOKIE_NAME, response.cookies)

    def test_recovery_token_authorizes_exactly_the_follow_up_request(self):
        rejected = self.factory.post(
            "/api/change", data="{}", content_type="application/json"
        )
        rejected.COOKIES[settings.SESSION_COOKIE_NAME] = "browser-session"
        rejected.COOKIES[settings.CSRF_COOKIE_NAME] = "a" * 32

        response = csrf_failure(rejected, reason="invalid header")
        response = self.middleware.process_response(rejected, response)

        retry = self.factory.post(
            "/api/change",
            data="{}",
            content_type="application/json",
            HTTP_X_CSRFTOKEN=response["X-CRCON-CSRF-Token"],
        )
        retry.COOKIES[settings.SESSION_COOKIE_NAME] = "browser-session"
        retry.COOKIES[settings.CSRF_COOKIE_NAME] = response.cookies[
            settings.CSRF_COOKIE_NAME
        ].value

        self.assertIsNone(
            self.middleware.process_view(retry, historically_exempt_view, (), {})
        )


class BrowserCookieSecuritySettingsTests(TestCase):
    def test_authenticated_cookies_are_https_only(self):
        self.assertTrue(settings.SESSION_COOKIE_SECURE)
        self.assertTrue(settings.CSRF_COOKIE_SECURE)

    def test_traefik_https_forwarding_is_recognized(self):
        self.assertEqual(
            settings.SECURE_PROXY_SSL_HEADER,
            ("HTTP_X_FORWARDED_PROTO", "https"),
        )
