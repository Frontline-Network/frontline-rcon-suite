"""Runtime/chat integration with synthetic data, no external services."""

from types import SimpleNamespace
from unittest.mock import Mock
import pytest
from sqlalchemy import select
from tests.test_leadership_vote import (
    db,
    NOW,
    player,
    roster,
    squads,
    activate,
    vote,
    report,
    context,
    observe_for,
    ready_to_kick,
    transport,
)
from rcon import (
    admin_incidents as incidents,
    discord_chat,
    incident_settings,
    incident_notifications,
)
from rcon.leadership_vote import domain, hooks, service, storage
from rcon.models import AdminIncident, LeadershipMessage
from rcon.user_config.leadership_vote import LeadershipVoteUserConfig as Config


@pytest.mark.parametrize("unavailable", [False, True])
def test_report_survives_discord_outage_and_disabled_optional_context(
    db, monkeypatch, unavailable
):
    players = roster()
    observe_for(db, players)
    monkeypatch.setattr(incident_settings, "incident_capture_enabled", lambda: True)
    monkeypatch.setattr(incident_settings, "incident_context_mode", lambda: "disabled")
    monkeypatch.setattr(incident_settings, "incident_triggers", lambda: ("!admin",))
    monkeypatch.setattr(
        incident_notifications, "received_reporter_template", lambda: ""
    )
    handler = Mock()
    handler.send_chat_message.side_effect = OSError("Discord unavailable")
    monkeypatch.setattr(discord_chat, "get_handler", lambda: handler)
    api = Mock()
    api.get_team_view.return_value = {}
    monkeypatch.setattr(incidents, "flatten_team_view", lambda _: squads(players))
    if unavailable:
        api.get_detailed_players.side_effect = OSError("Game unavailable")
        monkeypatch.setattr(
            service, "read_context", Mock(side_effect=OSError("No context"))
        )
    else:
        monkeypatch.setattr(service, "read_context", lambda _: context(players))
    log = dict(
        action="CHAT[Allies][Team]",
        player_id_1="v0",
        player_name_1="Person-v0",
        sub_content="!admin able redet nicht",
        timestamp_ms=NOW * 1000,
    )
    discord_chat.handle_on_chat(api, log)
    with db() as sess:
        incident = sess.scalar(select(AdminIncident))
        assert incident is not None and incident.status == "new"
        assert bool(incident.leadership_vote_id) is not unavailable
    api.message_player.assert_not_called()
    api.get_player_info.assert_not_called()


def test_context_uses_bulk_calls_for_100_players_and_rejects_staleness(monkeypatch):
    players = [player(str(i), role="Rifleman") for i in range(100)]
    api = Mock()
    api.get_gamestate.return_value = {"current_map": {"id": "test-map"}}
    api.get_players.return_value = players
    api.get_detailed_players.return_value = {
        "players": {p["player_id"]: p for p in players},
        "fail_count": 0,
    }
    api.get_raw_player_snapshot.return_value = {"captured_at": NOW}
    monkeypatch.setattr(service.time, "time", lambda: NOW)
    monkeypatch.setattr(
        service,
        "MapsHistory",
        lambda: SimpleNamespace(
            get_current_map=lambda: {"name": "test-map", "start": NOW - 600}
        ),
    )
    assert len(service.read_context(api)["players"]) == 100
    api.get_detailed_players.assert_called_once_with(compact=True)
    api.get_player_info.assert_not_called()
    api.get_raw_player_snapshot.return_value = {"captured_at": NOW - 11}
    with pytest.raises(ValueError, match="Stale"):
        service.read_context(api)


def test_reconnect_never_inherits_old_vote(db):
    vid, _ = activate(db)
    hooks.reconnected(
        None, {"player_id_1": "target", "timestamp_ms": (NOW - 100) * 1000}
    )
    assert vote(db, vid)["status"] == "active"
    hooks.reconnected(
        None, {"player_id_1": "target", "timestamp_ms": db.clock.now * 1000}
    )
    assert vote(db, vid)["status"] == "cancelled"


def test_disabled_idle_runtime_does_not_connect_to_game(db):
    storage.configure(1, Config(), "admin")
    api = Mock()
    service.tick(api, 1)
    assert api.mock_calls == []


