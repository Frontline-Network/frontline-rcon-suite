import json
from datetime import timedelta
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

from django.contrib.auth.models import Group, User
from django.test import Client, TestCase
from django.utils import timezone

from .models import MobileAccessToken, MobileDevice, MobilePairing


@patch.dict(
    "os.environ",
    {
        "MOBILE_INTEGRATION_ENABLED": "true",
        "MOBILE_PUBLIC_BASE_URL": "https://crcon.example.org",
        "SERVER_NUMBER": "1",
    },
)
class MobilePairingTests(TestCase):
    def setUp(self):
        registered_mods = patch("api.auth.set_registered_mods")
        registered_mods.start()
        self.addCleanup(registered_mods.stop)
        audit = patch("api.mobile.record_mobile_audit")
        audit.start()
        self.addCleanup(audit.stop)
        self.user = User.objects.create_superuser(
            username="mobile-admin",
            email="admin@example.org",
            password="correct horse battery staple",
        )
        self.client = Client()
        self.client.force_login(self.user)

    def _post(self, path, payload, client=None):
        return (client or self.client).post(
            path,
            data=json.dumps(payload),
            content_type="application/json",
        )

    def _pairing(self):
        created = self._post(
            "/api/mobile/v1/pairings",
            {"password": "correct horse battery staple"},
        )
        self.assertEqual(created.status_code, 200)
        result = created.json()["result"]
        query = parse_qs(urlparse(result["qr_payload"]).query)
        return result, query

    def _paired_tokens(self):
        pairing, query = self._pairing()
        path = f"/api/mobile/v1/pairings/{pairing['id']}"
        scanned = self._post(
            f"{path}/scan",
            {
                "secret": query["secret"][0],
                "device_name": "Phone",
                "platform": "android",
            },
        ).json()["result"]
        self._post(
            f"{path}/approve",
            {"verification_code": scanned["verification_code"]},
        )
        return self._post(
            f"{path}/exchange", {"exchange_token": scanned["exchange_token"]}
        ).json()["result"]

    def test_pairing_requires_correct_secret_and_web_approval(self):
        pairing, query = self._pairing()
        path = f"/api/mobile/v1/pairings/{pairing['id']}"
        wrong = self._post(
            f"{path}/scan",
            {"secret": "wrong", "device_name": "Phone", "platform": "android"},
        )
        self.assertEqual(wrong.status_code, 401)

        scanned = self._post(
            f"{path}/scan",
            {
                "secret": query["secret"][0],
                "device_name": "Phone",
                "platform": "android",
            },
        )
        scan_result = scanned.json()["result"]
        pending = self._post(
            f"{path}/exchange",
            {"exchange_token": scan_result["exchange_token"]},
        )
        self.assertEqual(pending.status_code, 202)

        approved = self._post(
            f"{path}/approve",
            {
                "approve": True,
                "verification_code": scan_result["verification_code"],
            },
        )
        self.assertEqual(approved.status_code, 200)
        exchanged = self._post(
            f"{path}/exchange",
            {"exchange_token": scan_result["exchange_token"]},
        )
        self.assertEqual(exchanged.status_code, 200)
        self.assertEqual(MobileDevice.objects.count(), 1)
        replay = self._post(
            f"{path}/exchange",
            {"exchange_token": scan_result["exchange_token"]},
        )
        self.assertEqual(replay.status_code, 401)

    def test_refresh_token_rotates_and_replay_fails(self):
        pairing, query = self._pairing()
        path = f"/api/mobile/v1/pairings/{pairing['id']}"
        scanned = self._post(
            f"{path}/scan",
            {
                "secret": query["secret"][0],
                "device_name": "iPhone",
                "platform": "ios",
            },
        ).json()["result"]
        self._post(
            f"{path}/approve",
            {"verification_code": scanned["verification_code"]},
        )
        tokens = self._post(
            f"{path}/exchange", {"exchange_token": scanned["exchange_token"]}
        ).json()["result"]
        payload = {
            "device_id": tokens["device_id"],
            "refresh_token": tokens["refresh_token"],
        }
        refreshed = self._post(
            "/api/mobile/v1/tokens/refresh", payload, client=Client()
        )
        self.assertEqual(refreshed.status_code, 200)
        replay = self._post("/api/mobile/v1/tokens/refresh", payload, client=Client())
        self.assertEqual(replay.status_code, 401)

    def test_pairing_expires_and_never_stores_raw_secret(self):
        pairing, query = self._pairing()
        record = MobilePairing.objects.get(pk=pairing["id"])
        self.assertNotEqual(record.secret_digest, query["secret"][0])
        record.expires_at = timezone.now() - timedelta(seconds=1)
        record.save(update_fields=("expires_at",))
        expired = self._post(
            f"/api/mobile/v1/pairings/{pairing['id']}/scan",
            {
                "secret": query["secret"][0],
                "device_name": "Late phone",
                "platform": "android",
            },
        )
        self.assertEqual(expired.status_code, 410)

    def test_wrong_comparison_code_is_rejected(self):
        pairing, query = self._pairing()
        path = f"/api/mobile/v1/pairings/{pairing['id']}"
        scanned = self._post(
            f"{path}/scan",
            {
                "secret": query["secret"][0],
                "device_name": "Phone",
                "platform": "android",
            },
        ).json()["result"]
        rejected = self._post(
            f"{path}/approve",
            {
                "approve": True,
                "verification_code": (
                    "000000" if scanned["verification_code"] != "000000" else "111111"
                ),
            },
        )
        self.assertEqual(rejected.status_code, 400)
        self.assertNotEqual(scanned["verification_code"], "")

    def test_device_revocation_invalidates_access_on_next_request(self):
        pairing, query = self._pairing()
        path = f"/api/mobile/v1/pairings/{pairing['id']}"
        scanned = self._post(
            f"{path}/scan",
            {
                "secret": query["secret"][0],
                "device_name": "Phone",
                "platform": "android",
            },
        ).json()["result"]
        self._post(
            f"{path}/approve",
            {"verification_code": scanned["verification_code"]},
        )
        tokens = self._post(
            f"{path}/exchange", {"exchange_token": scanned["exchange_token"]}
        ).json()["result"]
        device = MobileDevice.objects.get(pk=tokens["device_id"])
        self.assertNotEqual(device.refresh_token_digest, tokens["refresh_token"])
        self.assertFalse(
            MobileAccessToken.objects.filter(
                token_digest=tokens["access_token"]
            ).exists()
        )
        bearer = Client(HTTP_AUTHORIZATION=f"Bearer {tokens['access_token']}")
        self.assertEqual(bearer.get("/api/mobile/v1/devices").status_code, 200)
        revoked = self.client.delete(f"/api/mobile/v1/devices/{tokens['device_id']}")
        self.assertEqual(revoked.status_code, 200)
        self.assertEqual(bearer.get("/api/mobile/v1/devices").status_code, 401)

    def test_permission_loss_takes_effect_on_next_request(self):
        tokens = self._paired_tokens()
        bearer = Client(HTTP_AUTHORIZATION=f"Bearer {tokens['access_token']}")
        self.assertEqual(bearer.get("/api/mobile/v1/devices").status_code, 200)
        self.user.is_superuser = False
        self.user.save(update_fields=("is_superuser",))
        self.assertEqual(bearer.get("/api/mobile/v1/devices").status_code, 403)

    def test_disabled_user_is_rejected_on_next_request(self):
        tokens = self._paired_tokens()
        bearer = Client(HTTP_AUTHORIZATION=f"Bearer {tokens['access_token']}")
        self.user.is_active = False
        self.user.save(update_fields=("is_active",))
        self.assertEqual(bearer.get("/api/mobile/v1/devices").status_code, 401)

    def test_default_mobile_permissions_exclude_read_only(self):
        owner = Group.objects.get(name="owner")
        read_only = Group.objects.get(name="read_only")
        self.assertTrue(
            owner.permissions.filter(codename="can_manage_all_mobile_devices").exists()
        )
        self.assertFalse(
            read_only.permissions.filter(codename__contains="admin_incidents").exists()
        )
        self.assertFalse(
            read_only.permissions.filter(codename__contains="mobile_devices").exists()
        )


