"""Exercise incident claims while RCON holds a voice message in flight."""

from concurrent.futures import ThreadPoolExecutor
from threading import Event
from unittest.mock import Mock

import pytest
from sqlalchemy import select

from rcon import admin_incidents, voice_reports
from rcon.models import AdminIncident, AdminIncidentEvent, PlayerSession
from tests.test_leadership_vote_postgres import postgres
from tests.test_report_admin import report, service, setup, transport
from tests.test_voice_reports import pilot, snapshot


@pytest.fixture
def db(postgres):
    return postgres


@pytest.mark.parametrize(
    ("worker_delay", "context_delay", "should_send"),
    [(0, 0, True), (4, 0, True), (15, 0, True), (16, 0, False), (4, 12, False)],
)
def test_second_witness_question_uses_scheduled_time(pilot, monkeypatch, worker_delay, context_delay, should_send):
    scenario, advance = pilot
    database, _, context = scenario
    api = transport()
    first = report(scenario, reporter_id="v0")["id"]
    service.tick(api, 1)
    advance(1)
    context["event_time"] = database.clock.now
    second = report(scenario, "!admin Squad-1 redet nicht", reporter_id="v0")["id"]
    service.tick(api, 1)
    advance(59)
    service.tick(api, 1)
    first_prompt = snapshot(database, first)["voice"]
    assert first_prompt["witness_id"] == "v0"
    assert voice_reports.answer(1, first, "v0", True, context)
    advance(1)
    service.tick(api, 1)
    deferred = snapshot(database, second)
    assert deferred["voice"]["witness_id"] == "v0"
    assert deferred["ready_at"] == first_prompt["deadline"] + 1
    advance(deferred["ready_at"] - database.clock.now - 1)
    service.tick(api, 1)
    assert snapshot(database, second)["voice"]["phase"] == "notice_sent"
    advance(1 + worker_delay)
    api.message_player.reset_mock()

    def read_context(_api):
        # Only the second live-context read happens after the send reservation.
        if snapshot(database, second)["voice"]["phase"] == "question_sending":
            advance(context_delay)
        return context

    with monkeypatch.context() as patch:
        patch.setattr(service, "read_context", read_context)
        service.tick(api, 1)
    state = snapshot(database, second)["voice"]
    if not should_send:
        assert state["phase"] == "manual"
        api.message_player.assert_not_called()
        return
    assert state["phase"] == "awaiting_answer"
    assert state["deadline"] == state["question_at"] + 120
    api.message_player.assert_called_once()
    assert api.message_player.call_args.args[0] == "v0"
    service.tick(api, 1)
    api.message_player.assert_called_once()
    reply = {"player_id_1": "v0", "sub_content": "Ja"}
    assert not voice_reports.handle_chat(api, {**reply, "timestamp_ms": first_prompt["question_at"] * 1000}, 1)
    assert voice_reports.handle_chat(api, {**reply, "timestamp_ms": database.clock.now * 1000}, 1)
    assert snapshot(database, second)["voice"]["phase"] == "resolved"
    assert snapshot(database, first)["voice"]["answer_at"] == first_prompt["question_at"]
    api.kick.assert_not_called()


@pytest.mark.parametrize(
    ("reply_delay", "worker_delay", "accepted", "kicked"),
    [
        (119, 0, True, True),
        (119, 5, True, True),
        (119, 30, True, True),
        (119, 31, True, False),
        (1, 31, True, False),
        (120, 0, False, False),
        (121, 0, False, False),
    ],
)
def test_voice_answer_and_dispatch_deadlines(pilot, reply_delay, worker_delay, accepted, kicked):
    scenario, advance = pilot
    database, _, context = scenario
    api = transport()
    case = report(scenario, reporter_id="member")["id"]
    service.tick(api, 1)
    advance(60)
    service.tick(api, 1)
    assert snapshot(database, case)["voice"]["phase"] == "awaiting_answer"
    advance(reply_delay)
    assert voice_reports.answer(1, case, "member", False, context) is accepted
    advance(worker_delay)
    service.tick(api, 1)
    service.tick(api, 1)
    assert snapshot(database, case)["status"] == ("kicked" if kicked else "manual")
    assert api.kick.call_count == int(kicked)


def test_role_change_after_timely_voice_answer_prevents_delayed_kick(pilot):
    scenario, advance = pilot
    database, players, context = scenario
    api = transport()
    case = report(scenario, reporter_id="member")["id"]
    service.tick(api, 1)
    advance(60)
    service.tick(api, 1)
    advance(119)
    assert voice_reports.answer(1, case, "member", False, context)
    next(p for p in players if p["player_id"] == "target")["role"] = "Rifleman"
    advance(5)
    service.tick(api, 1)
    assert snapshot(database, case)["status"] == "manual"
    api.kick.assert_not_called()


