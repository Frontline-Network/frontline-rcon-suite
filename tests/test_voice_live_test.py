"""A scoped volunteer test must never become a server-wide exception."""

from copy import deepcopy

import pytest
from sqlalchemy import select

from tests.test_voice_reports import db, setup, pilot, snapshot
from tests.test_report_admin import service, report, transport
from rcon import voice_live_test as grant, voice_reports
from rcon.models import AdminIncidentEvent, PlayerID, PlayerSession

TARGET = "000000000000000000000000000000e1"
REPORTER = "000000000000000000000000000000e2"


@pytest.fixture
def volunteers(pilot, monkeypatch):
    fixture, advance = pilot
    database, players, ctx = fixture
    monkeypatch.delenv("FRONTLINE_VOICE_LIVE_KICK_SERVERS")
    with database() as sess:
        for old, new in (("target", TARGET), ("member", REPORTER)):
            sess.scalar(select(PlayerID).where(PlayerID.player_id == old)).player_id = (
                new
            )
            next(p for p in players if p["player_id"] == old)["player_id"] = new
    return fixture, advance


def start(fixture, advance):
    database, _, ctx = fixture
    api = transport()
    window = grant.arm(1, TARGET, REPORTER, ctx)
    iid = report(fixture, reporter_id=REPORTER)["id"]
    assert snapshot(database, iid)["voice"]["live_test"] == window
    service.tick(api, 1)
    api.kick.assert_not_called()
    advance(60)
    service.tick(api, 1)
    return window, iid, api


def test_one_confirmed_kick_and_other_reporters_remain_in_simulation(volunteers):
    fixture, advance = volunteers
    database, _, ctx = fixture
    window, iid, api = start(fixture, advance)
    assert grant.inspect_window(1)["state"] == "bound"
    assert not voice_reports.answer(1, iid, "v0", False, ctx)
    assert voice_reports.answer(1, iid, REPORTER, False, ctx)
    service.tick(api, 1)
    api.kick.assert_called_once()
    assert api.kick.call_args.args[0] == TARGET
    assert grant.inspect_window(1)["state"] == "consumed"
    assert snapshot(database, iid)["voice"]["phase"] == "kicked"
    service.tick(api, 1)
    api.kick.assert_called_once()
    with pytest.raises(ValueError, match="unexpired"):
        grant.arm(1, TARGET, REPORTER, ctx)
    # A later case from the same pair cannot reuse the consumed volunteer window.
    advance(310)
    ctx["event_time"] = database.clock.now
    other = report(fixture, reporter_id=REPORTER)["id"]
    assert snapshot(database, other)["mode"] == "dry_run"


@pytest.mark.parametrize(
    "change",
    ["cancel", "expiry", "new_round", "reconnect", "takeover", "no_reply", "works"],
)
def test_aborted_or_changed_volunteer_case_never_kicks(volunteers, change):
    fixture, advance = volunteers
    database, players, ctx = fixture
    window, iid, api = start(fixture, advance)
    if change == "works":
        assert voice_reports.answer(1, iid, REPORTER, True, ctx)
    elif change == "no_reply":
        advance(120)
    elif change == "takeover":
        from rcon.models import AdminIncident

        with database() as sess:
            service.cancel_incident(sess, sess.get(AdminIncident, iid), "human")
    else:
        assert voice_reports.answer(1, iid, REPORTER, False, ctx)
        if change == "cancel":
            grant.cancel(1, window)
        elif change == "expiry":
            advance(601)
        elif change == "new_round":
            ctx["round_id"] = "round-2"
        elif change == "reconnect":
            with database() as sess:
                sess.get(
                    PlayerSession, snapshot(database, iid)["session"]
                ).end_event_us = int(database.clock.now * 1e6)
    service.tick(api, 1)
    api.kick.assert_not_called()
    assert snapshot(database, iid)["status"] not in {"sending", "kicked"}


def test_grant_is_consumed_before_io_and_checked_again_before_transport(
    volunteers, monkeypatch
):
    fixture, advance = volunteers
    database, _, ctx = fixture
    window, iid, api = start(fixture, advance)
    assert voice_reports.answer(1, iid, REPORTER, False, ctx)
    original = service.read_context

    def pause_after_claim(transport):
        if grant.inspect_window(1)["state"] == "consumed":
            grant.cancel(1, window)
        return original(transport)

    monkeypatch.setattr(service, "read_context", pause_after_claim)
    service.tick(api, 1)
    assert snapshot(database, iid)["status"] == "dry_run"
    api.kick.assert_not_called()


def test_preexisting_and_unrelated_cases_not_upgraded(volunteers):
    fixture, advance = volunteers
    database, players, ctx = fixture
    earlier = report(fixture, reporter_id=REPORTER)["id"]
    window = grant.arm(1, TARGET, REPORTER, ctx)
    assert snapshot(database, earlier)["mode"] == "dry_run"
    assert grant.inspect_window(1)["state"] == "armed"
    next(p for p in players if p["player_id"] == "v2")["name"] = "MicrophoneJohn"
    different_target = report(
        fixture, "!admin MicrophoneJohn no comms", reporter_id="v0"
    )["id"]
    assert snapshot(database, different_target)["mode"] == "dry_run"
    assert grant.inspect_window(1)["state"] == "armed"
    with pytest.raises(ValueError, match="different"):
        grant.arm(1, TARGET, TARGET, ctx)


def test_arm_rejects_steam_id_other_team_or_stale_roster(volunteers):
    fixture, advance = volunteers
    database, players, ctx = fixture
    with pytest.raises(ValueError, match="EOS"):
        grant.arm(1, "76561198000000000", REPORTER, ctx)
    bad = deepcopy(ctx)
    bad["captured_at"] -= 11
    with pytest.raises(ValueError, match="fresh"):
        grant.arm(1, TARGET, REPORTER, bad)
    next(p for p in players if p["player_id"] == REPORTER)["team"] = "axis"
    with pytest.raises(ValueError, match="voice channel"):
        grant.arm(1, TARGET, REPORTER, ctx)


def test_expiry_while_witness_answer_is_still_fresh(volunteers):
    fixture, advance = volunteers
    database, _, ctx = fixture
    api = transport()
    grant.arm(1, TARGET, REPORTER, ctx)
    advance(510)
    ctx["event_time"] = database.clock.now
    iid = report(fixture, reporter_id=REPORTER)["id"]
    service.tick(api, 1)
    advance(60)
    service.tick(api, 1)
    advance(31)
    assert voice_reports.answer(1, iid, REPORTER, False, ctx)
    assert snapshot(database, iid)["mode"] == "dry_run"
    service.tick(api, 1)
    assert snapshot(database, iid)["status"] == "dry_run"
    api.kick.assert_not_called()


def test_prearmed_ai_report_is_not_authorized_after_interpretation(volunteers):
    from tests.test_report_reason import decision, complete
    from rcon.user_config.report_admin import ReportAdminUserConfig

    fixture, _ = volunteers
    database, _, ctx = fixture
    service.configure(
        1, ReportAdminUserConfig(enabled=True, mode="active", reason_mode="ai")
    )
    iid = report(fixture, "!admin BattlefieldHero no comms", reporter_id=REPORTER)["id"]
    grant.arm(
        1, TARGET, REPORTER, ctx
    )  # same clock tick; SQL event boundary also matters
    complete(fixture, iid, decision(excerpt="no comms"))
    service.tick(transport(), 1)
    assert snapshot(database, iid)["mode"] == "dry_run"
    assert grant.inspect_window(1)["state"] == "armed"