@patch.dict(
    "os.environ",
    {
        "MOBILE_INTEGRATION_ENABLED": "true",
        "MOBILE_PUBLIC_BASE_URL": "https://crcon.example.org",
        "SERVER_NUMBER": "1",
    },
)
class MobileContextTests(TestCase):
    def setUp(self):
        registered_mods = patch("api.auth.set_registered_mods")
        registered_mods.start()
        self.addCleanup(registered_mods.stop)
        self.user = User.objects.create_superuser(
            username="context-admin",
            email="context@example.org",
            password="secret",
        )
        self.client = Client()
        self.client.force_login(self.user)

    @patch("api.mobile_context._rcon_api")
    def test_player_search_combines_history_and_live_context(self, get_rcon_api):
        get_rcon_api.return_value.get_players_history.return_value = {
            "players": [{"player_id": "bob", "player_name": "Bob"}]
        }
        get_rcon_api.return_value.get_detailed_players.return_value = {
            "players": {
                "bob": {
                    "player_id": "bob",
                    "name": "Bob",
                    "team": "Allies",
                    "unit_name": "Item",
                }
            }
        }
        response = self.client.get(
            "/api/mobile/v1/players/search", {"q": "Bob", "server_number": 1}
        )
        self.assertEqual(response.status_code, 200)
        player = response.json()["result"][0]
        self.assertTrue(player["online"])
        self.assertEqual(player["unit_name"], "Item")

    @patch("api.mobile_context._rcon_api")
    def test_squad_endpoint_returns_only_requested_squad(self, get_rcon_api):
        get_rcon_api.return_value.get_team_view.return_value = {
            "Allies": {
                "squads": {
                    "Item": {
                        "type": "infantry",
                        "has_leader": True,
                        "players": [{"player_id": "leader", "name": "Leader"}],
                    }
                }
            },
            "fail_count": 0,
        }
        response = self.client.get("/api/mobile/v1/servers/1/squads/Allies/Item")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["result"]["squad_name"], "Item")
        self.assertEqual(len(response.json()["result"]["players"]), 1)

    @patch.dict("os.environ", {"MOBILE_CONTEXT_V2": "enabled"})
    @patch("api.mobile_incidents.record_mobile_audit")
    @patch("api.mobile_incidents.create_incident")
    @patch("api.mobile_incidents._rcon_api")
    def test_manual_incident_resolves_dynamic_squad_and_player(
        self, get_rcon_api, create_incident, _audit
    ):
        get_rcon_api.return_value.get_detailed_players.return_value = {
            "players": {
                "biene-id": {
                    "player_id": "biene-id",
                    "name": "Biene",
                    "team": "Allies",
                    "unit_name": "George",
                }
            }
        }
        get_rcon_api.return_value.get_team_view.return_value = {
            "Allies": {
                "squads": {
                    "George": {
                        "type": "infantry",
                        "has_leader": False,
                        "players": [
                            {
                                "player_id": "biene-id",
                                "name": "Biene",
                                "team": "Allies",
                                "unit_name": "George",
                            }
                        ],
                    }
                }
            },
            "Axis": {"squads": {}},
            "fail_count": 0,
        }
        create_incident.return_value = (
            {"id": "incident-id", "server_number": 1, "revision": 1},
            True,
        )

        response = self.client.post(
            "/api/mobile/v1/incidents",
            data=json.dumps({"server_number": 1, "reason": "George meldet Biene"}),
            content_type="application/json",
            HTTP_IDEMPOTENCY_KEY="manual-context-1",
        )

        self.assertEqual(response.status_code, 200)
        arguments = create_incident.call_args.kwargs
        subjects = arguments["subjects"]
        self.assertEqual(
            {(subject["kind"], subject["display_name"]) for subject in subjects},
            {("squad", "George"), ("player", "Biene")},
        )
        self.assertTrue(all(subject["state"] == "confirmed" for subject in subjects))
        self.assertEqual(arguments["raw_message"], "George meldet Biene")

    @patch("api.mobile_incidents.record_mobile_audit")
    @patch("api.mobile_incidents.mutate_incident_subject")
    def test_subject_confirmation_uses_revision_and_idempotency(
        self, mutate_subject, _audit
    ):
        incident_id = "f0c4a788-2d44-4621-9fa1-8447dd7caf65"
        subject_id = "8a1bcbe1-315a-4411-8238-cb9ed6f0874e"
        mutate_subject.return_value = {
            "id": incident_id,
            "server_number": 1,
            "revision": 4,
            "subjects": [],
        }
        response = self.client.patch(
            f"/api/mobile/v1/incidents/{incident_id}/subjects/{subject_id}",
            data=json.dumps({"revision": 3, "operation": "confirm"}),
            content_type="application/json",
            HTTP_IDEMPOTENCY_KEY="subject-confirm-1",
        )
        self.assertEqual(response.status_code, 200)
        mutate_subject.assert_called_once_with(
            incident_id,
            actor="context-admin",
            expected_revision=3,
            operation="confirm",
            payload={"revision": 3, "operation": "confirm"},
            subject_id=subject_id,
            idempotency_key="subject-confirm-1",
        )
