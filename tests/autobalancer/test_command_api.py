import json
import os
from contextlib import contextmanager
from types import SimpleNamespace

import pytest

from rcon.autobalancer.store import AutobalancerStore
from tests.autobalancer.test_service import FakeRepository, service, make_snapshot
from tests.autobalancer.test_store import FakeRedis
from tests.autobalancer.test_volunteer_flow import at, config, invitation, proposed


@pytest.fixture
def web(monkeypatch):
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "rconweb.rconweb.test_settings")
    import django

    django.setup()
    from django.test import RequestFactory
    from api import autobalancer as api, auth, audit_log

    store = AutobalancerStore(FakeRedis(), server_number=1)
    store.save_state(proposed())
    repository = FakeRepository()
    monkeypatch.setattr(store, "claim_snapshot_slot", lambda: False)
    monkeypatch.setattr(store, "claim_snapshot_prune", lambda: False)
    monkeypatch.setattr(api, "AutobalancerStore", lambda: store)
    monkeypatch.setattr(api, "_repository", lambda: repository)
    monkeypatch.setattr(api.AutobalancerUserConfig, "load_from_db", config)
    monkeypatch.setattr(api, "datetime", SimpleNamespace(now=lambda tz: at(3005)))
    monkeypatch.setattr(auth, "check_api_key", lambda r: None)
    monkeypatch.setattr("rcon.autobalancer.service.load_history", lambda *a, **kw: {})

    @contextmanager
    def audit_session():
        yield SimpleNamespace(add=lambda entry: None)

    monkeypatch.setattr(audit_log, "enter_session", audit_session)

    def call(name, payload, allowed=True):
        request = RequestFactory().post(
            f"/api/{name}", data=json.dumps(payload), content_type="application/json"
        )
        request.user = SimpleNamespace(
            username="test-admin",
            is_authenticated=True,
            is_active=True,
            has_perms=lambda perms: allowed,
        )
        return json.loads(getattr(api, name)(request).content)

    return store, repository, call


@pytest.mark.parametrize("endpoint", ["validate_autobalancer_config", "set_autobalancer_config"])
def test_invalid_config_is_a_safe_400_and_is_not_saved(web, monkeypatch, endpoint):
    from django.test import RequestFactory
    from api import autobalancer as api

    saved = []
    monkeypatch.setattr(api.AutobalancerUserConfig, "save_to_db", lambda *a, **kw: saved.append(True))
    request = RequestFactory().post(
        f"/api/{endpoint}",
        data=json.dumps({"skill_gap_soft_limit": 100, "skill_gap_hard_warning": 1}),
        content_type="application/json",
    )
    request.user = SimpleNamespace(username="admin", is_authenticated=True, is_active=True, has_perms=lambda perms: True)
    response = getattr(api, endpoint)(request)
    body = json.loads(response.content)
    assert response.status_code == 400
    assert body["failed"] is True
    assert "skill_gap_hard_warning" in body["error"]
    assert saved == []


def test_invalid_template_attribute_is_a_validation_error(web):
    from django.test import RequestFactory
    from api import autobalancer as api

    request = RequestFactory().post(
        "/api/validate_autobalancer_config",
        data=json.dumps({"messages": {"volunteer_request": "{target_team.foo}"}}),
        content_type="application/json",
    )
    request.user = SimpleNamespace(username="admin", is_authenticated=True, is_active=True, has_perms=lambda _: True)
    response = api.validate_autobalancer_config(request)
    assert response.status_code == 400
    assert json.loads(response.content)["failed"] is True


@pytest.mark.parametrize(
    "state",
    [
        proposed(data_pause_started_at=3000),
        {**proposed(), "proposal_expires_at": 3005},
        invitation(),
    ],
)
def test_approval_api_rejects_paused_expired_and_non_proposed_states(web, state):
    store, repository, call = web
    store.save_state(state)
    result = call("approve_autobalancer_proposal", {"decision_id": "decision"})
    assert result["failed"] is True
    assert store.read_events() == []
    assert repository.updated == []


def test_current_manual_proposal_can_still_be_approved(web):
    store, repository, call = web
    result = call("approve_autobalancer_proposal", {"decision_id": "decision"})
    assert result["failed"] is False
    assert store.load_state()["approved_by"] == "test-admin"
    assert store.read_events()[0]["type"] == "approval"


def test_approval_permission_is_still_required(web):
    store, repository, call = web
    response = call(
        "approve_autobalancer_proposal", {"decision_id": "decision"}, allowed=False
    )
    assert response["failed"] is True
    assert "required permissions" in response["error"]
    assert store.read_events() == []
    assert repository.updated == []


def test_api_cancel_disarms_immediately_worker_notifies_once(web):
    store, repository, call = web
    store.save_state(invitation(data_pause_started_at=3000, volunteers=["a0"]))
    store.arm_player("a0")
    result = call(
        "cancel_autobalancer_incident",
        {"incident_id": "invitation", "reason": "Internal admin details"},
    )
    assert result["failed"] is False
    assert not store.is_armed_player("a0")
    instance = service()
    instance.store = store
    instance.repository = repository
    instance.tick(config(), make_snapshot(at(3006)), at(3006))
    assert {player_id for player_id, _ in instance.rcon.messages} == {"a0"}
    assert all(
        "Teamausgleich wurde abgebrochen" in message and "Internal admin" not in message
        for _, message in instance.rcon.messages
    )
    count = len(instance.rcon.messages)
    instance.tick(config(), make_snapshot(at(3010)), at(3010))
    assert len(instance.rcon.messages) == count
    assert instance.rcon.switches == []
