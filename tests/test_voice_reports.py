"""New reports, actual state transitions, isolated SQLite and simulated RCON."""

import pytest
from sqlalchemy import select

from tests.test_report_admin import db, setup, report, service, transport

from rcon import voice_language, voice_reports
from rcon.models import AdminIncidentEvent
from rcon.voice_player_store import VoicePlayerDelivery


@pytest.fixture
def pilot(setup, monkeypatch):
    database, players, ctx = setup
    for player in players:
        player.setdefault("platform", "EPlatformFamily::Steam")
    monkeypatch.setenv("FRONTLINE_VOICE_REPORT_SERVERS", "1")
    monkeypatch.setenv("FRONTLINE_VOICE_LIVE_KICK_SERVERS", "1")
    with database() as sess:
        for model in (
            voice_language.VoiceLanguagePreference,
            voice_language.VoiceVerifiedIdentity,
            voice_language.VoiceTranslationCache,
            VoicePlayerDelivery,
        ):
            model.__table__.create(sess.bind)

    def advance(seconds):
        database.clock.now += seconds
        ctx["captured_at"] = database.clock.now

    return setup, advance


def snapshot(database, iid):
    with database() as sess:
        return sess.scalar(
            select(AdminIncidentEvent).where(
                AdminIncidentEvent.incident_id == iid,
                AdminIncidentEvent.event_type == "report_admin",
            )
        ).payload


@pytest.mark.parametrize("working", [True, False])
def test_first_report_needs_later_same_channel_confirmation(pilot, working):
    setup, advance = pilot
    database, _, ctx = setup
    api = transport()
    iid = report(setup, reporter_id="member")["id"]
    assert snapshot(database, iid)["voice"]["phase"] == "notice_pending"
    service.tick(api, 1)
    api.kick.assert_not_called()
    assert snapshot(database, iid)["voice"]["phase"] == "notice_sent"
    assert api.message_player.call_args.args[0] == "target"
    assert not voice_reports.answer(1, iid, "member", False, ctx)
    advance(59)
    service.tick(api, 1)
    assert api.message_player.call_args.args[0] == "member"
    assert snapshot(database, iid)["voice"]["phase"] == "notice_sent"
    advance(1)
    service.tick(api, 1)
    assert snapshot(database, iid)["voice"]["phase"] == "awaiting_answer"
    assert not voice_reports.answer(1, iid, "v2", False, ctx)
    assert voice_reports.answer(1, iid, "member", working, ctx)
    assert not voice_reports.answer(1, iid, "member", False, ctx)
    service.tick(api, 1)
    assert snapshot(database, iid)["voice"]["phase"] == (
        "resolved" if working else "kicked"
    )
    assert api.kick.call_count == (0 if working else 1)
    service.tick(api, 1)
    assert api.kick.call_count == (0 if working else 1)


def test_opponent_report_not_a_witness(pilot):
    setup, advance = pilot
    database, players, ctx = setup
    next(p for p in players if p["player_id"] == "v0")["team"] = "axis"
    api = transport()
    iid = report(setup, "!admin BattlefieldHero no comms", reporter_id="v0")["id"]
    service.tick(api, 1)
    v = snapshot(database, iid)["voice"]
    assert v["external"] and v["witness_id"] == "member"
    advance(60)
    service.tick(api, 1)
    assert not voice_reports.answer(1, iid, "v0", False, ctx)
    assert voice_reports.answer(1, iid, "member", True, ctx)
    api.kick.assert_not_called()