def test_missing_round_before_kick_preserves_other_voice_dialog(pilot, monkeypatch):
    scenario, advance = pilot
    database, players, context = scenario
    api = transport()
    runtime = service.Runtime()
    runtime.server = 1
    try:
        runtime.step(api)
        owner = runtime.owner
        assert owner is not None
        first = report(scenario, reporter_id="member")["id"]
        runtime.step(api)
        advance(60)
        runtime.step(api)
        assert voice_reports.answer(1, first, "member", False, context)

        context["event_time"] = database.clock.now
        second = report(scenario, "!admin MissingPerson no comms", reporter_id="v0")["id"]
        assert snapshot(database, second)["voice"]["phase"] == "clarify"
        with monkeypatch.context() as patch:
            reads = Mock(side_effect=[context, ValueError("No recorder-confirmed current round")])
            patch.setattr(service, "read_context", reads)
            runtime.step(api)
            assert reads.call_count == 2
        assert runtime.owner is owner
        assert snapshot(database, first)["status"] == "manual"
        assert snapshot(database, second)["voice"]["phase"] == "clarify"

        advance(5)
        with database() as sess:
            event_id = sess.scalar(select(AdminIncidentEvent.id).where(
                AdminIncidentEvent.incident_id == second,
                AdminIncidentEvent.event_type == "report_admin",
            ))
        name = next(p["name"] for p in players if p["player_id"] == "v1")
        assert voice_reports.clarify_target(1, event_id, "v0", name, context, database.clock.now)
        runtime.step(api)
        assert snapshot(database, second)["voice"]["phase"] == "notice_sent"
        api.kick.assert_not_called()
    finally:
        runtime.close()


@pytest.mark.parametrize("message", ["notice", "question", "receipt"])
def test_claim_during_voice_delivery(pilot, message):
    scenario, advance_time = pilot
    database, _, context = scenario
    api = transport()
    incident_id = report(scenario, reporter_id="member")["id"]
    with database() as sess:
        case_id = sess.scalar(
            select(AdminIncidentEvent.id).where(
                AdminIncidentEvent.incident_id == incident_id,
                AdminIncidentEvent.event_type == "report_admin",
            )
        )
        unrelated = AdminIncident(server_number=1, reason="Independent report")
        sess.add(unrelated)
        sess.flush()
        other_id = unrelated.id

    def send():
        if message == "receipt":
            voice_reports.flush_messages(api, 1)
        else:
            voice_reports.advance(api, 1, case_id, context)

    if message != "notice":
        voice_reports.advance(api, 1, case_id, context)
    if message == "question":
        advance_time(60)
    api.message_player.reset_mock()
    entered, release = Event(), Event()

    def wait_for_server(*args, **kwargs):
        entered.set()
        if not release.wait(20):
            raise TimeoutError("test transport was never released")
        return True

    api.message_player.side_effect = wait_for_server
    with ThreadPoolExecutor(max_workers=2) as pool:
        delivery = pool.submit(send)
        try:
            assert entered.wait(10)
            claim = pool.submit(
                admin_incidents.mutate_incident, other_id, actor="admin",
                expected_revision=1, operation="claim",
            )
            assert claim.result(timeout=5)["assigned_to"] == "admin"
            pool.submit(send).result(timeout=5)
            if message != "receipt":
                with database() as sess:
                    revision = sess.get(AdminIncident, incident_id).revision
                takeover = pool.submit(
                    admin_incidents.mutate_incident, incident_id, actor="admin",
                    expected_revision=revision, operation="claim", payload={"mode": "manual"},
                )
                assert takeover.result(timeout=5)["assigned_to"] == "admin"
        finally:
            release.set()
        delivery.result(timeout=5)
    api.message_player.assert_called_once()
    api.kick.assert_not_called()
    if message == "receipt":
        with database() as sess:
            receipt = sess.scalar(select(AdminIncidentEvent).where(
                AdminIncidentEvent.incident_id == incident_id,
                AdminIncidentEvent.event_type == "voice_game_message",
            ))
            assert receipt.payload["status"] == "sent"
    else:
        assert snapshot(database, incident_id)["status"] == "manual"


