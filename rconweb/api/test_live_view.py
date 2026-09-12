import json
from unittest.mock import patch

from django.contrib.auth.models import User
from django.http import HttpResponseForbidden
from django.test import Client, TestCase, override_settings
from django.urls import path

from . import live_view
from .live_view_preferences import default_user_live_view, normalize_live_view
from .models import UserLiveViewPreference

urlpatterns = [
    path("api/get_own_user_live_view", live_view.get_own_user_live_view),
    path("api/set_own_user_live_view", live_view.set_own_user_live_view),
]


def csrf_failure(request, reason=""):
    # Exercise the real CSRF middleware without depending on HTML rendering.
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
class UserLiveViewPreferenceTests(TestCase):
    def setUp(self):
        # Account creation normally publishes online-moderator data to Redis;
        # that unrelated integration is not needed by these database/API tests.
        registered_mods = patch("api.auth.set_registered_mods")
        registered_mods.start()
        self.addCleanup(registered_mods.stop)
        self.user = User.objects.create_user(username="live-one", password="secret")
        self.other = User.objects.create_user(username="live-two", password="secret")
        self.client.force_login(self.user)

    def put(self, payload, client=None):
        return (client or self.client).put(
            "/api/set_own_user_live_view",
            data=json.dumps(payload),
            content_type="application/json",
        )

    def test_default_only_shows_score_and_next_map_without_writing(self):
        response = self.client.get("/api/get_own_user_live_view")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["result"], default_user_live_view())
        self.assertFalse(UserLiveViewPreference.objects.exists())

    def test_account_isolation_and_persistence_across_clients(self):
        preferences = normalize_live_view(
            {"cards": {"commander": True, "vips": True, "score": False}}
        )
        self.assertEqual(self.put(preferences).status_code, 200)
        second_device = Client()
        second_device.force_login(self.user)
        self.assertEqual(
            second_device.get("/api/get_own_user_live_view").json()["result"],
            preferences,
        )
        second_device.force_login(self.other)
        self.assertEqual(
            second_device.get("/api/get_own_user_live_view").json()["result"],
            default_user_live_view(),
        )
        self.assertEqual(UserLiveViewPreference.objects.get().user_id, self.user.pk)

    def test_all_cards_can_be_disabled(self):
        payload = default_user_live_view()
        payload["cards"] = dict.fromkeys(payload["cards"], False)
        self.assertEqual(self.put(payload).json()["result"], payload)

    def test_invalid_inputs_do_not_overwrite_saved_settings(self):
        self.put(default_user_live_view())
        for invalid in [
            [], None, {"cards": []}, {"cards": {"score": "false"}},
            {"cards": {"score": 0}}, {"cards": {"unknown": True}},
            {"version": 2}, {"version": True}, {"user_id": self.other.pk},
        ]:
            with self.subTest(invalid=invalid):
                self.assertEqual(self.put(invalid).status_code, 400)
                self.assertEqual(
                    UserLiveViewPreference.objects.get(user=self.user).preferences,
                    default_user_live_view(),
                )

    def test_unauthenticated_requests_are_rejected(self):
        anonymous = Client()
        self.assertIn(anonymous.get("/api/get_own_user_live_view").status_code, (401, 403))
        self.assertIn(self.put(default_user_live_view(), anonymous).status_code, (401, 403))

    def test_update_requires_csrf(self):
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.user)
        self.assertEqual(self.put(default_user_live_view(), csrf_client).status_code, 403)
        self.assertFalse(UserLiveViewPreference.objects.exists())

    def test_update_accepts_valid_csrf_token(self):
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.user)
        token = "a" * 32
        csrf_client.cookies["csrftoken"] = token
        response = csrf_client.put(
            "/api/set_own_user_live_view",
            data=json.dumps(default_user_live_view()),
            content_type="application/json",
            HTTP_X_CSRFTOKEN=token,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(UserLiveViewPreference.objects.get().user_id, self.user.pk)

    def test_corrupt_saved_settings_fall_back_without_rewriting(self):
        record = UserLiveViewPreference.objects.create(user=self.user, preferences=[])
        self.assertEqual(
            self.client.get("/api/get_own_user_live_view").json()["result"],
            default_user_live_view(),
        )
        record.refresh_from_db()
        self.assertEqual(record.preferences, [])
