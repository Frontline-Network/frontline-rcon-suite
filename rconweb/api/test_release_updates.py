import json
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth.models import AnonymousUser, User
from django.core.cache import cache
from django.test import Client, RequestFactory, TestCase, override_settings
from django.urls import path
from django.utils import timezone
from django.http import HttpResponseForbidden

from .release_updates import get_update_channel, set_own_release_highlight_state
from .models import UserReleaseHighlightState

urlpatterns = [
    path("api/get_update_channel", get_update_channel),
    path("api/set_own_release_highlight_state", set_own_release_highlight_state),
]


def csrf_failure(request, reason=""):
    return HttpResponseForbidden("CSRF verification failed")


@override_settings(TAG_VERSION="v0.8.8")
class ReleaseUpdateAccessTests(TestCase):
    def request(self, method="get", authenticated=True, **params):
        request = getattr(RequestFactory(), method)("/api/get_update_channel", params)
        request.user = User(pk=17, username="reader") if authenticated else AnonymousUser()
        return request

    @patch("api.release_updates.get_channel")
    def test_anonymous_cannot_read_private_notes(self, channel):
        response = get_update_channel(self.request(authenticated=False))
        self.assertEqual(response.status_code, 401)
        channel.assert_not_called()

    @patch("api.release_updates.get_channel")
    def test_only_get_is_allowed(self, channel):
        self.assertEqual(get_update_channel(self.request("post")).status_code, 405)
        channel.assert_not_called()

    @patch("api.release_updates.get_channel", return_value={"status": "ready", "releases": []})
    def test_installation_version_is_server_owned_and_response_is_private(self, channel):
        response = get_update_channel(self.request(frontend_version="v0.8.8", installed_version="v99.0.0"))
        self.assertEqual(channel.call_args.args[:2], ("v0.8.8", "v0.8.8"))
        self.assertEqual(response["Cache-Control"], "private, no-store")
        self.assertEqual(json.loads(response.content)["result"]["status"], "ready")
        self.assertEqual(json.loads(response.content)["result"]["reader_id"], "17")


@override_settings(TAG_VERSION="v0.8.8", ROOT_URLCONF=__name__,
                   CSRF_FAILURE_VIEW=f"{__name__}.csrf_failure",
                   MIDDLEWARE=["django.contrib.sessions.middleware.SessionMiddleware",
                               "rconweb.rconweb.middleware.SessionCsrfProtectionMiddleware",
                               "django.contrib.auth.middleware.AuthenticationMiddleware"])
class ReleaseHighlightStateTests(TestCase):
    def setUp(self):
        registry = patch("api.auth.set_registered_mods")
        registry.start()
        self.addCleanup(registry.stop)
        self.user = User.objects.create_user(username="reader", password="test-only")
        self.other_user = User.objects.create_user(username="other", password="test-only")
        self.client.force_login(self.user)
        self.channel = {"status": "ready", "releases": [{"tag_name": "v0.8.8", "current": True, "highlights": {"schema_version": 1}}]}
        source = patch("api.release_updates.get_channel", return_value=self.channel)
        self.source = source.start()
        self.addCleanup(source.stop)

    def post(self, action="claim", client=None, **extra):
        return (client or self.client).post("/api/set_own_release_highlight_state", data=json.dumps({
            "frontend_version": "v0.8.8", "release_version": "v0.8.8", "action": action, **extra
        }), content_type="application/json")

    def read(self, client=None):
        return (client or self.client).get("/api/get_update_channel?frontend_version=v0.8.8").json()["result"]["highlight_state"]

    def test_first_claim_only_and_seen_state_survives_another_device(self):
        self.assertTrue(self.read()["auto_show"])
        first = self.post()
        self.assertEqual(first["Cache-Control"], "private, no-store")
        self.assertTrue(first.json()["result"]["show"])
        second_device = Client()
        second_device.force_login(self.user)
        self.assertTrue(self.read(second_device)["seen"])
        self.assertFalse(self.post(client=second_device).json()["result"]["show"])
        self.assertEqual(UserReleaseHighlightState.objects.count(), 1)

    def test_state_is_bound_to_account_and_not_changelog(self):
        self.post("seen")
        self.client.force_login(self.other_user)
        self.assertTrue(self.read()["auto_show"])
        self.assertTrue(self.post().json()["result"]["show"])

    def test_later_snoozes_24_hours_and_can_be_reopened_manually(self):
        now = timezone.now()
        with patch("api.release_updates.timezone.now", return_value=now):
            self.post()
            state = self.post("later").json()["result"]
            self.assertFalse(state["auto_show"])
            self.assertFalse(state["seen"])
            self.assertEqual(state["snoozed_until"], (now + timedelta(hours=24)).isoformat())
            self.assertFalse(self.post().json()["result"]["show"])
        with patch("api.release_updates.timezone.now", return_value=now + timedelta(hours=24, seconds=1)):
            self.assertTrue(self.read()["auto_show"])
            self.assertTrue(self.post().json()["result"]["show"])
        self.post("later")
        self.post("seen")
        self.assertTrue(self.read()["seen"])
        self.assertIsNone(self.read()["snoozed_until"])

    def test_uninstalled_version_and_unverified_channel_cannot_be_acknowledged(self):
        self.assertEqual(self.post(release_version="v0.8.9").status_code, 409)
        self.source.return_value = {"status": "version_mismatch", "releases": []}
        self.assertEqual(self.post(frontend_version="v0.8.7").status_code, 409)
        self.assertIsNone(self.read())
        self.assertFalse(UserReleaseHighlightState.objects.exists())
        self.source.assert_called_with("v0.8.8", "v0.8.8", cache)

    def test_invalid_payload_other_user_and_http_method_are_rejected(self):
        for extra in ({"user_id": self.other_user.pk}, {"action": "delete"}, {"release_version": []}):
            self.assertEqual(self.post(**extra).status_code, 400)
        self.assertEqual(self.client.get("/api/set_own_release_highlight_state").status_code, 405)
        self.assertFalse(UserReleaseHighlightState.objects.exists())

    def test_anonymous_and_missing_csrf_are_rejected(self):
        self.assertEqual(self.post(client=Client()).status_code, 401)
        browser = Client(enforce_csrf_checks=True)
        browser.force_login(self.user)
        self.assertEqual(self.post(client=browser).status_code, 403)
        self.assertFalse(UserReleaseHighlightState.objects.exists())

    def test_equivalent_version_tags_share_one_record(self):
        self.post(release_version="0.8.8")
        self.assertFalse(self.post().json()["result"]["show"])
        self.assertEqual(UserReleaseHighlightState.objects.get().release_version, "v0.8.8")

    def test_release_without_curated_highlights_does_not_create_state(self):
        self.channel["releases"][0]["highlights"] = None
        self.assertIsNone(self.read())
        self.assertEqual(self.post().status_code, 409)
        self.assertFalse(UserReleaseHighlightState.objects.exists())

    def test_new_release_has_its_own_state_and_rollback_keeps_old_acknowledgement(self):
        self.post("seen")
        self.channel["releases"][0]["tag_name"] = "v0.8.9"
        with override_settings(TAG_VERSION="v0.8.9"):
            response = self.post(frontend_version="v0.8.9", release_version="v0.8.9")
            self.assertTrue(response.json()["result"]["show"])
        self.channel["releases"][0]["tag_name"] = "v0.8.8"
        self.assertFalse(self.post().json()["result"]["show"])
        self.assertEqual(UserReleaseHighlightState.objects.count(), 2)
