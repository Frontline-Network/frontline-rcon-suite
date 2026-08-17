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


def test_parser_keeps_live_player_stats_in_confirmed_subject():
    parsed = incidents.parse_chat_report(
        "!admin Biene test",
        reporter_context={"team": "Allies"},
        current_players=[
            {
                "name": "Biene",
                "player_id": "biene-id",
                "team": "allies",
                "unit_name": "able",
                "role": "officer",
                "kills": 7,
                "deaths": 3,
                "team_kills": 0,
                "map_playtime_seconds": 1200,
            }
        ],
    )

    subject = parsed["subjects"][0]
    assert subject["player_id"] == "biene-id"
    assert subject["squad_name"] == "able"
    assert subject["snapshot"]["kills"] == 7
    assert subject["snapshot"]["deaths"] == 3
    assert subject["snapshot"]["teamkills"] == 0
    assert subject["snapshot"]["map_playtime_seconds"] == 1200


def test_parser_maps_commander_alias_to_reporter_team_with_stats():
    parsed = incidents.parse_chat_report(
        "!admin commander macht wieder Sachen",
        reporter_context={"team": "Allies"},
        current_players=[
            {
                "name": "Allied Commander",
                "player_id": "allied-command",
                "team": "allies",
                "role": "armycommander",
                "kills": 4,
                "deaths": 2,
                "map_playtime_seconds": 900,
            },
            {
                "name": "Axis Commander",
                "player_id": "axis-command",
                "team": "axis",
                "role": "armycommander",
                "kills": 8,
            },
        ],
    )

    subject = parsed["subjects"][0]
    assert subject["player_id"] == "allied-command"
    assert subject["state"] == "confirmed"
    assert subject["match_method"] == "team_commander"
    assert subject["snapshot"]["kills"] == 4
    assert subject["snapshot"]["deaths"] == 2
    assert subject["snapshot"]["map_playtime_seconds"] == 900


def test_parser_maps_vietnam_commander_role_to_reporter_team():
    parsed = incidents.parse_chat_report(
        "!admin Kommandant sabotiert das Team",
        reporter_context={"team": "axis"},
        current_players=[
            {
                "name": "Vietnam Commander",
                "player_id": "hllv-command",
                "team": "axis",
                "role": "commander",
            }
        ],
    )

    assert parsed["target_id"] == "hllv-command"
    assert parsed["subjects"][0]["role"] == "commander"


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


def test_parser_resolves_three_named_squads_in_one_report():
    squads = [
        {
            "name": name,
            "team": "Allies",
            "type": "infantry",
            "has_leader": True,
            "leader": {
                "name": f"{name} Lead",
                "player_id": f"{name.casefold()}-leader",
                "role": "Officer",
            },
            "players": [],
        }
        for name in ["Able", "Charlie", "Baker"]
    ]

    parsed = incidents.parse_chat_report(
        "!admin squads able, charlie und baker reden nicht",
        reporter_context={"team": "Allies"},
        current_squads=squads,
    )

    assert [subject["squad_name"] for subject in parsed["subjects"]] == [
        "Able",
        "Charlie",
        "Baker",
    ]
    assert all(subject["state"] == "confirmed" for subject in parsed["subjects"])
    assert sum(bool(subject["is_primary"]) for subject in parsed["subjects"]) == 1


def test_team_view_recognizes_vietnam_squadleader_and_normalizes_teamkills():
    squads = incidents.flatten_team_view(
        {
            "allies": {
                "squads": {
                    "able": {
                        "type": "infantry",
                        "has_leader": True,
                        "players": [
                            {
                                "name": "Biene",
                                "player_id": "eos-id",
                                "role": "squadleader",
                                "team_kills": 0,
                            }
                        ],
                    }
                }
            },
            "fail_count": 0,
        }
    )

    assert squads[0]["leader"]["player_id"] == "eos-id"
    assert squads[0]["leader"]["teamkills"] == 0
    assert squads[0]["players"][0]["teamkills"] == 0


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


def test_reassignment_records_the_selected_admin_and_handover_note(incident_database):
    incident, _ = incidents.create_incident(
        server_number=2,
        source="manual",
        reason="handover",
        actor="alice",
    )

    reassigned = incidents.mutate_incident(
        incident["id"],
        actor="alice",
        expected_revision=incident["revision"],
        operation="reassign",
        payload={
            "assigned_to": "bob",
            "handover_note": "Bitte die letzten Teamkills prüfen.",
        },
    )

    assert reassigned["status"] == "claimed"
    assert reassigned["assigned_to"] == "bob"
    assert reassigned["events"][-1]["event_type"] == "reassign"
    assert reassigned["events"][-1]["payload"] == {
        "assigned_to": "bob",
        "handover_note": "Bitte die letzten Teamkills prüfen.",
    }