def test_enabled_runtime_observes_even_without_votes(db, monkeypatch):
    api = transport()
    read = Mock(return_value=context(roster()))
    monkeypatch.setattr(service, "read_context", read)
    service.tick(api, 1)
    read.assert_called_once()
    with db() as sess:
        assert len(storage.presence(sess, 1)) == 7


@pytest.mark.parametrize("failure", ["disconnect", "context"])
def test_last_validation_failure_prevents_kick(db, monkeypatch, failure):
    vid, players, job = ready_to_kick(db)

    def read(api):
        if failure == "context":
            raise OSError("offline")
        storage.end_for_event(1, db.clock.now, "target")
        return context(players)

    monkeypatch.setattr(service, "read_context", read)
    api = transport()
    service.execute(api, 1, job)
    api.kick.assert_not_called()
    assert vote(db, vid)["status"] == "cancelled"


@pytest.mark.parametrize(
    "text,hidden",
    [
        ("!yes", True),
        (" !NO ", True),
        ("!admin Able redet nicht", True),
        ("!admin commander is not talking", True),
        ("!admin cheater", False),
        ("hello team", False),
        ("!yes please", False),
    ],
)
def test_public_webhook_privacy_classification(db, text, hidden):
    assert bool(domain.suppress_public_chat({"sub_content": text})) is hidden


def test_private_admin_report_kept_but_general_chat_webhook_suppressed(db, monkeypatch):
    handler = object.__new__(discord_chat.DiscordWebhookHandler)
    handler.chat_webhooks = [Mock()]
    admin = Mock()
    admin.json = {
        "url": "https://example.invalid",
        "webhook_id": "123",
        "rate_limit_retry": False,
    }
    handler.ping_trigger_webhooks = [admin]
    handler.create_admin_ping_message = lambda _: ("<@1>", Mock(), True)
    handler.create_chat_message = lambda _: Mock()
    enqueued = Mock()
    monkeypatch.setattr(discord_chat, "enqueue_message", enqueued)
    handler.send_chat_message({"sub_content": "!admin commander redet nicht"})
    assert enqueued.call_count == 1
    assert enqueued.call_args.kwargs["message"].message_type.value == "admin_ping"


@pytest.mark.parametrize(
    "channel", ["CHAT[Allies][Global]", "CHAT", "CHAT[Axis][Team]"]
)
def test_invalid_channel_answers_never_count(db, monkeypatch, channel):
    vid, players = activate(db)
    monkeypatch.setattr(service, "read_context", lambda _: context(players))
    assert service.handle_answer(
        transport(),
        dict(
            action=channel,
            player_id_1="v0",
            sub_content="!yes",
            timestamp_ms=db.clock.now * 1000,
        ),
    )
    assert vote(db, vid)["yes"] == 0


def test_direct_admin_action_cancels_or_waits_for_started_send(db):
    vid, _ = activate(db)
    storage.before_manual_action("target", "admin")
    assert vote(db, vid)["status"] == "cancelled"


def test_duplicate_report_log_has_only_one_offer(db):
    observe_for(db, roster())
    a = report(dedupe_seconds=60)
    b = report(dedupe_seconds=60)
    assert a["id"] == b["id"]
    with db() as sess:
        assert len(list(sess.scalars(select(LeadershipMessage)))) == 1


def test_leadership_failure_does_not_stop_other_routines(monkeypatch):
    from rcon import routines
    runtime = Mock()
    runtime.step.side_effect = OSError("isolated vote failure")
    runtime.close.side_effect = OSError("isolated cleanup failure")
    monkeypatch.setattr(service, "Runtime", lambda: runtime)
    api = Mock()
    api.performance_stats_interval.return_value = 0
    monkeypatch.setattr(routines, "get_rcon", lambda: api)
    regular = Mock()
    monkeypatch.setattr(routines, "toggle_votekick", regular)
    map_votes = Mock()
    monkeypatch.setattr(routines, "VoteMap", lambda: map_votes)
    stop = Mock()
    stop.is_set.side_effect = [False, True]
    routines.run(stop)
    regular.assert_called_once_with(api)
    map_votes.send_reminder.assert_called_once()
    runtime.close.assert_called_once()