@pytest.mark.parametrize(
    "failure",
    [
        "duplicate",
        "notice_failed",
        "expired",
        "rejoin",
        "role_change",
        "takeover",
        "restart",
    ],
)
def test_no_kick_on_failed_or_interrupted_cases(pilot, failure):
    setup, advance = pilot
    database, players, ctx = setup
    api = transport()
    if failure == "notice_failed":
        api.message_player.return_value = False
    iid = report(setup, reporter_id="member")["id"]
    service.tick(api, 1)
    if failure == "duplicate":
        other = report(setup, reporter_id="v0")["id"]
        assert snapshot(database, other)["voice"]["phase"] == "duplicate"
    if failure == "notice_failed":
        assert snapshot(database, iid)["voice"]["message_key"] == "notice_failed"
    if failure == "role_change":
        players[0]["role"] = "Rifleman"
    if failure == "restart":
        service.recover(1)
    if failure == "takeover":
        from rcon.models import AdminIncident

        with database() as s:
            service.cancel_incident(s, s.get(AdminIncident, iid), "admin")
    if failure == "rejoin":
        from rcon.models import PlayerSession

        with database() as s:
            s.get(PlayerSession, snapshot(database, iid)["session"]).end_event_us = int(
                database.clock.now * 1_000_000
            )
    advance(60)
    service.tick(api, 1)
    advance(120)
    service.tick(api, 1)
    assert not voice_reports.answer(1, iid, "member", False, ctx)
    assert snapshot(database, iid)["status"] == "manual"
    api.kick.assert_not_called()


def test_discord_unlinked_polish_report_and_french_target_preference(pilot):
    from tests.test_report_reason import decision, complete
    from rcon import admin_incidents

    setup, advance = pilot
    database, players, ctx = setup
    api = transport()
    with database() as s:
        voice_language.set_language(s, "fr", game_id="target")
    iid = admin_incidents.create_incident(
        server_number=1,
        source="manual",
        reason="Nie odpowiada na kanale głosowym drużyny",
        raw_message="!admin BattlefieldHero Nie odpowiada na kanale głosowym drużyny",
        actor="discord:voice-player",
        reporter_context={"voice_discord_id": "450", "voice_locale": "pl"},
        target_id="target",
        target_name="BattlefieldHero",
        leadership_context={**ctx, "voice_discord_intake": True},
    )[0]["id"]
    assert snapshot(database, iid)["status"] == "classifying"
    complete(setup, iid, decision(excerpt="Nie odpowiada na kanale głosowym drużyny"))
    service.tick(api, 1)
    assert snapshot(database, iid)["voice"]["phase"] == "notice_pending"
    service.tick(api, 1)
    voice = snapshot(database, iid)["voice"]
    assert voice["external"] and voice["reporter_language"] == "pl"
    assert voice["witness_id"] == "member"
    assert api.message_player.call_count == 1
    with database() as s:
        assert api.message_player.call_args.args[1] == voice_language.render(
            s, "notice_squad", "fr"
        )
        delivery = s.scalar(
            select(VoicePlayerDelivery).where(VoicePlayerDelivery.incident_id == iid)
        )
        assert delivery.discord_id == "450" and delivery.payload["locale"] == "pl"
    advance(60)
    service.tick(api, 1)
    assert voice_reports.answer(1, iid, "member", True, ctx)
    api.kick.assert_not_called()


def test_live_role_guard_after_explicit_answer(pilot):
    setup, advance = pilot
    database, players, ctx = setup
    api = transport()
    iid = report(setup, reporter_id="member")["id"]
    service.tick(api, 1)
    advance(60)
    service.tick(api, 1)
    assert voice_reports.answer(1, iid, "member", False, ctx)
    players[0]["unit_name"] = "Fox"
    service.tick(api, 1)
    assert snapshot(database, iid)["status"] == "manual"
    api.kick.assert_not_called()


def test_dry_run_and_unconfirmed_kick_are_never_replayed(pilot):
    from rcon.user_config.report_admin import ReportAdminUserConfig

    setup, advance = pilot
    database, _, ctx = setup
    api = transport()
    service.configure(1, ReportAdminUserConfig(enabled=True, mode="dry_run"))
    iid = report(setup, reporter_id="member")["id"]
    service.tick(api, 1)
    advance(60)
    service.tick(api, 1)
    assert voice_reports.answer(1, iid, "member", False, ctx)
    service.tick(api, 1)
    assert snapshot(database, iid)["status"] == "dry_run"
    api.kick.assert_not_called()


