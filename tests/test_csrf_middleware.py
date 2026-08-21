import os
from unittest import TestCase

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
