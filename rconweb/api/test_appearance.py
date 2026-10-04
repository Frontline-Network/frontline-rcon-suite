import json
from unittest.mock import patch

from django.contrib.auth.models import User
from django.http import HttpResponseForbidden
from django.test import Client, TestCase, override_settings
from django.urls import path

from .appearance import get_own_user_appearance, set_own_user_appearance
from .models import UserAppearancePreference

urlpatterns = [
    path("api/get_own_user_appearance", get_own_user_appearance),
    path("api/set_own_user_appearance", set_own_user_appearance),
]

def csrf_failure(request, reason=""):
    return HttpResponseForbidden("CSRF verification failed")


@override_settings(
    ROOT_URLCONF=__name__,
    CSRF_FAILURE_VIEW=f"{__name__}.csrf_failure",
    MIDDLEWARE=[
        "django.contrib.sessions.middleware.SessionMiddleware",
        "rconweb.rconweb.middleware.SessionCsrfProtectionMiddleware",
        "django.contrib.auth.middleware.AuthenticationMiddleware",
    ],
)
class UserAppearancePreferenceTests(TestCase):
    def setUp(self):
        # Account creation also updates the live moderator registry. Preference
        # tests exercise the database and HTTP API without a running game/Redis.
        moderator_registry = patch("api.auth.set_registered_mods")
        moderator_registry.start()
        self.addCleanup(moderator_registry.stop)
        self.first_user = User.objects.create_user(
            username="appearance-one", password="secret"
        )
        self.second_user = User.objects.create_user(
            username="appearance-two", password="secret"
        )
        self.client.force_login(self.first_user)

    def test_default_preferences_are_versioned_and_account_bound(self):
        response = self.client.get("/api/get_own_user_appearance")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["result"],
            {
                "version": 1,
                "mode": "dark",
                "preset": "frontline-gold",
                "customAccent": "#c59a4a",
                "colorVision": "standard",
                "wardogsStyle": "rose",
                "wardogsShortcuts": ["/settings/broadcast-message", "/records/players"],
            },
        )
        self.assertEqual(
            UserAppearancePreference.objects.get().user_id, self.first_user.pk
        )

    def test_preferences_do_not_leak_between_users(self):
        payload = {
            "version": 1,
            "mode": "system",
            "preset": "tactical-blue",
            "customAccent": "#478ac9",
            "colorVision": "deuteranopia",
            "wardogsStyle": "rose",
            "wardogsShortcuts": ["/views/live-map", "/views/autobalancer"],
        }
        updated = self.client.put(
            "/api/set_own_user_appearance",
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()["result"], payload)

        other_client = Client()
        other_client.force_login(self.second_user)
        other = other_client.get("/api/get_own_user_appearance")
        self.assertEqual(other.status_code, 200)
        self.assertEqual(other.json()["result"]["preset"], "frontline-gold")
        self.assertEqual(other.json()["result"]["colorVision"], "standard")
        self.assertEqual(other.json()["result"]["wardogsShortcuts"], ["/settings/broadcast-message", "/records/players"])

    def test_invalid_custom_color_is_rejected_without_overwriting(self):
        response = self.client.put(
            "/api/set_own_user_appearance",
            data=json.dumps(
                {
                    "mode": "dark",
                    "preset": "custom",
                    "customAccent": "red",
                    "colorVision": "standard",
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(
            UserAppearancePreference.objects.filter(user=self.first_user).exists()
        )

    def test_wardogs_survives_save_and_reload_in_each_display_mode(self):
        for mode in ("dark", "light", "system"):
            with self.subTest(mode=mode):
                payload = {
                    "version": 1,
                    "mode": mode,
                    "preset": "wardogs",
                    "customAccent": "#e45b80",
                    "colorVision": "deuteranopia",
                    "wardogsStyle": "rose",
                    "wardogsShortcuts": ["/views/live-map", "/records/players"],
                }
                updated = self.client.put(
                    "/api/set_own_user_appearance",
                    data=json.dumps(payload),
                    content_type="application/json",
                )
                self.assertEqual(updated.status_code, 200)
                self.assertEqual(updated.json()["result"], payload)
                reloaded = self.client.get("/api/get_own_user_appearance")
                self.assertEqual(reloaded.status_code, 200)
                self.assertEqual(reloaded.json()["result"], payload)
                self.assertEqual(
                    UserAppearancePreference.objects.get(user=self.first_user).preferences,
                    payload,
                )

    def test_shortcuts_preserve_order_allow_empty_and_remove_duplicates(self):
        for routes, expected in [
            (["/views/live-map", "/records/players", "/views/live-map"], ["/views/live-map", "/records/players"]),
            ([], []),
        ]:
            response = self.client.put("/api/set_own_user_appearance", data=json.dumps({"wardogsShortcuts": routes}), content_type="application/json")
            self.assertEqual(response.status_code, 200)
            reloaded = self.client.get("/api/get_own_user_appearance")
            self.assertEqual(reloaded.json()["result"]["wardogsShortcuts"], expected)

    def test_invalid_shortcut_payload_does_not_overwrite_saved_selection(self):
        saved = ["/views/live-map"]
        self.client.put("/api/set_own_user_appearance", data=json.dumps({"wardogsShortcuts": saved}), content_type="application/json")
        for value in [None, "invalid", ["https://example.org"], ["//example.org"], ["/../login"], ["/views/live?token=x"], [False], ["/views/live"] * 65]:
            with self.subTest(value=value):
                response = self.client.put("/api/set_own_user_appearance", data=json.dumps({"wardogsShortcuts": value}), content_type="application/json")
                self.assertEqual(response.status_code, 400)
                self.assertEqual(UserAppearancePreference.objects.get(user=self.first_user).preferences["wardogsShortcuts"], saved)

    def test_older_theme_client_preserves_shortcuts(self):
        self.client.put("/api/set_own_user_appearance", data=json.dumps({"wardogsShortcuts": ["/views/live-map"]}), content_type="application/json")
        updated = self.client.put("/api/set_own_user_appearance", data=json.dumps({"preset": "neutral"}), content_type="application/json")
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()["result"]["wardogsShortcuts"], ["/views/live-map"])

    def test_unsafe_update_requires_csrf(self):
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.first_user)
        response = csrf_client.put(
            "/api/set_own_user_appearance",
            data=json.dumps(
                {
                    "mode": "dark",
                    "preset": "neutral",
                    "customAccent": "#a9aca8",
                    "colorVision": "standard",
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)

    def test_wardogs_styles_roundtrip_without_changing_theme_or_shortcuts(self):
        from .wardogs_styles import WARDOGS_STYLES
        for style in WARDOGS_STYLES:
            with self.subTest(style=style):
                response = self.client.put("/api/set_own_user_appearance", data=json.dumps({
                    "preset": "wardogs", "wardogsStyle": style,
                    "colorVision": "tritanopia", "wardogsShortcuts": ["/views/live"],
                }), content_type="application/json")
                self.assertEqual(response.status_code, 200)
                saved = self.client.get("/api/get_own_user_appearance").json()["result"]
                self.assertEqual(saved["wardogsStyle"], style)
                self.assertEqual(saved["preset"], "wardogs")
                self.assertEqual(saved["colorVision"], "tritanopia")
                self.assertEqual(saved["wardogsShortcuts"], ["/views/live"])

    def test_invalid_style_does_not_overwrite_preferences(self):
        self.client.put("/api/set_own_user_appearance", data=json.dumps({"wardogsStyle": "blue"}), content_type="application/json")
        for value in (None, [], {}, 5, "custom", "unknown"):
            with self.subTest(value=value):
                response = self.client.put("/api/set_own_user_appearance", data=json.dumps({"wardogsStyle": value}), content_type="application/json")
                self.assertEqual(response.status_code, 400)
                self.assertEqual(UserAppearancePreference.objects.get(user=self.first_user).preferences["wardogsStyle"], "blue")

    def test_older_client_preserves_style_but_can_update_shortcuts(self):
        self.client.put("/api/set_own_user_appearance", data=json.dumps({"wardogsStyle": "violet"}), content_type="application/json")
        response = self.client.put("/api/set_own_user_appearance", data=json.dumps({"wardogsShortcuts": ["/views/team"]}), content_type="application/json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["result"]["wardogsStyle"], "violet")
        self.assertEqual(response.json()["result"]["wardogsShortcuts"], ["/views/team"])

    def test_legacy_saved_preferences_default_to_original_rose(self):
        UserAppearancePreference.objects.create(user=self.first_user, preferences={"preset": "wardogs"})
        saved = self.client.get("/api/get_own_user_appearance").json()["result"]
        self.assertEqual(saved["wardogsStyle"], "rose")
        self.assertEqual(saved["preset"], "wardogs")