def test_pc_target_clarification_is_bound_to_reporter_and_incident(pilot):
    setup, _ = pilot
    database, _, ctx = setup
    api = transport()
    iid = report(setup, "!admin MissingPerson no comms", reporter_id="member")["id"]
    assert snapshot(database, iid)["voice"]["phase"] == "clarify"
    with database() as s:
        eid = s.scalar(
            select(AdminIncidentEvent.id).where(
                AdminIncidentEvent.event_type == "report_admin",
                AdminIncidentEvent.incident_id == iid,
            )
        )
    command = {
        "sub_content": f"!voice {eid} target BattlefieldHero",
        "timestamp_ms": int(database.clock.now * 1000),
    }
    voice_reports.handle_chat(api, dict(command, player_id_1="v0"), 1)
    assert snapshot(database, iid)["voice"]["phase"] == "clarify"
    voice_reports.handle_chat(api, dict(command, player_id_1="member"), 1)
    assert snapshot(database, iid)["voice"]["phase"] == "notice_pending"
    service.tick(api, 1)
    assert snapshot(database, iid)["voice"]["phase"] == "notice_sent"
    api.kick.assert_not_called()


def test_confirmed_voice_kick_timeout_does_not_replay(pilot):
    setup, advance = pilot
    database, _, ctx = setup
    api = transport()
    api.kick.side_effect = TimeoutError()
    iid = report(setup, reporter_id="member")["id"]
    service.tick(api, 1)
    advance(60)
    service.tick(api, 1)
    assert voice_reports.answer(1, iid, "member", False, ctx)
    service.tick(api, 1)
    service.recover(1)
    service.tick(api, 1)
    assert snapshot(database, iid)["voice"]["message_key"] == "unconfirmed"
    api.kick.assert_called_once()


@pytest.mark.parametrize("initially_live", [True, False])
def test_active_legacy_config_cannot_bypass_pilot_dry_run(
    pilot, monkeypatch, initially_live
):
    setup, advance = pilot
    database, _, ctx = setup
    api = transport()
    if not initially_live:
        monkeypatch.delenv("FRONTLINE_VOICE_LIVE_KICK_SERVERS")
    iid = report(setup, reporter_id="member")["id"]
    service.tick(api, 1)
    advance(60)
    service.tick(api, 1)
    assert voice_reports.answer(1, iid, "member", False, ctx)
    # Disabling active immediately blocks the kick, and starting an active trial
    # cannot upgrade a case that was accepted in simulation mode.
    monkeypatch.setenv(
        "FRONTLINE_VOICE_LIVE_KICK_SERVERS", "" if initially_live else "1"
    )
    service.tick(api, 1)
    assert snapshot(database, iid)["voice"]["phase"] == "dry_run"
    assert snapshot(database, iid)["voice"]["message_key"] == "dry_run"
    api.kick.assert_not_called()


@pytest.mark.parametrize(
    ("command", "works"),
    [
        ("!voice ja", True),
        ("!voice YES", True),
        ("!voice non", False),
        ("!voice nie", False),
        ("!voice nee", False),
    ],
)
def test_private_voice_short_answers_do_not_capture_leadership_votes(
    pilot, command, works
):
    setup, advance = pilot
    database, _, ctx = setup
    iid = report(setup, reporter_id="member")["id"]
    api = transport()
    service.tick(api, 1)
    advance(60)
    service.tick(api, 1)
    message = api.message_player.call_args.args[1]
    assert "!voice" not in message and "Discord" not in message

    def reply(word, pid="member", age=0):
        return voice_reports.handle_chat(
            api,
            {
                "sub_content": word,
                "player_id_1": pid,
                "timestamp_ms": int((database.clock.now - age) * 1000),
            },
            1,
        )

    assert not reply("!yes") and not reply("!no")
    assert reply(command, pid="target")
    assert reply(command, age=5)
    assert snapshot(database, iid)["voice"]["phase"] == "awaiting_answer"
    assert reply(command)
    assert snapshot(database, iid)["voice"]["phase"] == (
        "resolved" if works else "kick_ready"
    )


