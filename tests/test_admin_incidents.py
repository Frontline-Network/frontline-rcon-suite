import os
from contextlib import contextmanager

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ.setdefault("SERVER_NUMBER", "1")
os.environ.setdefault("DEBUG", "1")

import rcon.admin_incidents as incidents
from rcon.models import AdminIncident, AdminIncidentEvent, AdminIncidentSubject


@pytest.fixture
def incident_database(monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    AdminIncident.__table__.create(engine)
    AdminIncidentSubject.__table__.create(engine)
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


def test_disabled_context_keeps_legacy_prefix_matching():
    players = [{"name": "Bob", "player_id": "bob"}]
    prefixed = incidents.parse_chat_report(
        "!admin Bob team killing", current_players=players, context_mode="disabled"
    )
    embedded = incidents.parse_chat_report(
        "!admin please inspect Bob", current_players=players, context_mode="disabled"
    )
    assert prefixed["target_id"] == "bob"
    assert prefixed["subjects"] == []
    assert embedded["target_id"] is None


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
    assert {subject["state"] for subject in parsed["subjects"]} == {"suggested"}


def test_parser_recognizes_multiple_players_anywhere_in_message():
    parsed = incidents.parse_chat_report(
        "!admin Charlie is griefing and Easy Company Bob is helping",
        current_players=[
            {"name": "Charlie", "player_id": "charlie", "team": "Allies"},
            {
                "name": "Easy Company Bob",
                "player_id": "bob",
                "team": "Allies",
            },
        ],
    )
    assert [subject["player_id"] for subject in parsed["subjects"]] == [
        "charlie",
        "bob",
    ]
    assert parsed["subjects"][0]["is_primary"] is True
    assert parsed["target_id"] == "charlie"


def test_parser_recognizes_reporter_team_squad_and_captures_members():
    parsed = incidents.parse_chat_report(
        "!admin Item keine Kommunikation",
        reporter_context={"team": "Allies"},
        current_squads=[
            {
                "name": "Item",
                "team": "Allies",
                "type": "infantry",
                "has_leader": True,
                "leader": {
                    "name": "Leader",
                    "player_id": "leader",
                    "role": "Officer",
                },
                "players": [
                    {"name": "Leader", "player_id": "leader", "role": "Officer"},
                    {"name": "Member", "player_id": "member", "role": "Rifleman"},
                ],
            },
            {"name": "Item", "team": "Axis", "players": []},
        ],
    )
    subject = parsed["subjects"][0]
    assert subject["kind"] == "squad"
    assert subject["state"] == "confirmed"
    assert subject["leader_player_id"] == "leader"
    assert len(subject["snapshot"]["players"]) == 2


@pytest.mark.parametrize(
    "squad_name",
    [
        "Able",
        "Baker",
        "Charlie",
        "Dog",
        "Easy",
        "Fox",
        "George",
        "How",
        "Item",
        "Jig",
        "King",
        "Love",
        "Mike",
    ],
)
def test_parser_recognizes_every_squad_from_live_team_view(squad_name):
    current_squads = incidents.flatten_team_view(
        {
            "allies": {
                "squads": {
                    squad_name.casefold(): {
                        "type": "infantry",
                        "has_leader": True,
                        "players": [
                            {
                                "name": "Leader",
                                "player_id": "leader",
                                "team": "allies",
                                "unit_name": squad_name.casefold(),
                                "role": "officer",
                            }
                        ],
                    }
                }
            },
            "axis": {"squads": {}},
            "fail_count": 0,
        }
    )
    parsed = incidents.parse_chat_report(
        f"!admin {squad_name} spricht nicht",
        reporter_context={"team": "Team.ALLIES"},
        current_squads=current_squads,
    )
    subject = parsed["subjects"][0]
    assert subject["kind"] == "squad"
    assert subject["state"] == "confirmed"
    assert subject["squad_name"] == squad_name.casefold()


def test_chat_ingestion_persists_dynamic_squad_context(incident_database, monkeypatch):
    monkeypatch.setenv("MOBILE_CONTEXT_V2", "enabled")
    monkeypatch.setattr(incidents, "get_server_number", lambda: 2)
    result, created = incidents.create_incident_from_chat(
        {
            "sub_content": "!admin Able spricht nicht",
            "player_id_1": "reporter",
            "player_name_1": "Reporter",
        },
        current_players=[
            {
                "player_id": "reporter",
                "name": "Reporter",
                "team": "Allies",
                "unit_name": "Baker",
                "role": "Officer",
            },
            {
                "player_id": "leader",
                "name": "Leader",
                "team": "Allies",
                "unit_name": "Able",
                "role": "Officer",
            },
        ],
        current_squads=[
            {
                "name": "Able",
                "team": "Allies",
                "type": "infantry",
                "has_leader": True,
                "leader": {
                    "player_id": "leader",
                    "name": "Leader",
                    "role": "Officer",
                },
                "players": [
                    {"player_id": "leader", "name": "Leader", "role": "Officer"},
                ],
            }
        ],
    )

    assert created is True
    assert result["server_number"] == 2
    assert result["target_id"] == "leader"
    assert result["subjects"][0]["kind"] == "squad"
    assert result["subjects"][0]["squad_name"] == "Able"
    assert result["reporter_context"]["unit_name"] == "Baker"


def test_parser_resolves_unique_player_name_anywhere_in_report():
    parsed = incidents.parse_chat_report(
        "!admin bitte prüft Biene wegen Teamkill",
        current_players=[
            {
                "name": "Biene",
                "player_id": "biene-id",
                "team": "allies",
                "unit_name": "able",
            }
        ],
    )
    assert parsed["target_id"] == "biene-id"
    assert parsed["subjects"][0]["state"] == "confirmed"


def test_fuzzy_player_is_never_confirmed_automatically():
    parsed = incidents.parse_chat_report(
        "!admin Eazy Company Bob team killing",
        current_players=[{"name": "Easy Company Bob", "player_id": "bob"}],
    )
    assert parsed["target_id"] is None
    assert parsed["subjects"][0]["state"] == "suggested"
    assert parsed["subjects"][0]["match_method"] == "fuzzy"


def test_fuzzy_squad_is_never_confirmed_or_action_target():
    parsed = incidents.parse_chat_report(
        "!admin Bakre spricht nicht",
        reporter_context={"team": "Allies"},
        current_squads=[
            {
                "name": "Baker",
                "team": "Allies",
                "type": "infantry",
                "has_leader": False,
                "players": [],
            }
        ],
    )
    assert parsed["target_id"] is None
    assert parsed["subjects"][0]["kind"] == "squad"
    assert parsed["subjects"][0]["state"] == "suggested"
    assert parsed["subjects"][0]["match_method"] == "squad_fuzzy"


def test_player_and_squad_name_collision_keeps_both_contexts():
    parsed = incidents.parse_chat_report(
        "!admin Able meldet einen Vorfall",
        reporter_context={"team": "Allies"},
        current_players=[
            {"name": "Able", "player_id": "able-player", "team": "Allies"}
        ],
        current_squads=[
            {
                "name": "Able",
                "team": "Allies",
                "type": "infantry",
                "has_leader": False,
                "players": [],
            }
        ],
    )
    assert {(subject["kind"], subject["state"]) for subject in parsed["subjects"]} == {
        ("player", "confirmed"),
        ("squad", "confirmed"),
    }


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


def test_subject_confirmation_and_primary_target_use_revision(incident_database):
    incident, _ = incidents.create_incident(
        server_number=1,
        source="chat",
        reason="possible team killing",
        actor="system:chat",
        subjects=[
            {
                "kind": "player",
                "state": "suggested",
                "display_name": "Bob",
                "player_id": "bob",
                "confidence": 0.8,
                "match_method": "fuzzy",
            }
        ],
    )
    subject_id = incident["subjects"][0]["id"]
    confirmed = incidents.mutate_incident_subject(
        incident["id"],
        actor="alice",
        expected_revision=incident["revision"],
        operation="confirm",
        payload={},
        subject_id=subject_id,
        idempotency_key="confirm-subject-1",
    )
    assert confirmed["target_id"] == "bob"
    assert confirmed["primary_subject"]["id"] == subject_id
    assert confirmed["subjects"][0]["confirmed_by"] == "alice"


def test_action_target_must_belong_to_confirmed_subject(incident_database):
    incident, _ = incidents.create_incident(
        server_number=1,
        source="chat",
        reason="squad report",
        actor="system:chat",
        subjects=[
            {
                "kind": "squad",
                "state": "confirmed",
                "is_primary": True,
                "display_name": "Item",
                "squad_name": "Item",
                "snapshot": {
                    "players": [
                        {"name": "Leader", "player_id": "leader"},
                        {"name": "Member", "player_id": "member"},
                    ]
                },
            }
        ],
    )
    subject = incidents.confirmed_action_subject(incident, player_id="member")
    assert subject["kind"] == "squad"
    with pytest.raises(ValueError):
        incidents.confirmed_action_subject(incident, player_id="outsider")
