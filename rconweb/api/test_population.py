"""Real API-key hashing, Django permissions, routing and session CSRF."""

from unittest.mock import patch

from django.contrib.auth.models import Permission, User
from django.db import connection
from django.db.migrations.loader import MigrationLoader
from django.test import Client, TestCase, override_settings
from django.urls import path

from . import population
from .models import DjangoAPIKey

urlpatterns = [
    path("api/get_player_count_history", population.get_player_count_history),
    path("api/mark_seeding_session", population.mark_seeding_session),
]


@override_settings(
    ROOT_URLCONF=__name__,
    MIDDLEWARE=[
        "django.contrib.sessions.middleware.SessionMiddleware",
        "rconweb.rconweb.middleware.SessionCsrfProtectionMiddleware",
        "django.contrib.auth.middleware.AuthenticationMiddleware",
    ],
)
class PopulationAuthenticationTests(TestCase):
    def setUp(self):
        for target in (
            "api.auth.set_registered_mods",
            "api.population.population.history",
        ):
            patcher = patch(target)
            mock = patcher.start()
            self.addCleanup(patcher.stop)
            if target.endswith("history"):
                mock.return_value = {"points": []}
        self.user = User.objects.create_user(username="population-reader")
        self.key = DjangoAPIKey.objects.create(
            user=self.user, api_key="test-only-population-key"
        )
        self.headers = {"HTTP_AUTHORIZATION": "Bearer test-only-population-key"}
        self.query = {"from": "2026-01-01T00:00:00Z", "to": "2026-01-01T01:00:00Z"}

    def read(self):
        return self.client.get(
            "/api/get_player_count_history", self.query, **self.headers
        )

    def grant(self, codename):
        self.user.user_permissions.add(Permission.objects.get(codename=codename))

    def test_api_key_needs_only_read_permission_and_can_be_revoked(self):
        self.assertNotEqual(self.key.api_key, "test-only-population-key")
        self.assertEqual(self.read().status_code, 403)
        self.grant("can_view_population_history")
        self.assertEqual(self.read().status_code, 200)
        self.assertFalse(self.user.is_staff)
        self.assertFalse(self.user.is_superuser)
        self.assertEqual(
            self.client.post(
                "/api/mark_seeding_session", {}, **self.headers
            ).status_code,
            403,
        )
        self.key.delete()
        self.assertEqual(self.read().status_code, 401)

    def test_inactive_key_owner_and_anonymous_requests_are_denied(self):
        self.grant("can_view_population_history")
        self.user.is_active = False
        self.user.save()
        self.assertEqual(self.read().status_code, 403)
        self.assertEqual(
            self.client.get("/api/get_player_count_history", self.query).status_code,
            401,
        )

    def test_browser_marker_requires_csrf(self):
        self.grant("can_mark_seeding_sessions")
        browser = Client(enforce_csrf_checks=True)
        browser.force_login(self.user)
        response = browser.post("/api/mark_seeding_session", {"action": "start"})
        self.assertEqual(response.status_code, 403)

    def test_permission_migration_is_single_head(self):
        self.assertEqual(
            MigrationLoader(connection).graph.leaf_nodes("api"),
            [("api", "0041_user_appearance_default")],
        )
