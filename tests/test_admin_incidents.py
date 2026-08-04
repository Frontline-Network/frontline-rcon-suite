import os
from contextlib import contextmanager

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ.setdefault("SERVER_NUMBER", "1")
os.environ.setdefault("DEBUG", "1")

import rcon.admin_incidents as incidents
from rcon.models import AdminIncident, AdminIncidentEvent


@pytest.fixture
def incident_database(monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    AdminIncident.__table__.create(engine)
    AdminIncidentEvent.__table__.create(engine)
    sessions = sessionmaker(engine, expire_on_commit=False)

    @contextmanager
    def enter_test_session():
        session = sessions()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    monkeypatch.setattr(incidents, "enter_session", enter_test_session)
    return enter_test_session


def test_trigger_parser_links_only_a_unique_longest_player_name():
    parsed = incidents.parse_chat_report(
        "!admin Easy Company Bob team killing at HQ",
        current_players=[
            {"name": "Easy", "player_id": "short"},
            {"name": "Easy Company Bob", "player_id": "exact"},
        ],
    )
    assert parsed["target_id"] == "exact"
    assert parsed["reason"] == "team killing at HQ"


def test_trigger_parser_leaves_ambiguous_player_unlinked():
    parsed = incidents.parse_chat_report(
        "!admin Bob team killing",
        current_players=[
            {"name": "Bob", "player_id": "one"},
            {"name": "Bob", "player_id": "two"},
        ],
    )
    assert parsed["target_id"] is None
    assert parsed["target_name"] is None


def test_duplicate_chat_report_is_collapsed_for_sixty_seconds(incident_database):
    first, created = incidents.create_incident(
        server_number=1,
        source="chat",
        reason="team killing",
        raw_message="!admin Bob team killing",
        reporter_id="reporter",
        actor="system:chat",
    )
    second, duplicate_created = incidents.create_incident(
        server_number=1,
        source="chat",
        reason="team killing",
        raw_message="!admin Bob team killing",
        reporter_id="reporter",
        actor="system:chat",
    )
    assert created is True
    assert duplicate_created is False
    assert second["id"] == first["id"]


def test_claim_uses_revision_and_prevents_takeover(incident_database):
    incident, _ = incidents.create_incident(
        server_number=2,
        source="manual",
        reason="investigate player",
        actor="alice",
    )
    claimed = incidents.mutate_incident(
        incident["id"],
        actor="alice",
        expected_revision=incident["revision"],
        operation="claim",
    )
    assert claimed["assigned_to"] == "alice"
    with pytest.raises(incidents.IncidentConflict):
        incidents.mutate_incident(
            incident["id"],
            actor="bob",
            expected_revision=claimed["revision"],
            operation="claim",
        )


def test_action_idempotency_key_is_reserved_once(incident_database):
    incident, _ = incidents.create_incident(
        server_number=1,
        source="manual",
        reason="action test",
        actor="alice",
    )
    first, created = incidents.reserve_incident_action(
        incident["id"],
        actor="alice",
        action="kick",
        arguments={"reason": "TK"},
        idempotency_key="mobile-action-1",
    )
    second, duplicate_created = incidents.reserve_incident_action(
        incident["id"],
        actor="alice",
        action="kick",
        arguments={"reason": "TK"},
        idempotency_key="mobile-action-1",
    )
    assert created is True
    assert duplicate_created is False
    assert second["id"] == first["id"]

    cursor = incidents.latest_incident_event_cursor()
    completed = incidents.complete_incident_action(
        "mobile-action-1", result={"ok": True}
    )
    changes, next_cursor = incidents.list_incident_changes(cursor)
    outcome, retry_created = incidents.reserve_incident_action(
        incident["id"],
        actor="alice",
        action="kick",
        arguments={"reason": "TK"},
        idempotency_key="mobile-action-1",
    )
    assert completed["revision"] == incident["revision"] + 2
    assert [change["id"] for change in changes] == [incident["id"]]
    assert next_cursor > cursor
    assert retry_created is False
    assert outcome["event_type"] == "action"


def test_manual_creation_idempotency_returns_original_incident(incident_database):
    first, created = incidents.create_incident(
        server_number=1,
        source="manual",
        reason="first request",
        actor="alice",
        idempotency_key="manual-create-1",
    )
    second, duplicate_created = incidents.create_incident(
        server_number=1,
        source="manual",
        reason="retried request",
        actor="alice",
        idempotency_key="manual-create-1",
    )
    assert created is True
    assert duplicate_created is False
    assert second["id"] == first["id"]
    assert second["reason"] == "first request"


def test_mutation_idempotency_survives_response_retry(incident_database):
    incident, _ = incidents.create_incident(
        server_number=1,
        source="manual",
        reason="claim retry",
        actor="alice",
    )
    first = incidents.mutate_incident(
        incident["id"],
        actor="alice",
        expected_revision=incident["revision"],
        operation="claim",
        idempotency_key="claim-1",
    )
    second = incidents.mutate_incident(
        incident["id"],
        actor="alice",
        expected_revision=incident["revision"],
        operation="claim",
        idempotency_key="claim-1",
    )
    assert second["revision"] == first["revision"]
    assert second["assigned_to"] == "alice"