@pytest.mark.parametrize("outcome", ["confirmed", "timeout", "recovered"])
def test_claim_while_voice_kick_awaits_server(pilot, outcome):
    scenario, advance = pilot
    database, _, context = scenario
    api = transport()
    incident_id = report(scenario, reporter_id="member")["id"]
    service.tick(api, 1)
    advance(60)
    service.tick(api, 1)
    assert voice_reports.answer(1, incident_id, "member", False, context)
    with database() as sess:
        other = AdminIncident(server_number=1, reason="Independent report")
        sess.add(other)
        sess.flush()
        other_id = other.id

    entered, release = Event(), Event()

    def wait_for_server(*args, **kwargs):
        entered.set()
        if not release.wait(30) or outcome == "timeout":
            raise TimeoutError("no acknowledgement from game server")
        return True

    api.kick.side_effect = wait_for_server
    with ThreadPoolExecutor(max_workers=2) as pool:
        delivery = pool.submit(service.tick, api, 1)
        try:
            assert entered.wait(10)
            claim = pool.submit(
                admin_incidents.mutate_incident, other_id, actor="admin",
                expected_revision=1, operation="claim",
            )
            assert claim.result(timeout=5)["assigned_to"] == "admin"
            with database() as sess:
                revision = sess.get(AdminIncident, incident_id).revision
            takeover = pool.submit(
                admin_incidents.mutate_incident, incident_id, actor="admin",
                expected_revision=revision, operation="claim",
            )
            with pytest.raises(admin_incidents.IncidentConflict, match="kick in progress"):
                takeover.result(timeout=5)
            with pytest.raises(admin_incidents.IncidentConflict, match="in-progress report kick"):
                pool.submit(service.configure, 1, service.Config(enabled=False)).result(timeout=5)
            pool.submit(service.tick, api, 1).result(timeout=5)
            if outcome == "recovered":
                pool.submit(service.recover, 1).result(timeout=5)
                assert snapshot(database, incident_id)["status"] == "unknown"
        finally:
            release.set()
        delivery.result(timeout=5)

    assert snapshot(database, incident_id)["status"] == (
        "kicked" if outcome == "confirmed" else "unknown"
    )
    service.recover(1)
    service.tick(api, 1)
    api.kick.assert_called_once()


@pytest.mark.parametrize("outcome", ["restart", "timeout"])
def test_uncertain_receipt_is_never_replayed(pilot, outcome):
    scenario, _ = pilot
    database, _, _ = scenario
    api = transport()
    incident_id = report(scenario, reporter_id="member")["id"]
    service.tick(api, 1)
    with database() as sess:
        receipt_id = sess.scalar(select(AdminIncidentEvent.id).where(
            AdminIncidentEvent.event_type == "voice_game_message",
            AdminIncidentEvent.incident_id == incident_id,
        ))

    if outcome == "restart":
        entered, release = Event(), Event()

        def late_confirmation(*args, **kwargs):
            entered.set()
            return release.wait(20)

        api.message_player.side_effect = late_confirmation
        with ThreadPoolExecutor(max_workers=2) as pool:
            delivery = pool.submit(voice_reports.flush_messages, api, 1)
            try:
                assert entered.wait(10)
                pool.submit(service.recover, 1).result(timeout=5)
            finally:
                release.set()
            delivery.result(timeout=5)
    else:
        api.message_player.side_effect = TimeoutError("no game-server acknowledgement")
        voice_reports.flush_messages(api, 1)
    original_receipt = api.message_player.call_args
    with database() as sess:
        assert sess.get(AdminIncidentEvent, receipt_id).payload["status"] == "unknown"
    api.message_player.reset_mock()
    api.message_player.side_effect = None
    voice_reports.flush_messages(api, 1)
    # Recovery may queue a separate manual-review update for the reporter.
    assert original_receipt not in api.message_player.call_args_list
    with database() as sess:
        assert sess.get(AdminIncidentEvent, receipt_id).payload["status"] == "unknown"


@pytest.mark.parametrize("invalid", ["expired", "disconnected"])
def test_stale_receipt_expires_without_sending(pilot, invalid):
    scenario, advance_time = pilot
    database, _, _ = scenario
    api = transport()
    incident_id = report(scenario, reporter_id="member")["id"]
    service.tick(api, 1)
    with database() as sess:
        receipt = sess.scalar(select(AdminIncidentEvent).where(
            AdminIncidentEvent.incident_id == incident_id,
            AdminIncidentEvent.event_type == "voice_game_message",
        ))
        receipt_id = receipt.id
        if invalid == "disconnected":
            sess.get(PlayerSession, receipt.payload["session"]).end_event_us = int(
                database.clock.now * 1_000_000
            )
    if invalid == "expired":
        advance_time(120)
    api.message_player.reset_mock()
    voice_reports.flush_messages(api, 1)
    api.message_player.assert_not_called()
    with database() as sess:
        assert sess.get(AdminIncidentEvent, receipt_id).payload["status"] == "expired"