def test_two_pc_questions_do_not_apply_an_old_answer_to_new_case(pilot):
    setup, advance = pilot
    database, players, ctx = setup
    next(p for p in players if p["player_id"] == "v2")["name"] = "MicrophoneJohn"
    first = report(setup, "!admin BattlefieldHero no comms", reporter_id="v0")["id"]
    api = transport()
    service.tick(api, 1)
    advance(1)
    ctx["event_time"] = database.clock.now
    second = report(setup, "!admin MicrophoneJohn no comms", reporter_id="v0")["id"]
    service.tick(api, 1)
    advance(59)
    service.tick(api, 1)
    advance(1)
    service.tick(api, 1)
    assert snapshot(database, first)["voice"]["phase"] == "awaiting_answer"
    assert snapshot(database, second)["voice"]["phase"] == "notice_sent"
    advance(119)
    service.tick(api, 1)
    advance(1)
    service.tick(api, 1)
    assert snapshot(database, first)["voice"]["phase"] == "manual"
    assert snapshot(database, second)["voice"]["phase"] == "manual"
    voice_reports.handle_chat(
        api,
        {
            "player_id_1": "v0",
            "sub_content": "!voice nein",
            "timestamp_ms": int(database.clock.now * 1000),
        },
        1,
    )
    api.kick.assert_not_called()


@pytest.mark.parametrize("linked", [True, False])
def test_external_console_witness_needs_existing_link_and_no_pc_instructions(
    pilot, linked
):
    setup, advance = pilot
    database, players, _ = setup
    next(p for p in players if p["player_id"] == "v0")["team"] = "axis"
    for p in players:
        p["platform"] = "EPlatformFamily::PS5"
    if linked:
        with database() as sess:
            voice_language.link_verified(sess, game_id="member", discord_id="8790")
    iid = report(setup, "!admin BattlefieldHero no comms", reporter_id="v0")["id"]
    api = transport()
    service.tick(api, 1)
    advance(60)
    service.tick(api, 1)
    v = snapshot(database, iid)["voice"]
    if linked:
        assert v["witness_route"] == "discord" and v["phase"] == "awaiting_answer"
        with database() as sess:
            delivery = sess.scalar(
                select(VoicePlayerDelivery).where(
                    VoicePlayerDelivery.incident_id == iid,
                    VoicePlayerDelivery.kind == "question",
                )
            )
            assert delivery.discord_id == "8790" and delivery.payload["send_dm"] is True
        assert not any(c.args[0] == "member" for c in api.message_player.call_args_list)
    else:
        assert v["witness_id"] is None and v["phase"] == "manual"
    api.kick.assert_not_called()


@pytest.mark.parametrize(
    ("locale", "positive", "negative"),
    [
        ("de", "Ja", "Nein"),
        ("en", "Yes", "No"),
        ("fr", "Oui", "Non"),
        ("pl", "Tak", "Nie"),
        ("nl", "Ja", "Nee"),
    ],
)
@pytest.mark.parametrize("working", [True, False])
def test_real_chat_hook_uses_only_addressed_single_local_word(
    pilot, monkeypatch, locale, positive, negative, working
):
    from unittest.mock import Mock
    from rcon import discord_chat, incident_settings, moderation_candidates

    setup, advance = pilot
    database, _, _ = setup
    handler = Mock()
    monkeypatch.setattr(discord_chat, "get_handler", lambda: handler)
    monkeypatch.setattr(incident_settings, "incident_capture_enabled", lambda: False)
    monkeypatch.setattr(moderation_candidates, "enqueue_candidate", Mock())
    api = transport()
    with database() as sess:
        voice_language.set_language(sess, locale, game_id="member")
    iid = report(setup, "!admin BattlefieldHero no VOIP", reporter_id="member")["id"]
    service.tick(api, 1)

    def chat(word, pid="member", age=0):
        before = handler.send_chat_message.call_count
        discord_chat.handle_on_chat(
            api,
            {
                "action": "CHAT[Team][Allies]",
                "player_id_1": pid,
                "sub_content": word,
                "timestamp_ms": int((database.clock.now - age) * 1000),
            },
        )
        return handler.send_chat_message.call_count == before

    assert not chat(positive)
    advance(60)
    service.tick(api, 1)
    v = snapshot(database, iid)["voice"]
    assert v["reply_language"] == locale
    assert not chat(positive, pid="v0")
    assert not chat(positive, age=1)
    assert not chat("!yes") and not chat("!no")
    assert not chat(positive + " today")
    assert not chat("Nie" if locale != "pl" else "No")
    assert chat((positive if working else negative).upper())
    assert not chat(positive)
    assert snapshot(database, iid)["voice"]["phase"] == (
        "resolved" if working else "kick_ready"
    )


