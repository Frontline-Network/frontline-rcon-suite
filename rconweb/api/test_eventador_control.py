import json
import os
import tempfile
import uuid
from datetime import timedelta
from io import StringIO
from unittest.mock import patch

from django.contrib.auth.models import Permission, User
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import RequestFactory, TestCase
from django.utils import timezone

from rcon.game.hllv.profile import HLLV_PROFILE

from . import eventador_control
from .eventador_control_contract import build_state
from .models import DjangoAPIKey, EventadorControlStep


class FakeHistory:
    def get_current_map(self):
        return {
            "name": "wdeve_warfare_day",
            "start": 1_789_752_600,
            "end": None,
        }


class FakeRcon:
    game_profile = HLLV_PROFILE

    def __init__(self):
        self.calls = []
        self.fail_map = False

    def get_status(self):
        return {
            "server_number": 1,
            "game": "hllv",
            "map": "wdeve_warfare_day",
            "current_players": 2,
        }

    def get_players(self):
        return []

    def get_map(self):
        return "wdeve_warfare_day"

    def get_all_player_info(self):
        return [
            {"iD": "steam:1", "team": 1},
            {"iD": "steam:2", "team": 2},
        ]

    def set_map(self, map_id):
        self.calls.append(("set_map", map_id))
        if self.fail_map:
            raise TimeoutError("fixture timeout after dispatch")

    def set_broadcast(self, message):
        self.calls.append(("set_broadcast", message))

    def message_player(self, player_id, message):
        self.calls.append(("message_player", player_id, message))
        return True

    def switch_player_now(self, player_id):
        self.calls.append(("switch_player_now", player_id))
        return True


class EventadorControlApiTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.api = FakeRcon()
        self.history = patch("api.eventador_control_contract.MapsHistory", FakeHistory)
        self.server = patch(
            "api.eventador_control_contract.get_server_number", return_value="1"
        )
        self.provider = patch("api.eventador_control.rcon_api", self.api)
        self.enabled = patch.dict("os.environ", {"EVENTADOR_CONTROL_ENABLED": "true"})
        for fixture in (self.history, self.server, self.provider, self.enabled):
            fixture.start()
            self.addCleanup(fixture.stop)

        permission = Permission.objects.get(codename="can_control_eventador_events")
        self.user = User.objects.create_user(username="eventador-control")
        self.user.set_unusable_password()
        self.user.save(update_fields=("password",))
        self.user.user_permissions.add(permission)
        self.raw_key = "eventador-test-key-0123456789abcdef"
        DjangoAPIKey.objects.create(
            user=self.user, api_key=self.raw_key, notes="Eventador test identity"
        )

    def request(self, method, path, body=None, key=None):
        headers = {}
        if key is not False:
            headers["HTTP_AUTHORIZATION"] = f"Bearer {key or self.raw_key}"
        if method == "get":
            return self.factory.get(path, **headers)
        return self.factory.post(
            path,
            data=json.dumps(body or {}),
            content_type="application/json",
            **headers,
        )

    @staticmethod
    def payload(response):
        return json.loads(response.content)

    def plan(self, **updates):
        observed = build_state(self.api)
        value = {
            "schema_version": 1,
            "event_id": "10000000-0000-4000-8000-000000000001",
            "event_revision": 4,
            "workflow_revision": 2,
            "step_id": "round-1-map",
            "idempotency_key": "20000000-0000-4000-8000-000000000001",
            "execute_at": timezone.now().isoformat(),
            "target": {"server_number": 1, "game": "hllv"},
            "action": "set_map",
            "reason": "Start approved first round",
            "arguments": {"map": "wdevd_warfare_day"},
            "expected": {
                "map": observed["map"],
                "round_id": observed["round_id"],
                "roster_hash": observed["roster_hash"],
                "state_observed_at": timezone.now().isoformat(),
                "previous_step_id": None,
            },
        }
        value.update(updates)
        return value

    def prepare(self, plan=None):
        return eventador_control.prepare_step(
            self.request("post", "/api/eventador/v1/steps/prepare", plan or self.plan())
        )

    def test_requires_bearer_api_key_and_dedicated_permission(self):
        missing = eventador_control.capabilities(
            self.request("get", "/api/eventador/v1/capabilities", key=False)
        )
        self.assertEqual(missing.status_code, 401)

        other = User.objects.create_user(username="other-service")
        raw_other = "other-service-key-0123456789abcdef"
        DjangoAPIKey.objects.create(user=other, api_key=raw_other)
        forbidden = eventador_control.capabilities(
            self.request("get", "/api/eventador/v1/capabilities", key=raw_other)
        )
        self.assertEqual(forbidden.status_code, 403)

        allowed = eventador_control.capabilities(
            self.request("get", "/api/eventador/v1/capabilities")
        )
        self.assertEqual(allowed.status_code, 200)
        value = self.payload(allowed)["result"]
        self.assertEqual(value["game"], "hllv")
        self.assertTrue(value["execution_enabled"])

        self.user.is_staff = True
        self.user.save(update_fields=("is_staff",))
        privileged = eventador_control.capabilities(
            self.request("get", "/api/eventador/v1/capabilities")
        )
        self.assertEqual(privileged.status_code, 403)

    def test_prepare_execute_and_result_are_idempotent(self):
        frozen = self.plan()
        first = self.prepare(frozen)
        self.assertEqual(first.status_code, 200)
        prepared = self.payload(first)["result"]
        self.assertEqual(prepared["state"], "prepared")
        self.assertFalse(prepared["cached"])
        self.assertTrue(prepared["confirmation_required"])
        self.assertEqual(EventadorControlStep.objects.count(), 1)
        self.assertEqual(
            EventadorControlStep.objects.get().prepared_by, "eventador-control"
        )

        replay = self.payload(self.prepare(frozen))["result"]
        self.assertEqual(replay["preparation_id"], prepared["preparation_id"])
        self.assertEqual(replay["confirmation_token"], prepared["confirmation_token"])
        self.assertTrue(replay["cached"])
        self.assertEqual(EventadorControlStep.objects.count(), 1)

        executed_response = eventador_control.execute_step(
            self.request(
                "post",
                f"/api/eventador/v1/steps/{prepared['preparation_id']}/execute",
                {"confirmation_token": prepared["confirmation_token"]},
            ),
            uuid.UUID(prepared["preparation_id"]),
        )
        executed = self.payload(executed_response)["result"]
        self.assertEqual(executed["state"], "succeeded")
        self.assertEqual(self.api.calls, [("set_map", "wdevd_warfare_day")])

        replayed_execution = eventador_control.execute_step(
            self.request(
                "post",
                f"/api/eventador/v1/steps/{prepared['preparation_id']}/execute",
                {"confirmation_token": prepared["confirmation_token"]},
            ),
            uuid.UUID(prepared["preparation_id"]),
        )
        self.assertTrue(self.payload(replayed_execution)["result"]["cached"])
        self.assertEqual(self.api.calls, [("set_map", "wdevd_warfare_day")])

        result = eventador_control.result(
            self.request(
                "get",
                "/api/eventador/v1/results/20000000-0000-4000-8000-000000000001",
            ),
            uuid.UUID("20000000-0000-4000-8000-000000000001"),
        )
        self.assertEqual(self.payload(result)["result"]["state"], "succeeded")

    def test_stale_state_and_missing_previous_step_are_terminal_conflicts(self):
        stale = self.plan()
        stale["expected"]["state_observed_at"] = (
            timezone.now() - timedelta(minutes=1)
        ).isoformat()
        stale_result = self.payload(self.prepare(stale))["result"]
        self.assertEqual(stale_result["state"], "conflict")
        self.assertEqual(stale_result["error_code"], "state_observation_stale")
        self.assertNotIn("confirmation_token", stale_result)

        missing_previous = self.plan(
            step_id="round-2-map",
            idempotency_key="20000000-0000-4000-8000-000000000002",
        )
        missing_previous["expected"]["previous_step_id"] = "round-1-message"
        previous_result = self.payload(self.prepare(missing_previous))["result"]
        self.assertEqual(previous_result["state"], "conflict")
        self.assertEqual(previous_result["error_code"], "previous_step_not_succeeded")

    def test_execution_is_blocked_before_the_bound_time(self):
        future = self.plan(
            execute_at=(timezone.now() + timedelta(minutes=1)).isoformat()
        )
        prepared = self.payload(self.prepare(future))["result"]
        response = eventador_control.execute_step(
            self.request(
                "post",
                f"/api/eventador/v1/steps/{prepared['preparation_id']}/execute",
                {"confirmation_token": prepared["confirmation_token"]},
            ),
            uuid.UUID(prepared["preparation_id"]),
        )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(EventadorControlStep.objects.get().state, "prepared")
        self.assertEqual(self.api.calls, [])

    def test_unknown_dispatch_result_is_never_replayed(self):
        prepared = self.payload(self.prepare())["result"]
        self.api.fail_map = True
        first = eventador_control.execute_step(
            self.request(
                "post",
                f"/api/eventador/v1/steps/{prepared['preparation_id']}/execute",
                {"confirmation_token": prepared["confirmation_token"]},
            ),
            uuid.UUID(prepared["preparation_id"]),
        )
        self.assertEqual(self.payload(first)["result"]["state"], "unknown")
        self.assertEqual(len(self.api.calls), 1)

        second = eventador_control.execute_step(
            self.request(
                "post",
                f"/api/eventador/v1/steps/{prepared['preparation_id']}/execute",
                {"confirmation_token": prepared["confirmation_token"]},
            ),
            uuid.UUID(prepared["preparation_id"]),
        )
        self.assertEqual(self.payload(second)["result"]["state"], "unknown")
        self.assertEqual(len(self.api.calls), 1)

    def test_restart_marks_abandoned_executing_receipt_unknown(self):
        prepared = self.payload(self.prepare())["result"]
        step = EventadorControlStep.objects.get()
        step.state = EventadorControlStep.State.EXECUTING
        step.execution_started_at = timezone.now() - timedelta(minutes=1)
        step.save(update_fields=("state", "execution_started_at", "updated_at"))

        response = eventador_control.result(
            self.request("get", f"/api/eventador/v1/results/{step.idempotency_key}"),
            step.idempotency_key,
        )
        result = self.payload(response)["result"]
        self.assertEqual(result["preparation_id"], prepared["preparation_id"])
        self.assertEqual(result["state"], "unknown")
        self.assertEqual(result["error_code"], "execution_outcome_unknown")

    def test_disabled_switch_keeps_mutations_unreachable(self):
        with patch.dict("os.environ", {"EVENTADOR_CONTROL_ENABLED": "false"}):
            capabilities = eventador_control.capabilities(
                self.request("get", "/api/eventador/v1/capabilities")
            )
            self.assertFalse(self.payload(capabilities)["result"]["execution_enabled"])
            prepared = self.prepare()
            self.assertEqual(prepared.status_code, 409)
            self.assertEqual(EventadorControlStep.objects.count(), 0)

    def test_identity_provisioning_requires_explicit_rotation_and_hides_key(self):
        replacement = "replacement-eventador-key-0123456789abcdef"
        handle = tempfile.NamedTemporaryFile(delete=False)
        try:
            handle.write(replacement.encode("ascii"))
            handle.close()
            os.chmod(handle.name, 0o600)
            with self.assertRaises(CommandError):
                call_command(
                    "provision_eventador_control_identity",
                    key_file=handle.name,
                )
            output = StringIO()
            call_command(
                "provision_eventador_control_identity",
                key_file=handle.name,
                rotate=True,
                stdout=output,
            )
        finally:
            handle.close()
            os.unlink(handle.name)

        self.user.refresh_from_db()
        self.assertFalse(self.user.is_staff)
        self.assertFalse(self.user.is_superuser)
        self.assertEqual(
            set(self.user.user_permissions.values_list("codename", flat=True)),
            {"can_control_eventador_events"},
        )
        self.assertNotIn(replacement, output.getvalue())
        old_key = eventador_control.capabilities(
            self.request("get", "/api/eventador/v1/capabilities")
        )
        self.assertEqual(old_key.status_code, 401)
        new_key = eventador_control.capabilities(
            self.request("get", "/api/eventador/v1/capabilities", key=replacement)
        )
        self.assertEqual(new_key.status_code, 200)