def test_first_closer_becomes_owner_and_other_admin_cannot_close(incident_database):
    incident, _ = incidents.create_incident(
        server_number=2,
        source="manual",
        reason="first button wins",
        actor="system",
    )
    closed = incidents.mutate_incident(
        incident["id"],
        actor="discord:1:Alice",
        expected_revision=incident["revision"],
        operation="dismissed",
        idempotency_key="dismiss-by-alice",
    )
    assert closed["status"] == "dismissed"
    assert closed["assigned_to"] == "discord:1:Alice"

    second, _ = incidents.create_incident(
        server_number=2,
        source="manual",
        reason="already owned",
        actor="system",
    )
    claimed = incidents.mutate_incident(
        second["id"],
        actor="discord:1:Alice",
        expected_revision=second["revision"],
        operation="claim",
        idempotency_key="claim-by-alice",
    )
    with pytest.raises(incidents.IncidentConflict, match="another admin"):
        incidents.mutate_incident(
            second["id"],
            actor="discord:2:Bob",
            expected_revision=claimed["revision"],
            operation="resolved",
            idempotency_key="resolve-by-bob",
        )


def test_stale_first_button_returns_current_claim_only_to_owner(incident_database):
    incident, _ = incidents.create_incident(
        server_number=1,
        source="manual",
        reason="stale Discord message",
        actor="system",
    )
    claimed = incidents.mutate_incident(
        incident["id"],
        actor="discord:1:Alice",
        expected_revision=incident["revision"],
        operation="claim",
        idempotency_key="first-click-alice",
    )
    retry = incidents.mutate_incident(
        incident["id"],
        actor="discord:1:Alice",
        expected_revision=incident["revision"],
        operation="claim",
        idempotency_key="stale-click-alice",
    )
    assert retry["revision"] == claimed["revision"]
    manual = incidents.mutate_incident(
        incident["id"],
        actor="discord:1:Alice",
        expected_revision=incident["revision"],
        operation="claim",
        payload={"mode": "manual"},
        idempotency_key="stale-manual-alice",
    )
    assert manual["revision"] == claimed["revision"] + 1
    assert manual["events"][-1]["payload"] == {"mode": "manual"}
    with pytest.raises(incidents.IncidentConflict, match="another admin"):
        incidents.mutate_incident(
            incident["id"],
            actor="discord:2:Bob",
            expected_revision=incident["revision"],
            operation="claim",
            idempotency_key="stale-click-bob",
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


def test_action_reservation_claims_incident_and_confirms_selected_suggestion(
    incident_database,
):
    incident, _ = incidents.create_incident(
        server_number=1,
        source="chat",
        reason="possible cheating",
        actor="system:chat",
        subjects=[
            {
                "kind": "player",
                "state": "suggested",
                "display_name": "Bob",
                "player_id": "bob",
                "confidence": 0.76,
                "match_method": "fuzzy",
            }
        ],
    )
    subject_id = incident["subjects"][0]["id"]

    _, created = incidents.reserve_incident_action(
        incident["id"],
        actor="alice",
        action="punish",
        arguments={"player_id": "bob", "subject_id": subject_id, "reason": "Check"},
        idempotency_key="claim-with-action-1",
        confirm_subject_id=subject_id,
    )

    updated = incidents.get_incident(incident["id"])
    assert created is True
    assert updated["status"] == "claimed"
    assert updated["assigned_to"] == "alice"
    assert updated["primary_subject"]["id"] == subject_id
    assert updated["primary_subject"]["state"] == "confirmed"
    assert {event["event_type"] for event in updated["events"]} >= {
        "claim",
        "subject_confirmed",
        "action_started",
    }


def test_disband_squad_action_reserves_confirmed_squad(incident_database):
    incident, _ = incidents.create_incident(
        server_number=1,
        source="chat",
        reason="squad issue",
        actor="system:chat",
        subjects=[
            {
                "kind": "squad",
                "state": "confirmed",
                "display_name": "Able",
                "team": "allies",
                "squad_name": "Able",
                "squad_type": "infantry",
            }
        ],
    )
    subject_id = incident["subjects"][0]["id"]

    _, created = incidents.reserve_incident_action(
        incident["id"],
        actor="alice",
        action="disband_squad",
        arguments={"subject_id": subject_id, "reason": "No squad leader"},
        idempotency_key="disband-squad-1",
        validate_action_subject=True,
    )

    updated = incidents.get_incident(incident["id"])
    assert created is True
    assert updated["status"] == "claimed"
    assert updated["assigned_to"] == "alice"
    assert updated["events"][-1]["event_type"] == "action_started"


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


def test_general_incident_allows_explicit_reporter_action_without_subject(
    incident_database,
):
    incident, _ = incidents.create_incident(
        server_number=1,
        source="chat",
        reporter_id="reporter-id",
        reporter_name="Reporter",
        reason="General request for an admin",
        actor="system:chat",
    )

    with pytest.raises(ValueError):
        incidents.confirmed_action_subject(incident, player_id="reporter-id")

    reporter = incidents.confirmed_action_subject(
        incident,
        player_id="reporter-id",
        allow_reporter=True,
    )
    assert reporter == {
        "id": None,
        "kind": "reporter",
        "state": "contact",
        "player_id": "reporter-id",
        "display_name": "Reporter",
    }

    _, created = incidents.reserve_incident_action(
        incident["id"],
        actor="alice",
        action="message",
        arguments={
            "player_id": "reporter-id",
            "player_name": "Reporter",
            "reporter_action": True,
            "message": "We are looking into this.",
        },
        idempotency_key="reporter-message-1",
        validate_action_subject=True,
    )
    updated = incidents.get_incident(incident["id"])
    assert created is True
    assert updated["status"] == "claimed"
    assert updated["target_id"] is None
    assert updated["primary_subject"] is None


def test_explicit_reporter_message_remains_available_with_accused_player(
    incident_database,
):
    incident, _ = incidents.create_incident(
        server_number=1,
        source="chat",
        reporter_id="reporter-id",
        reporter_name="Reporter",
        reason="Target is teamkilling",
        actor="system:chat",
        subjects=[
            {
                "kind": "player",
                "state": "confirmed",
                "is_primary": True,
                "display_name": "Target",
                "player_id": "target-id",
            }
        ],
    )
    reporter = incidents.confirmed_action_subject(
        incident,
        player_id="reporter-id",
        allow_reporter=True,
    )
    assert reporter["kind"] == "reporter"
    assert reporter["player_id"] == "reporter-id"


def test_end_to_end_chat_report_to_resolved_incident(incident_database, monkeypatch):
    monkeypatch.setenv("MOBILE_CONTEXT_V2", "enabled")
    players = [
        {
            "player_id": "reporter-id",
            "name": "Reporter",
            "team": "Allies",
            "unit_name": "Charlie",
            "role": "rifleman",
        },
        {
            "player_id": "target-id",
            "name": "Biene",
            "team": "Allies",
            "unit_name": "Charlie",
            "role": "officer",
        },
    ]
    squads = [
        {
            "name": "Charlie",
            "team": "Allies",
            "type": "infantry",
            "has_leader": True,
            "leader": {"player_id": "target-id", "name": "Biene"},
            "players": players[1:],
        }
    ]

    incident, created = incidents.create_incident_from_chat(
        {
            "player_id_1": "reporter-id",
            "player_name_1": "Reporter",
            "sub_content": "!admin Charlie Biene meldet Teamkill",
        },
        current_players=players,
        current_squads=squads,
    )

    assert created is True
    assert incident["source"] == "chat"
    assert incident["reporter_context"]["unit_name"] == "Charlie"
    assert {
        (subject["kind"], subject["state"]) for subject in incident["subjects"]
    } == {
        ("squad", "confirmed"),
        ("player", "confirmed"),
    }

    claimed = incidents.mutate_incident(
        incident["id"],
        actor="mobile-admin",
        expected_revision=incident["revision"],
        operation="claim",
        idempotency_key="e2e-claim",
    )
    player_subject = next(
        subject for subject in claimed["subjects"] if subject["kind"] == "player"
    )
    target = incidents.confirmed_action_subject(
        claimed,
        player_id="target-id",
        subject_id=player_subject["id"],
    )
    assert target["display_name"] == "Biene"

    reservation, first_action = incidents.reserve_incident_action(
        incident["id"],
        actor="mobile-admin",
        action="temp_ban",
        arguments={
            "player_id": "target-id",
            "subject_id": target["id"],
            "reason": "Teamkill",
            "duration_hours": 2,
            "confirmed": True,
        },
        idempotency_key="e2e-tempban",
    )
    assert first_action is True
    completed = incidents.complete_incident_action(
        "e2e-tempban", result={"ok": True, "action": "temp_ban"}
    )
    retry, retry_created = incidents.reserve_incident_action(
        incident["id"],
        actor="mobile-admin",
        action="temp_ban",
        arguments={"player_id": "target-id"},
        idempotency_key="e2e-tempban",
    )
    assert retry_created is False
    assert retry["event_type"] == "action"
    assert retry["payload"]["idempotency_key"] == "e2e-tempban"
    assert completed["revision"] == claimed["revision"] + 2

    resolved = incidents.mutate_incident(
        incident["id"],
        actor="mobile-admin",
        expected_revision=completed["revision"],
        operation="resolved",
        payload={"note": "Tempban ausgeführt und geprüft"},
        idempotency_key="e2e-resolve",
    )
    assert resolved["status"] == "resolved"
    assert {event["event_type"] for event in resolved["events"]} >= {
        "created",
        "claim",
        "action_started",
        "action",
        "resolved",
    }
