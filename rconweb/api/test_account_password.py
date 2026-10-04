import re
from datetime import datetime, timedelta
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core import mail
from django.core.cache import cache
from django.test import Client, TestCase, override_settings
from django.urls import include, path

urlpatterns = [path("accounts/", include("api.account_urls"))]
CHANGE = "/accounts/password_change/"
RESET = "/accounts/password_reset/"
JSON = {"HTTP_ACCEPT": "application/json"}
OLD = "previous-test-password-749!"
NEW = "new-test-password-182!long"


@override_settings(
    ROOT_URLCONF=__name__,
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    CRCON_PASSWORD_RESET_ENABLED=True,
    CRCON_PUBLIC_URL="https://rcon.example.test",
    DEFAULT_FROM_EMAIL="CRCON <noreply@example.test>",
    PASSWORD_RESET_TIMEOUT=1800,
)
class AccountPasswordTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user("operator", "operator@example.test", OLD)
        self.other = User.objects.create_user("other", "other@example.test", OLD)
        self.client.force_login(self.user)

    def change_payload(self, **overrides):
        return {"old_password": OLD, "new_password1": NEW, "new_password2": NEW, **overrides}

    def request_reset(self, email="operator@example.test", client=None):
        return (client or self.client).post(RESET + "?ui_language=de", {"email": email}, **JSON)

    def reset_link(self):
        self.request_reset()
        return re.search(r"https://rcon\.example\.test(/accounts/reset/[^\s?]+)", mail.outbox[-1].body).group(1)

    def prepare_reset(self, client, link):
        response = client.get(link)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response["Location"].rstrip("/").endswith("/set-password"))
        url = response["Location"]
        data = client.get(url, **JSON).json()
        return url, data["csrf_token"]

    def test_regular_user_can_load_localized_form_without_admin_access(self):
        response = self.client.get(CHANGE + "?ui_language=de", **JSON)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(self.user.is_staff)
        self.assertEqual(response.json()["username"], "operator")
        self.assertEqual(len(response.json()["requirements"]), 4)
        self.assertIn("Zeichen", " ".join(response.json()["requirements"]))
        self.assertIn("no-store", response["Cache-Control"])
        self.assertNotContains(response, OLD)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(OLD))

    def test_legacy_url_redirects_into_the_rcon(self):
        for path in (CHANGE, CHANGE.rstrip("/")):
            self.assertRedirects(self.client.get(path), "/account/password", fetch_redirect_response=False)

    def test_anonymous_requests_cannot_change_a_password(self):
        client = Client()
        self.assertRedirects(client.get(CHANGE), "/login?from=%2Faccount%2Fpassword", fetch_redirect_response=False)
        self.assertEqual(client.get(CHANGE, **JSON).status_code, 401)
        self.assertEqual(client.post(CHANGE, self.change_payload(), **JSON).status_code, 401)

    def test_wrong_current_password_and_weak_or_mismatched_new_password_are_rejected(self):
        for overrides, field in (
            ({"old_password": "wrong"}, "old_password"),
            ({"new_password1": "123", "new_password2": "123"}, "new_password2"),
            ({"new_password2": "different"}, "new_password2"),
        ):
            with self.subTest(field=field):
                response = self.client.post(CHANGE, self.change_payload(**overrides), **JSON)
                self.assertEqual(response.status_code, 400)
                self.assertIn(field, response.json()["errors"])
                self.assertNotIn(OLD, response.content.decode())
                self.assertNotIn(NEW, response.content.decode())
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(OLD))

    def test_change_only_updates_current_user_and_preserves_current_session(self):
        second_session = Client()
        second_session.force_login(self.user)
        response = self.client.post(CHANGE, self.change_payload(user_id=self.other.pk), **JSON)
        self.assertEqual(response.json(), {"changed": True})
        self.user.refresh_from_db()
        self.other.refresh_from_db()
        self.assertTrue(self.user.check_password(NEW))
        self.assertTrue(self.other.check_password(OLD))
        self.assertEqual(self.client.get(CHANGE, **JSON).status_code, 200)
        self.assertEqual(second_session.get(CHANGE, **JSON).status_code, 401)

    def test_csrf_is_required_even_for_anonymous_reset_requests(self):
        client = Client(enforce_csrf_checks=True)
        self.assertEqual(client.post(RESET, {"email": self.user.email}, **JSON).status_code, 403)
        client.force_login(self.user)
        self.assertEqual(client.post(CHANGE, self.change_payload(), **JSON).status_code, 403)
        token = client.get(CHANGE, **JSON).json()["csrf_token"]
        self.assertEqual(client.post(CHANGE, self.change_payload(), HTTP_X_CSRFTOKEN=token, HTTP_ORIGIN="https://hostile.example", **JSON).status_code, 403)
        self.assertEqual(client.post(CHANGE, self.change_payload(), HTTP_X_CSRFTOKEN=token, **JSON).status_code, 200)

    def test_reset_request_does_not_disclose_account_existence_or_status(self):
        inactive = User.objects.create_user("inactive", "inactive@example.test", OLD, is_active=False)
        external = User.objects.create_user("external", "external@example.test")
        expected = self.request_reset().json()
        for email in ("missing@example.test", inactive.email, external.email):
            response = self.request_reset(email)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json(), expected)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [self.user.email])
        self.assertIn("30 Minuten", mail.outbox[0].body)
        self.assertNotIn(OLD, mail.outbox[0].body)

    def test_email_uses_configured_origin_not_request_host(self):
        self.client.post(RESET, {"email": self.user.email}, HTTP_HOST="localhost", **JSON)
        self.assertIn("https://rcon.example.test/accounts/reset/", mail.outbox[0].body)
        self.assertNotIn("http://localhost", mail.outbox[0].body)

    def test_reset_link_is_session_bound_single_use_and_does_not_auto_login(self):
        link = self.reset_link()
        client = Client(enforce_csrf_checks=True)
        url, token = self.prepare_reset(client, link)
        self.assertEqual(Client().get(url, **JSON).json(), {"error": "invalid_link"})
        values = {"new_password1": NEW, "new_password2": NEW}
        self.assertEqual(client.post(url, values, **JSON).status_code, 403)
        result = client.post(url, values, HTTP_X_CSRFTOKEN=token, **JSON)
        self.assertEqual(result.json(), {"changed": True})
        self.assertEqual(client.get(CHANGE, **JSON).status_code, 401)
        self.assertEqual(client.get(url, **JSON).json(), {"error": "invalid_link"})
        self.assertEqual(Client().get(link, **JSON).json(), {"error": "invalid_link"})
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(NEW))
        self.assertEqual(self.client.get(CHANGE, **JSON).status_code, 401)

    def test_expired_and_malformed_links_are_rejected(self):
        link = self.reset_link()
        with patch("django.contrib.auth.tokens.PasswordResetTokenGenerator._now", return_value=datetime.now() + timedelta(hours=1)):
            self.assertEqual(Client().get(link, **JSON).json(), {"error": "invalid_link"})
        self.assertEqual(Client().get("/accounts/reset/bad/invalid/", **JSON).json(), {"error": "invalid_link"})

    def test_reset_form_validation_keeps_the_link_usable(self):
        client = Client()
        url, _ = self.prepare_reset(client, self.reset_link())
        response = client.post(url, {"new_password1": "123", "new_password2": "123"}, **JSON)
        self.assertEqual(response.status_code, 400)
        self.assertIn("new_password2", response.json()["errors"])
        self.assertEqual(client.get(url, **JSON).status_code, 200)

    def test_deactivated_account_cannot_use_previously_issued_link(self):
        link = self.reset_link()
        self.user.is_active = False
        self.user.save(update_fields=["is_active"])
        self.assertEqual(Client().get(link, **JSON).json(), {"error": "invalid_link"})

    def test_email_rate_limit_is_independent_of_account_existence(self):
        for _ in range(5):
            self.assertEqual(self.request_reset().json(), {"sent": True})
        self.assertEqual(len(mail.outbox), 3)

    def test_ip_rate_limit_applies_across_different_addresses(self):
        client = Client()
        for number in range(10):
            self.assertEqual(self.request_reset("missing" + str(number) + "@example.test", client).status_code, 200)
        response = self.request_reset("another@example.test", client)
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response["Retry-After"], "900")

    def test_smtp_failure_does_not_reveal_the_recipient(self):
        with patch("api.account_views.EmailMultiAlternatives.send", side_effect=OSError("secret SMTP failure")):
            response = self.request_reset()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"sent": True})
        self.assertNotContains(response, "SMTP")

    def test_cache_failure_prevents_unlimited_email_requests(self):
        with patch("api.account_views.cache.add", side_effect=OSError("cache unavailable")):
            response = self.request_reset()
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {"error": "temporarily_unavailable"})
        self.assertEqual(len(mail.outbox), 0)

    @override_settings(CRCON_PASSWORD_RESET_ENABLED=False)
    def test_unconfigured_email_recovery_is_explicitly_unavailable(self):
        self.assertFalse(self.client.get(RESET, **JSON).json()["available"])
        self.assertEqual(self.request_reset().status_code, 503)