def test_delayed_old_log_never_answers_next_serialised_question(pilot):
    setup, advance = pilot
    database, players, ctx = setup
    next(p for p in players if p["player_id"] == "v2")["name"] = "MicrophoneJohn"
    first = report(setup, "!admin BattlefieldHero no comms", reporter_id="v0")["id"]
    api = transport()
    service.tick(api, 1)
    advance(5)
    ctx["event_time"] = database.clock.now
    second = report(setup, "!admin MicrophoneJohn no comms", reporter_id="v0")["id"]
    service.tick(api, 1)
    advance(55)
    service.tick(api, 1)
    assert voice_reports.answer(1, first, "v0", True, ctx)
    old_stamp = database.clock.now
    advance(5)
    service.tick(api, 1)
    assert snapshot(database, second)["voice"]["phase"] == "notice_sent"
    advance(116)
    service.tick(api, 1)
    assert snapshot(database, second)["voice"]["phase"] == "awaiting_answer"
    assert not voice_reports.handle_chat(
        api,
        {"player_id_1": "v0", "sub_content": "Nein", "timestamp_ms": old_stamp * 1000},
        1,
    )
    assert snapshot(database, second)["voice"]["phase"] == "awaiting_answer"
    assert voice_reports.handle_chat(
        api,
        {
            "player_id_1": "v0",
            "sub_content": "Ja",
            "timestamp_ms": database.clock.now * 1000,
        },
        1,
    )
    assert snapshot(database, second)["voice"]["phase"] == "resolved"


def test_linked_discord_reporter_only_gets_buttons_as_the_question(pilot):
    from tests.test_report_reason import decision, complete
    from rcon import admin_incidents

    setup, advance = pilot
    database, players, ctx = setup
    next(p for p in players if p["player_id"] == "member")[
        "platform"
    ] = "EPlatformFamily::PS5"
    with database() as sess:
        voice_language.link_verified(sess, game_id="member", discord_id="827")
    iid = admin_incidents.create_incident(
        server_number=1,
        source="manual",
        reason="no comms",
        actor="discord:voice-player",
        reporter_context={"voice_discord_id": "827", "voice_locale": "pl"},
        raw_message="!admin BattlefieldHero no comms",
        reporter_id="member",
        target_id="target",
        target_name="BattlefieldHero",
        leadership_context={**ctx, "voice_discord_intake": True},
    )[0]["id"]
    complete(setup, iid, decision(excerpt="no comms"))
    api = transport()
    service.tick(api, 1)
    service.tick(api, 1)
    advance(60)
    service.tick(api, 1)
    assert snapshot(database, iid)["voice"]["phase"] == "awaiting_answer"
    assert (
        api.message_player.call_count == 1
        and api.message_player.call_args.args[0] == "target"
    )
    with database() as sess:
        delivery = sess.scalar(
            select(VoicePlayerDelivery).where(
                VoicePlayerDelivery.incident_id == iid,
                VoicePlayerDelivery.kind == "question",
            )
        )
        assert delivery.discord_id == "827" and delivery.payload["send_dm"] is False
        voice_reports.private_question_unavailable(sess, delivery)
        voice_reports.private_question_unavailable(sess, delivery)
    service.tick(api, 1)
    service.tick(api, 1)
    assert api.message_player.call_count == 2
    assert (
        api.message_player.call_args.args[0] == "member"
        and "!voice" not in api.message_player.call_args.args[1]
    )
