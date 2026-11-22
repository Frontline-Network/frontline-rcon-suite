"""Exercise incident claims while RCON holds a voice message in flight."""

from concurrent.futures import ThreadPoolExecutor
from threading import Event

import pytest
from sqlalchemy import select

from rcon import admin_incidents, voice_reports
from rcon.models import AdminIncident, AdminIncidentEvent
from tests.test_leadership_vote_postgres import postgres
from tests.test_report_admin import report, service, setup, transport
from tests.test_voice_reports import pilot, snapshot


@pytest.fixture
def db(postgres):
    return postgres


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

    def interrupted(*args, **kwargs):
        if outcome == "restart":
            service.recover(1)
            return True  # Late confirmation from the previous owner.
        raise TimeoutError("no game-server acknowledgement")

    api.message_player.side_effect = interrupted
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
