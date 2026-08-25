import json

from django.contrib.auth.models import User
from django.test import Client, TestCase

from .models import UserAppearancePreference


class UserAppearancePreferenceTests(TestCase):
    def setUp(self):
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
