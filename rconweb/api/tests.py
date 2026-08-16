import json
import sys
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from urllib.parse import parse_qs, urlparse

from django.contrib.auth.models import Group, User
from django.test import Client, TestCase, override_settings
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

    def test_web_app_can_scan_qr_pairing(self):
        pairing, query = self._pairing()
        scanned = self._post(
            f"/api/mobile/v1/pairings/{pairing['id']}/scan",
            {
                "secret": query["secret"][0],
                "device_name": "Frontline Web",
                "platform": "web",
            },
        )

        self.assertEqual(scanned.status_code, 200)
        self.assertEqual(MobilePairing.objects.get(pk=pairing["id"]).platform, "web")

    @override_settings(CORS_ALLOWED_ORIGINS=["https://webapp.fln.gg"])
    def test_web_app_cors_preflight_allows_json_pairing_request(self):
        response = Client().options(
            "/api/mobile/v1/pairings/00000000-0000-0000-0000-000000000000/scan",
            HTTP_ORIGIN="https://webapp.fln.gg",
            HTTP_ACCESS_CONTROL_REQUEST_METHOD="POST",
            HTTP_ACCESS_CONTROL_REQUEST_HEADERS="content-type",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response["Access-Control-Allow-Origin"], "https://webapp.fln.gg"
        )
        self.assertIn("POST", response["Access-Control-Allow-Methods"])
        self.assertIn("content-type", response["Access-Control-Allow-Headers"].lower())

    def test_desktop_authorization_requires_browser_approval_and_is_single_use(self):
        desktop = Client()
        created = self._post(
            "/api/mobile/v1/desktop-authorizations",
            {"device_name": "Frontline Control Room", "app_version": "0.1.8"},
            client=desktop,
        )
        self.assertEqual(created.status_code, 200)
        result = created.json()["result"]
        self.assertIn("/apps?desktop_code=", result["verification_uri"])
        self.assertTrue(result["user_code"].startswith("FLN-"))

        record = MobilePairing.objects.get(pk=result["id"])
        self.assertIsNone(record.user)
        self.assertNotEqual(record.secret_digest, result["device_code"])
        self.assertNotEqual(record.user_code_digest, result["user_code"])

        exchange_path = f"/api/mobile/v1/desktop-authorizations/{result['id']}/exchange"
        pending = self._post(
            exchange_path, {"device_code": result["device_code"]}, client=desktop
        )
        self.assertEqual(pending.status_code, 202)

        approved = self._post(
            "/api/mobile/v1/desktop-authorizations/approve",
            {
                "user_code": result["user_code"],
                "password": "correct horse battery staple",
                "approve": True,
            },
        )
        self.assertEqual(approved.status_code, 200)

        exchanged = self._post(
            exchange_path, {"device_code": result["device_code"]}, client=desktop
        )
        self.assertEqual(exchanged.status_code, 200)
        self.assertEqual(exchanged.json()["result"]["username"], self.user.username)
        self.assertEqual(MobileDevice.objects.get().platform, "windows")

        replay = self._post(
            exchange_path, {"device_code": result["device_code"]}, client=desktop
        )
        self.assertEqual(replay.status_code, 401)

    def test_desktop_authorization_rejects_invalid_device_code(self):
        created = self._post(
            "/api/mobile/v1/desktop-authorizations",
            {"device_name": "Frontline Control Room"},
            client=Client(),
        ).json()["result"]
        response = self._post(
            f"/api/mobile/v1/desktop-authorizations/{created['id']}/exchange",
            {"device_code": "wrong"},
            client=Client(),
        )
        self.assertEqual(response.status_code, 401)

    def test_bootstrap_lists_only_active_admins_eligible_for_incident_handover(self):
        User.objects.create_user(
            username="mobile-observer",
            email="observer@example.org",
            password="secret",
        )

        response = self.client.get("/api/mobile/v1/bootstrap")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["result"]["user"]["assignable_admins"],
            ["mobile-admin"],
        )
        self.assertEqual(response.json()["result"]["incident_cursor"], 0)

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

    def test_devices_endpoint_never_exposes_or_mutates_another_users_device(self):
        tokens = self._paired_tokens()
        other_user = User.objects.create_user(
            username="another-admin", password="another correct password"
        )
        other_device = MobileDevice.objects.create(
            user=other_user,
            name="Another admin's phone",
            platform="android",
        )

        # The authenticated user is a superuser in this test.  Even that must
        # not widen the account-bound mobile device endpoint.
        bearer = Client(HTTP_AUTHORIZATION=f"Bearer {tokens['access_token']}")
        listed = bearer.get("/api/mobile/v1/devices?all=true")
        self.assertEqual(listed.status_code, 200)
        device_ids = {item["id"] for item in listed.json()["result"]}
        self.assertEqual(device_ids, {tokens["device_id"]})

        forbidden = bearer.delete(f"/api/mobile/v1/devices/{other_device.id}")
        self.assertEqual(forbidden.status_code, 404)
        other_device.refresh_from_db()
        self.assertIsNone(other_device.revoked_at)

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

    @patch("api.mobile_context.AutobalancerStore")
    def test_autobalancer_mobile_status_is_read_only_and_minimal(self, store):
        store.return_value.load_status.return_value = {
            "mode": "automatic",
            "phase": "armed",
            "team_counts": {"allies": 46, "axis": 42},
            "team_difference": 4,
            "required_switches": 1,
            "proposal": {"player_id": "must-not-leak"},
            "plan": {"steps": ["must-not-leak"]},
            "block_reasons": [],
            "warnings": ["low confidence"],
        }

        response = self.client.get("/api/mobile/v1/autobalancer", {"server_number": 1})

        self.assertEqual(response.status_code, 200)
        result = response.json()["result"]
        self.assertEqual(result["team_counts"], {"allies": 46, "axis": 42})
        self.assertEqual(result["required_switches"], 1)
        self.assertNotIn("proposal", result)
        self.assertNotIn("plan", result)

    @patch("api.mobile_context.get_message_templates")
    def test_action_templates_expose_only_message_and_reason_templates(
        self, get_templates
    ):
        get_templates.side_effect = lambda category: [
            {
                "id": 1,
                "title": f"{category.value} template",
                "content": "Prepared text",
                "category": category.value,
            }
        ]

        response = self.client.get("/api/mobile/v1/templates")

        self.assertEqual(response.status_code, 200)
        result = response.json()["result"]
        self.assertEqual(result["message"][0]["content"], "Prepared text")
        self.assertEqual(result["reason"][0]["content"], "Prepared text")
        self.assertEqual(
            [call.args[0].value for call in get_templates.call_args_list],
            ["MESSAGE", "REASON"],
        )

    def test_action_templates_require_existing_template_permission(self):
        limited = User.objects.create_user("limited-template-viewer", password="secret")
        self.client.force_login(limited)

        response = self.client.get("/api/mobile/v1/templates")

        self.assertEqual(response.status_code, 403)

    @patch.dict("os.environ", {"MOBILE_PLAYER_OPERATIONS": "true"})
    @patch("api.mobile_context._rcon_api")
    def test_watchlist_reuses_native_watch_entries(self, get_rcon_api):
        get_rcon_api.return_value.get_players_history.return_value = {
            "total": 1,
            "players": [
                {
                    "player_id": "p1",
                    "names": [{"name": "Watched Player"}],
                    "watchlist": {
                        "reason": "Suspicious behaviour",
                        "by": "admin",
                        "count": 2,
                    },
                }
            ],
        }

        response = self.client.get("/api/mobile/v1/watchlist", {"server_number": 1})

        self.assertEqual(response.status_code, 200)
        result = response.json()["result"]
        self.assertEqual(result["players"][0]["name"], "Watched Player")
        self.assertEqual(result["players"][0]["count"], 2)
        get_rcon_api.return_value.get_players_history.assert_called_once_with(
            page=1, page_size=100, is_watched=True
        )

    @patch.dict("os.environ", {"MOBILE_PLAYER_OPERATIONS": "true"})
    @patch("api.mobile_context.record_mobile_audit")
    @patch("api.mobile_context._rcon_api")
    def test_watch_requires_reason_and_records_native_operation(
        self, get_rcon_api, audit
    ):
        missing = self.client.put(
            "/api/mobile/v1/players/p1/watch",
            data=json.dumps({"server_number": 1}),
            content_type="application/json",
        )
        self.assertEqual(missing.status_code, 400)
        response = self.client.put(
            "/api/mobile/v1/players/p1/watch",
            data=json.dumps(
                {
                    "server_number": 1,
                    "reason": "Check teamkills",
                    "player_name": "Player One",
                    "incident_id": "11111111-1111-1111-1111-111111111111",
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        get_rcon_api.return_value.watch_player.assert_called_once_with(
            player_id="p1",
            reason="Check teamkills",
            by="context-admin",
            player_name="Player One",
        )
        audit.assert_called_once()

    @patch.dict("os.environ", {"MOBILE_PLAYER_OPERATIONS": "true"})
    @patch("rcon.admin_incidents.get_incident")
    @patch("api.mobile_context._rcon_api")
    def test_incident_context_is_bounded_and_filters_raw_log_types(
        self, get_rcon_api, get_incident
    ):
        get_incident.return_value = {
            "server_number": 1,
            "created_at": "2026-08-06T12:00:00+00:00",
            "reporter_id": "reporter",
            "subjects": [{"kind": "player", "state": "confirmed", "player_id": "p1"}],
        }
        get_rcon_api.return_value.get_historical_logs.return_value = [
            {
                "id": 1,
                "type": "CHAT[Allies]",
                "event_time": "2026-08-06T11:58:00+00:00",
                "player1_name": "Player One",
                "content": "hello",
            },
            {
                "id": 2,
                "type": "TEAM KILL",
                "event_time": "2026-08-06T12:01:00+00:00",
                "player1_name": "Player One",
                "player2_name": "Friendly",
                "content": "team kill",
            },
            {"id": 3, "type": "ADMIN", "content": "must not appear"},
        ]

        response = self.client.get(
            "/api/mobile/v1/incidents/11111111-1111-1111-1111-111111111111/player-context",
            {"player_id": "p1", "limit": 5},
        )

        self.assertEqual(response.status_code, 200)
        events = response.json()["result"]["events"]
        self.assertEqual([event["type"] for event in events], ["chat", "teamkill"])
        self.assertEqual(events[0]["message"], "hello")
        call = get_rcon_api.return_value.get_historical_logs.call_args.kwargs
        self.assertEqual(call["player_id"], "p1")
        self.assertEqual(call["server_filter"], "1")

    @patch.dict("os.environ", {"MOBILE_LIVE_STATUS": "true"})
    @patch("api.mobile_context._rcon_api")
    def test_live_status_only_returns_read_only_fields(self, get_rcon_api):
        api = get_rcon_api.return_value
        api.get_status.return_value = {
            "name": "Server 1",
            "current_players": 42,
            "max_players": 100,
        }
        api.get_gamestate.return_value = {
            "current_map": {"pretty_name": "Foy"},
            "time_remaining": timedelta(minutes=42),
            "num_allied_players": 21,
            "num_axis_players": 21,
            "allied_score": 2,
            "axis_score": 3,
        }
        api.get_next_map.return_value = {"pretty_name": "Carentan"}
        api.get_queue_length.return_value = 4
        api.get_ingame_mods.return_value = ["a"]
        api.get_online_mods.return_value = ["a", "b"]

        response = self.client.get("/api/mobile/v1/servers/1/live-status")

        self.assertEqual(response.status_code, 200)
        result = response.json()["result"]
        self.assertEqual(result["match"]["team_counts"], {"allies": 21, "axis": 21})
        self.assertEqual(result["ingame_admin_count"], 1)
        self.assertNotIn("set_map", result)

    @patch("api.mobile_context._rcon_api")
    def test_player_detail_keeps_steam_and_eos_identifiers_separate(self, get_rcon_api):
        get_rcon_api.return_value.get_player_profile.return_value = {
            "player_id": "76561198036685843",
            "soldier": {"eos_id": "eos-7db4c0a9"},
        }
        get_rcon_api.return_value.get_detailed_player_info.return_value = None

        response = self.client.get(
            "/api/mobile/v1/players/76561198036685843",
            {"server_number": 1},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["result"]["identifiers"],
            {
                "steam_id": "76561198036685843",
                "eos_id": "eos-7db4c0a9",
                "platform_player_id": None,
            },
        )

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

    @patch("api.mobile_incidents.confirmed_action_subject")
    def test_permanent_ban_requires_confirmation_and_uses_existing_permission_path(
        self, confirmed_subject
    ):
        from api.mobile_incidents import _execute_action

        confirmed_subject.return_value = {
            "display_name": "Biene",
            "player_id": "biene-id",
        }
        incident = {"target_id": "biene-id", "target_name": "Biene"}
        perma_ban = MagicMock()
        fake_views = SimpleNamespace(rcon_api=SimpleNamespace(perma_ban=perma_ban))

        with patch.dict(sys.modules, {"api.views": fake_views}):
            with self.assertRaisesRegex(ValueError, "explicit confirmation"):
                _execute_action(
                    "perma_ban",
                    {"player_id": "biene-id", "reason": "Repeated abuse"},
                    "context-admin",
                    incident,
                )

            _execute_action(
                "perma_ban",
                {
                    "player_id": "biene-id",
                    "reason": "Repeated abuse",
                    "confirmed": True,
                },
                "context-admin",
                incident,
            )

        perma_ban.assert_called_once_with(
            "biene-id",
            reason="Repeated abuse",
            by="context-admin",
            player_name="Biene",
        )

    @patch("api.mobile_incidents.confirmed_action_subject")
    def test_rejected_rcon_action_is_not_treated_as_success(self, confirmed_subject):
        from api.mobile_incidents import _execute_action

        confirmed_subject.return_value = {
            "display_name": "Biene",
            "player_id": "biene-id",
        }
        kick = MagicMock(return_value=False)
        fake_views = SimpleNamespace(rcon_api=SimpleNamespace(kick=kick))

        with patch.dict(sys.modules, {"api.views": fake_views}):
            with self.assertRaisesRegex(ValueError, "game server rejected"):
                _execute_action(
                    "kick",
                    {
                        "player_id": "biene-id",
                        "reason": "Ping limit exceeded",
                        "confirmed": True,
                    },
                    "context-admin",
                    {"target_id": "biene-id", "target_name": "Biene"},
                )

    @patch("api.mobile_incidents.confirmed_action_subject")
    def test_rejected_blacklist_is_not_treated_as_success(self, confirmed_subject):
        from api.mobile_incidents import _execute_action

        confirmed_subject.return_value = {
            "display_name": "Biene",
            "player_id": "biene-id",
        }
        add_blacklist_record = MagicMock(return_value=False)
        fake_views = SimpleNamespace(
            rcon_api=SimpleNamespace(add_blacklist_record=add_blacklist_record)
        )

        with patch.dict(sys.modules, {"api.views": fake_views}):
            with self.assertRaisesRegex(ValueError, "game server rejected"):
                _execute_action(
                    "blacklist",
                    {
                        "player_id": "biene-id",
                        "blacklist_id": 4,
                        "reason": "Reason",
                        "confirmed": True,
                    },
                    "context-admin",
                    {"target_id": "biene-id", "target_name": "Biene"},
                )

    def test_rejected_squad_disband_is_not_treated_as_success(self):
        from api.mobile_incidents import _execute_action

        disband = MagicMock(return_value=False)
        fake_views = SimpleNamespace(
            rcon_api=SimpleNamespace(disband_squad_by_name=disband)
        )
        incident = {
            "subjects": [
                {
                    "id": "squad-subject",
                    "kind": "squad",
                    "state": "confirmed",
                    "team": "allies",
                    "squad_name": "able",
                }
            ]
        }

        with patch.dict(sys.modules, {"api.views": fake_views}):
            with self.assertRaisesRegex(ValueError, "game server rejected"):
                _execute_action(
                    "disband_squad",
                    {
                        "subject_id": "squad-subject",
                        "reason": "Reason",
                        "confirmed": True,
                    },
                    "context-admin",
                    incident,
                )

    @patch("api.mobile_incidents.confirmed_action_subject")
    def test_all_discord_game_actions_reach_the_expected_crcon_method(
        self, confirmed_subject
    ):
        from api.mobile_incidents import _execute_action

        confirmed_subject.return_value = {
            "id": "player-subject",
            "kind": "player",
            "state": "confirmed",
            "display_name": "Biene",
            "player_id": "player-id",
            "team": "allies",
            "squad_name": "able",
        }
        api = SimpleNamespace(
            message_player=MagicMock(return_value=True),
            punish=MagicMock(return_value=True),
            kick=MagicMock(return_value=True),
            temp_ban=MagicMock(return_value=True),
            perma_ban=MagicMock(return_value=True),
            add_blacklist_record=MagicMock(return_value={"id": 9}),
            remove_player_from_squad=MagicMock(return_value=True),
            disband_squad_by_name=MagicMock(return_value={"squad_name": "able"}),
        )
        incident = {
            "target_id": "player-id",
            "target_name": "Biene",
            "subjects": [
                {
                    "id": "player-subject",
                    "kind": "player",
                    "state": "confirmed",
                    "player_id": "player-id",
                    "display_name": "Biene",
                    "team": "allies",
                    "squad_name": "able",
                }
            ],
        }

        with patch.dict(sys.modules, {"api.views": SimpleNamespace(rcon_api=api)}):
            self.assertTrue(
                _execute_action(
                    "message",
                    {"player_id": "player-id", "message": "Hello"},
                    "Moderator",
                    incident,
                )
            )
            self.assertTrue(
                _execute_action(
                    "punish",
                    {"player_id": "player-id", "reason": "Reason"},
                    "Moderator",
                    incident,
                )
            )
            for action in ("kick", "perma_ban"):
                self.assertTrue(
                    _execute_action(
                        action,
                        {
                            "player_id": "player-id",
                            "reason": "Reason",
                            "confirmed": True,
                        },
                        "Moderator",
                        incident,
                    )
                )
            self.assertTrue(
                _execute_action(
                    "temp_ban",
                    {
                        "player_id": "player-id",
                        "reason": "Reason",
                        "duration_hours": 6,
                        "confirmed": True,
                    },
                    "Moderator",
                    incident,
                )
            )
            self.assertEqual(
                _execute_action(
                    "blacklist",
                    {
                        "player_id": "player-id",
                        "reason": "Reason",
                        "blacklist_id": 4,
                        "confirmed": True,
                    },
                    "Moderator",
                    incident,
                ),
                {"id": 9},
            )
            self.assertTrue(
                _execute_action(
                    "remove_from_squad",
                    {
                        "player_id": "player-id",
                        "reason": "Reason",
                        "confirmed": True,
                    },
                    "Moderator",
                    incident,
                )
            )
            self.assertEqual(
                _execute_action(
                    "disband_squad",
                    {
                        "subject_id": "player-subject",
                        "reason": "Reason",
                        "confirmed": True,
                    },
                    "Moderator",
                    incident,
                ),
                {"squad_name": "able"},
            )

        api.message_player.assert_called_once()
        api.punish.assert_called_once()
        api.kick.assert_called_once()
        api.temp_ban.assert_called_once()
        api.perma_ban.assert_called_once()
        api.add_blacklist_record.assert_called_once()
        api.remove_player_from_squad.assert_called_once_with("player-id", "Reason")
        api.disband_squad_by_name.assert_called_once_with("allies", "able", "Reason")


class DiscordActionTemplateTests(TestCase):
    def _discord_manager(self):
        user = User.objects.create_superuser(
            username="discord-manager",
            email="manager@example.org",
            password="secret",
        )
        self.client.force_login(user)
        return user

    def test_ai_provider_config_encrypts_api_key_and_never_serializes_it(self):
        from api.discord_capabilities import decrypt_capability
        from api.models import DiscordReportIntegration

        self._discord_manager()
        response = self.client.put(
            "/api/discord/v1/integration",
            data=json.dumps(
                {
                    "enabled": True,
                    "moderator_role_ids": [],
                    "allowed_actions": [],
                    "language": "de",
                    "ai_config": {
                        "provider": "api_key",
                        "ai_model": "gpt-5.6-luna",
                        "player_name_model": "gpt-5.4-nano",
                    },
                    "api_key": "sk-test-key-that-is-long-enough",
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        result = response.json()["result"]
        self.assertTrue(result["has_api_key"])
        self.assertNotIn("api_key", result)
        integration = DiscordReportIntegration.objects.get(pk=1)
        self.assertNotIn(b"sk-test", bytes(integration.ai_api_key_ciphertext))
        self.assertEqual(
            decrypt_capability(integration.ai_api_key_ciphertext),
            "sk-test-key-that-is-long-enough",
        )

    def test_ai_provider_rejects_invalid_model_identifier(self):
        from api.discord_integration import _config_payload

        with self.assertRaisesRegex(ValueError, "Invalid AI model"):
            _config_payload(
                {
                    "ai_config": {
                        "provider": "api_key",
                        "ai_model": "../../secret",
                    }
                }
            )

    def test_legacy_managed_provider_is_disabled_until_customer_configures_ai(self):
        from api.discord_integration import _config_payload, _normalized_ai_config

        normalized = _normalized_ai_config(
            {
                "provider": "managed",
                "chat_enabled": True,
                "names_enabled": True,
            }
        )
        self.assertEqual(normalized["provider"], "api_key")
        self.assertFalse(normalized["chat_enabled"])
        self.assertFalse(normalized["names_enabled"])
        with self.assertRaisesRegex(ValueError, "Unknown AI provider"):
            _config_payload({"ai_config": {"provider": "managed"}})

    def test_action_subject_confirmation_is_derived_from_crcon_state(self):
        from api.discord_integration import (
            _normalize_action_subject,
            _validate_prepared_action_target,
        )

        confirmed_squad = {
            "target_id": "leader-id",
            "subjects": [
                {
                    "id": "squad-subject",
                    "kind": "squad",
                    "state": "confirmed",
                    "snapshot": {
                        "leader": {
                            "player_id": "leader-id",
                            "name": "Able Lead",
                            "role": "officer",
                        }
                    },
                }
            ],
        }
        normalized = _normalize_action_subject(
            confirmed_squad,
            {
                "subject_id": "squad-subject",
                "confirm_subject_id": "squad-subject",
            },
        )
        self.assertNotIn("confirm_subject_id", normalized)
        self.assertEqual(normalized["player_id"], "leader-id")

        vietnam_squad = {
            "target_id": None,
            "subjects": [
                {
                    "id": "vietnam-squad",
                    "kind": "squad",
                    "state": "confirmed",
                    "snapshot": {
                        "leader": {},
                        "players": [
                            {
                                "player_id": "eos-leader",
                                "name": "Biene",
                                "role": "squadleader",
                            }
                        ],
                    },
                }
            ],
        }
        normalized = _normalize_action_subject(
            vietnam_squad, {"subject_id": "vietnam-squad"}
        )
        self.assertEqual(normalized["player_id"], "eos-leader")
        self.assertEqual(normalized["player_name"], "Biene")
        _validate_prepared_action_target("kick", vietnam_squad, normalized)

        suggested_player = {
            "target_id": "player-id",
            "subjects": [
                {
                    "id": "player-subject",
                    "kind": "player",
                    "state": "suggested",
                    "player_id": "player-id",
                }
            ],
        }
        normalized = _normalize_action_subject(
            suggested_player, {"subject_id": "player-subject"}
        )
        self.assertEqual(normalized["confirm_subject_id"], "player-subject")
        self.assertEqual(normalized["player_id"], "player-id")
        _validate_prepared_action_target("kick", suggested_player, normalized)

        with self.assertRaisesRegex(ValueError, "confirmed player"):
            _validate_prepared_action_target("message", {"subjects": []}, {})

    def test_selected_squad_takes_priority_over_incident_primary_target(self):
        from api.discord_integration import _normalize_action_subject

        incident = {
            "target_id": "able-leader",
            "target_name": "Able Lead",
            "subjects": [
                {
                    "id": "able-subject",
                    "kind": "squad",
                    "state": "confirmed",
                    "snapshot": {
                        "leader": {
                            "player_id": "able-leader",
                            "name": "Able Lead",
                            "role": "officer",
                        }
                    },
                },
                {
                    "id": "charlie-subject",
                    "kind": "squad",
                    "state": "confirmed",
                    "snapshot": {
                        "leader": {
                            "player_id": "charlie-leader",
                            "name": "Charlie Lead",
                            "role": "officer",
                        }
                    },
                },
            ],
        }

        normalized = _normalize_action_subject(
            incident,
            {
                "subject_id": "charlie-subject",
                "player_id": "forged-player",
            },
        )

        self.assertEqual(normalized["player_id"], "charlie-leader")
        self.assertEqual(normalized["player_name"], "Charlie Lead")

    def test_multiple_confirmed_subjects_keep_incident_open_after_one_action(self):
        from api.discord_integration import _should_auto_resolve_after_action

        self.assertFalse(
            _should_auto_resolve_after_action(
                {
                    "subjects": [
                        {"kind": "squad", "state": "confirmed"},
                        {"kind": "squad", "state": "confirmed"},
                    ]
                }
            )
        )
        self.assertTrue(
            _should_auto_resolve_after_action(
                {"subjects": [{"kind": "player", "state": "confirmed"}]}
            )
        )

    @patch("api.discord_integration.get_incident")
    @patch("api.discord_integration._validate_binding")
    @patch("api.discord_integration._authorized_integration")
    def test_subject_selection_is_role_and_revision_validated_without_mutation(
        self, authorized, validate_binding, get_incident
    ):
        authorized.return_value = (SimpleNamespace(), None)
        get_incident.return_value = {
            "id": "22222222-2222-2222-2222-222222222222",
            "revision": 4,
            "subjects": [
                {
                    "id": "33333333-3333-3333-3333-333333333333",
                    "kind": "squad",
                    "state": "confirmed",
                    "display_name": "Charlie",
                    "squad_name": "Charlie",
                }
            ],
        }
        response = self.client.post(
            "/api/discord/v1/incidents/select-subject",
            data=json.dumps(
                {
                    "interaction_id": "1538274085513994998",
                    "installation_id": "11111111-1111-1111-1111-111111111111",
                    "guild_id": "123",
                    "channel_id": "456",
                    "incident_id": "22222222-2222-2222-2222-222222222222",
                    "incident_revision": 4,
                    "actor": {
                        "discord_id": "789",
                        "display_name": "Moderator",
                        "role_ids": ["42"],
                    },
                    "operation": "select_subject",
                    "payload": {"subject_id": "33333333-3333-3333-3333-333333333333"},
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["result"]["display_name"], "Charlie")
        validate_binding.assert_called_once()
        get_incident.assert_called_once_with("22222222-2222-2222-2222-222222222222")

    @patch("api.discord_integration.mutate_incident")
    @patch("api.discord_integration._validate_binding")
    @patch("api.discord_integration._authorized_integration")
    def test_transition_persists_datetime_result_as_idempotency_receipt(
        self, authorized, validate_binding, mutate_incident
    ):
        from api.models import DiscordInteractionReceipt

        authorized.return_value = (SimpleNamespace(reporter_templates={}), None)
        mutate_incident.return_value = {
            "id": "22222222-2222-2222-2222-222222222222",
            "status": "resolved",
            "revision": 2,
            "updated_at": timezone.now(),
            "reporter_id": None,
        }
        response = self.client.post(
            "/api/discord/v1/incidents/transition",
            data=json.dumps(
                {
                    "interaction_id": "1538274085513994999",
                    "installation_id": "11111111-1111-1111-1111-111111111111",
                    "guild_id": "123",
                    "channel_id": "456",
                    "incident_id": "22222222-2222-2222-2222-222222222222",
                    "incident_revision": 1,
                    "actor": {
                        "discord_id": "789",
                        "display_name": "Moderator",
                        "role_ids": ["42"],
                    },
                    "operation": "resolve",
                    "payload": {},
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        receipt = DiscordInteractionReceipt.objects.get(
            interaction_id="1538274085513994999"
        )
        self.assertIsInstance(receipt.result["updated_at"], str)
        self.assertEqual(receipt.result["status"], "resolved")
        validate_binding.assert_called_once()

    @patch("api.discord_integration._validate_binding")
    @patch("api.discord_integration._authorized_integration")
    @patch("api.discord_integration.get_message_templates")
    def test_templates_come_from_shared_crcon_categories(
        self, get_templates, authorized, validate_binding
    ):
        authorized.return_value = (SimpleNamespace(), None)
        get_templates.return_value = [
            {
                "id": 7,
                "title": "Beleidigung",
                "content": "Gespeicherter Grund",
            }
        ]
        response = self.client.post(
            "/api/discord/v1/action-templates",
            data=json.dumps(
                {
                    "guild_id": "123",
                    "channel_id": "456",
                    "actor": {
                        "discord_id": "789",
                        "display_name": "Moderator",
                        "role_ids": ["42"],
                    },
                    "action": "kick",
                    "template_id": 7,
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        result = response.json()["result"]
        self.assertEqual(result["category"], "REASON")
        self.assertEqual(result["templates"], [{"id": 7, "title": "Beleidigung"}])
        self.assertEqual(result["selected"]["content"], "Gespeicherter Grund")
        self.assertNotIn("content", result["templates"][0])
        validate_binding.assert_called_once()

    @patch("api.discord_integration.decrypt_capability", return_value="events-test")
    @patch("api.discord_integration.requests.get")
    @patch("api.discord_integration._integration")
    def test_discord_options_are_proxied_for_authenticated_manager(
        self, integration, get, _decrypt
    ):
        self._discord_manager()
        integration.return_value = SimpleNamespace(
            enabled=True,
            outbound_capability_ciphertext=b"ciphertext",
            service_url="https://discord.example",
            installation_id="11111111-1111-1111-1111-111111111111",
        )
        get.return_value.raise_for_status.return_value = None
        get.return_value.json.return_value = {
            "guild": {"id": "123", "name": "Frontline"},
            "channels": [{"id": "456", "name": "admin-ping"}],
            "roles": [{"id": "789", "name": "HLL-Moderator"}],
        }
        response = self.client.get("/api/discord/v1/options")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["result"]["roles"][0]["name"], "HLL-Moderator")
        get.assert_called_once_with(
            "https://discord.example/v1/options/11111111-1111-1111-1111-111111111111",
            headers={"Authorization": "Bearer events-test"},
            timeout=10,
        )

    @patch("api.discord_integration.requests.post")
    @patch("api.discord_integration._integration")
    def test_disconnected_options_use_authenticated_pairing_discovery(
        self, integration, post
    ):
        self._discord_manager()
        integration.return_value = SimpleNamespace(
            enabled=False,
            outbound_capability_ciphertext=b"",
            service_url="https://discord.example",
        )
        post.return_value.ok = True
        post.return_value.status_code = 200
        post.return_value.raise_for_status.return_value = None
        post.return_value.json.return_value = {
            "guild": {"id": "123", "name": "Frontline"},
            "channels": [{"id": "456", "name": "admin-ping"}],
            "roles": [{"id": "789", "name": "HLL-Moderator"}],
        }

        response = self.client.get("/api/discord/v1/options")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["result"]["guild"]["name"], "Frontline")
        request_payload = post.call_args.kwargs["json"]
        self.assertNotIn("guild_id", request_payload)
        self.assertEqual(
            request_payload["crcon_callback_url"],
            "https://crcon.example.org/api/discord/v1/pairings/complete",
        )

    @patch("api.discord_integration.requests.post")
    @patch("api.discord_integration._integration")
    def test_connect_does_not_accept_guild_and_surfaces_service_detail(
        self, integration, post
    ):
        self._discord_manager()
        integration.return_value = SimpleNamespace(
            service_url="https://discord.example"
        )
        post.return_value.ok = False
        post.return_value.status_code = 400
        post.return_value.json.return_value = {
            "detail": "The selected channel is not available on the installed Discord server"
        }

        response = self.client.post(
            "/api/discord/v1/connect",
            data=json.dumps({"guild_id": "999", "channel_id": "456"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("selected channel", str(response.json()))
        self.assertNotIn("guild_id", post.call_args.kwargs["json"])

    def test_pairing_verification_is_one_time_secret_protected(self):
        from api.discord_capabilities import capability_digest
        from api.models import DiscordPairing

        secret = "pair-secret-that-is-at-least-32-characters"
        pairing = DiscordPairing.objects.create(
            secret_digest=capability_digest(secret),
            expires_at=timezone.now() + timedelta(minutes=10),
        )
        valid = self.client.post(
            "/api/discord/v1/pairings/verify",
            data=json.dumps({"pairing_id": str(pairing.id), "pairing_secret": secret}),
            content_type="application/json",
        )
        invalid = self.client.post(
            "/api/discord/v1/pairings/verify",
            data=json.dumps({"pairing_id": str(pairing.id), "pairing_secret": "wrong"}),
            content_type="application/json",
        )
        self.assertEqual(valid.status_code, 200)
        self.assertEqual(invalid.status_code, 404)


class DiscordOutboxWorkerModeTests(TestCase):
    def test_event_worker_never_processes_moderation_jobs(self):
        from api.management.commands.discord_report_worker import Command

        command = Command()
        with patch.object(
            command, "_deliver_batch", side_effect=KeyboardInterrupt
        ) as deliver:
            with self.assertRaises(KeyboardInterrupt):
                command.handle(events_only=True, moderation_only=False)
        deliver.assert_called_once_with(deliver_events=True, deliver_moderation=False)

    def test_moderation_worker_never_processes_incident_events(self):
        from api.management.commands.discord_report_worker import Command

        command = Command()
        with patch.object(
            command, "_deliver_batch", side_effect=KeyboardInterrupt
        ) as deliver:
            with self.assertRaises(KeyboardInterrupt):
                command.handle(events_only=False, moderation_only=True)
        deliver.assert_called_once_with(deliver_events=False, deliver_moderation=True)
