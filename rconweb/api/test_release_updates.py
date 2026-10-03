import json
from unittest.mock import patch

from django.contrib.auth.models import AnonymousUser, User
from django.test import RequestFactory, TestCase, override_settings

from .release_updates import get_update_channel


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
