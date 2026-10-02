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
    cast,
    confirm,
    deliver,
    elapse,
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


@pytest.mark.parametrize(
    "text,squad,commander",
    [
        ("!admin Bravo SL kicken aufgrund fehlender komms", "Baker", False),
        ("!Admin Eays SL kicken, der redet nicht", "Easy", False),
        ("!admin SL Gorge keine Com plz ban", "George", False),
        ("!admin echosquad not communicating", "Easy", False),
        ("!admin sl B hat kein mic", "Baker", False),
        ("!admin Bitte KILO SL kicken, redet nicht", "King", False),
        ("!admin Squad Easy SL redet nicht (Person-target)", "Easy", False),
        ("!admin SL Person-target redet nicht", "Easy", False),
        ("!admin Kommander spricht nicht", "", True),
        ("!admin cmd keine com", "", True),
    ],
)
def test_real_alias_report_stays_bound_through_complete_dry_run(
    db, monkeypatch, text, squad, commander
):
    players = roster(commander=commander)
    players[0]["unit_name"] = squad
    observe_for(db, players)
    incident = report(players, text=text)
    vid = incident["leadership_vote"]["id"]
    assert incident["target_id"] == "target"
    assert incident["raw_message"] == text
    assert incident["leadership_vote"]["target_resolution"]["matches"]
    assert sum(s["is_primary"] for s in incident["subjects"]) == 1
    api = deliver(db, players)
    invitation = api.message_player.call_args.args[1]
    assert "Person-target" in invitation
    assert "!no = Vote against kicking" in invitation
    assert "DRY RUN" in invitation
    assert confirm(db, players, incident) == vid
    assert vote(db, vid)["yes"] == 0
    storage.advance(1, context(players))
    deliver(db, players, api)
    storage.advance(1, context(players))
    assert vote(db, vid)["status"] == "active"
    for i in range(4):
        assert cast(db, players, f"v{i}")
    elapse(db, players, 120)
    assert storage.advance(1, context(players)) == []
    assert vote(db, vid)["status"] == "dry_run"
    result = incidents.get_incident(incident["id"])
    assert result["status"] == "new" and result["target_id"] == "target"
    monkeypatch.setattr(service, "read_context", lambda _: context(players))
    service.execute(api, 1, vote(db, vid))
    api.kick.assert_not_called()


@pytest.mark.parametrize("commander", [False, True])
def test_report_without_any_confirmation_invites_every_eligible_leader(
    db, monkeypatch, commander
):
    storage.configure(1, Config(enabled=True, confirmation_seconds=120), "tester")
    players = roster(commander=commander)
    players += [player("opponent", squad="Other", team="axis")]
    observe_for(db, players)
    incident = report(players, "!admin commander" if commander else "!admin able")
    vid = incident["leadership_vote"]["id"]
    api = deliver(db, players)
    assert api.message_player.call_count == 12
    assert "You have 120 seconds" in api.message_player.call_args.args[1]
    assert vote(db, vid)["status"] == "inviting"
    assert vote(db, vid)["yes"] == 0
    deliver(db, players, api)
    storage.advance(1, context(players))
    deliver(db, players, api)
    storage.advance(1, context(players))

    current = vote(db, vid)
    assert current["status"] == "active"
    assert current["ends_at"] - db.clock.now == 120
    assert current["required"] == 4
    with db() as sess:
        invitations = list(
            sess.scalars(
                select(LeadershipMessage).where(
                    LeadershipMessage.vote_id == vid,
                    LeadershipMessage.purpose == "invite",
                )
            )
        )
    assert {item.player_id for item in invitations} == {f"v{i}" for i in range(6)}
    assert all(item.status == "sent" for item in invitations)
    assert all(
        "!yes = Vote to kick\n!no = Vote against kicking" in item.body
        for item in invitations
    )
    assert all("Reply in TEAM or SQUAD chat only." in item.body for item in invitations)
    assert all("Nur Team-/Squadchat" not in item.body for item in invitations)
    assert all(
        member["invited_at"] is not None for member in current["electorate"].values()
    )
    api.kick.assert_not_called()


def test_no_ballots_rejects_vote_after_full_duration_without_kicking(db):
    storage.configure(1, Config(enabled=True, confirmation_seconds=120), "tester")
    players = roster()
    observe_for(db, players)
    incident = report(players)
    vid = incident["leadership_vote"]["id"]
    api = deliver(db, players)
    assert api.message_player.call_count == 12
    storage.advance(1, context(players))
    elapse(db, players, 119)
    assert storage.advance(1, context(players)) == []
    assert vote(db, vid)["status"] == "active"
    elapse(db, players, 1)
    assert storage.advance(1, context(players)) == []
    assert vote(db, vid)["status"] == "rejected"
    assert "No majority" in vote(db, vid)["result"]
    with db() as sess:
        assert not list(
            sess.scalars(
                select(LeadershipMessage).where(
                    LeadershipMessage.vote_id == vid,
                    LeadershipMessage.purpose.in_({"target", "confirm"}),
                )
            )
        )
    api.kick.assert_not_called()


@pytest.mark.parametrize("change", ["takeover", "successor", "disable", "retarget"])
def test_new_alias_offer_keeps_admin_and_identity_guards(db, change):
    players = roster()
    observe_for(db, players)
    incident = report(players, text="!admin alpha")
    vid = confirm(db, players, incident)
    current = incidents.get_incident(incident["id"])
    if change == "takeover":
        incidents.mutate_incident(
            current["id"],
            actor="admin",
            expected_revision=current["revision"],
            operation="claim",
        )
    elif change == "retarget":
        # Even an out-of-band primary-ID change must stop this workflow.
        with db() as sess:
            sess.get(AdminIncident, current["id"]).target_id = "v1"
    elif change == "successor":
        players[0]["player_id"] = "successor"
    else:
        storage.configure(1, Config(), "admin")
    storage.observe(1, context(players))
    storage.advance(1, context(players))
    assert vote(db, vid)["status"] == "cancelled"


@pytest.mark.parametrize("gate", ["disabled", "unassigned", "no_history", "global"])
def test_ordinary_reports_not_rewritten_when_alias_offer_ineligible(db, gate):
    players = roster()
    if gate == "disabled":
        storage.configure(1, Config(), "admin")
    if gate == "unassigned":
        players[2]["role"] = "Rifleman"
        players[2]["unit_name"] = "unassigned"
    if gate != "no_history":
        observe_for(db, players)
    text = "!admin alpha"
    parsed = incidents.parse_chat_report(
        text,
        current_players=players,
        current_squads=squads(players),
        reporter_context=players[2],
        context_mode="enabled",
    )
    incident = report(players, text=text, private=gate != "global")
    assert not incident["leadership_vote"]
    assert incident["raw_message"] == text and incident["reason"] == parsed["reason"]
    assert [
        (s["display_name"], s["state"], s["match_method"]) for s in incident["subjects"]
    ] == [
        (s["display_name"], s["state"], s["match_method"]) for s in parsed["subjects"]
    ]


@pytest.mark.parametrize("unavailable", [False, True])
@pytest.mark.parametrize("reporter", ["v0", "member"])
@pytest.mark.parametrize(
    "text,commander,squad",
    [
        ("!admin able redet nicht", False, "Able"),
        ("!admin bitte mal prüfen able redet nicht", False, "Able"),
        ("!admin der commander redet nicht", True, ""),
        ("!admin able", False, "Able"),
        ("!admin bitte mal prüfen able", False, "Able"),
        ("!admin commander", True, ""),
        ("!Admin Able squad keine Komms", False, "Able"),
        ("!admin squad lead how  redet nicht", False, "How"),
    ],
)
def test_report_survives_discord_outage_and_disabled_optional_context(
    db, monkeypatch, unavailable, text, commander, squad, reporter
):
    players = roster(commander=commander)
    players[0]["unit_name"] = squad
    players[1]["unit_name"] = squad or "Able"
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
        player_id_1=reporter,
        player_name_1="Person-" + reporter,
        sub_content=text,
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
    api.game_profile.player_adapter.adapt.side_effect = lambda row: row
    monkeypatch.setattr(service, "parse_raw_player_info", lambda row, game: row)
    api.get_raw_player_snapshot.return_value = {"captured_at": NOW, "players": players}
    monkeypatch.setattr(service.time, "time", lambda: NOW)
    monkeypatch.setattr(
        service,
        "MapsHistory",
        lambda: SimpleNamespace(
            get_current_map=lambda: {"name": "test-map", "start": NOW - 600}
        ),
    )
    assert len(service.read_context(api)["players"]) == 100
    api.get_detailed_players.assert_not_called()
    api.get_players.assert_not_called()
    api.get_raw_player_snapshot.assert_called_once_with()
    api.get_player_info.assert_not_called()
    api.get_raw_player_snapshot.return_value = {"captured_at": NOW - 11}
    with pytest.raises(ValueError, match="Stale"):
        service.read_context(api)


def test_bulk_context_keeps_tenure_during_unrelated_roster_churn(db, monkeypatch):
    """Cached UI roster divergence must not reset unchanged leadership seats."""
    players = roster()
    api = Mock()
    api.get_gamestate.return_value = {"current_map": {"id": "test-map"}}
    # Reproduce production: two UI caches disagree while the bulk roster is valid.
    api.get_players.return_value = players + [player("just-joined", "Rifleman")]
    api.get_detailed_players.return_value = {"players": {}, "fail_count": 1}
    api.game_profile.player_adapter.adapt.side_effect = lambda row: row
    monkeypatch.setattr(service, "parse_raw_player_info", lambda row, game: row)
    monkeypatch.setattr(
        service,
        "MapsHistory",
        lambda: SimpleNamespace(
            get_current_map=lambda: {"name": "test-map", "start": NOW - 600}
        ),
    )
    for step in range(62):
        db.clock.now = NOW + step * 5
        visitors = [player(f"visitor-{step}", "Rifleman")]
        api.get_raw_player_snapshot.return_value = {
            "captured_at": db.clock.now,
            "players": players + visitors,
        }
        storage.observe(1, service.read_context(api))
    with db() as sess:
        observations = storage.presence(sess, 1)
        target = dict(domain.identity(players[0]), player_id="target")
        assert observations["v0"]["since"] == NOW
        assert (
            len(domain.electorate(players, target, observations, db.clock.now, 300))
            >= 3
        )
    api.get_players.assert_not_called()
    api.get_detailed_players.assert_not_called()


@pytest.mark.parametrize(
    "rows", [None, {}, [{"player_id": ""}], [player("x"), player("x")]]
)
def test_bulk_context_rejects_missing_and_duplicate_identities(monkeypatch, rows):
    api = Mock()
    api.get_gamestate.return_value = {"current_map": {"id": "test-map"}}
    api.get_raw_player_snapshot.return_value = {"captured_at": NOW, "players": rows}
    api.game_profile.player_adapter.adapt.side_effect = lambda row: row
    monkeypatch.setattr(service, "parse_raw_player_info", lambda row, game: row)
    monkeypatch.setattr(service.time, "time", lambda: NOW)
    monkeypatch.setattr(
        service,
        "MapsHistory",
        lambda: SimpleNamespace(
            get_current_map=lambda: {"name": "test-map", "start": NOW - 600}
        ),
    )
    with pytest.raises(ValueError):
        service.read_context(api)


@pytest.mark.parametrize("game,team,role", [("hll", 2, 1), ("hllv", 6, 28)])
def test_bulk_context_uses_real_game_adapter(monkeypatch, game, team, role):
    from rcon.game import get_game_profile
    from rcon.game.player_adapter import PlayerResponseAdapterError
    from rcon.types import GameEnum

    api = Mock()
    api.game_profile = get_game_profile(game)
    api.config.game = GameEnum(game)
    api.get_gamestate.return_value = {"current_map": {"id": "test-map"}}
    raw = {
        "iD": "test-account",
        "name": "Synthetic Player",
        "team": team,
        "role": role,
        "platoon": "Able",
        "level": 50,
    }
    api.get_raw_player_snapshot.return_value = {"captured_at": NOW, "players": [raw]}
    monkeypatch.setattr(service.time, "time", lambda: NOW)
    monkeypatch.setattr(
        service,
        "MapsHistory",
        lambda: SimpleNamespace(
            get_current_map=lambda: {"name": "test-map", "start": NOW - 600}
        ),
    )
    current = service.read_context(api)
    assert current["players"][0]["player_id"] == "test-account"
    assert current["players"][0]["unit_name"] == "able"
    api.get_raw_player_snapshot.return_value["players"].append({})
    with pytest.raises(PlayerResponseAdapterError):
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
        ("!admin der commander redet nicht", True),
        ("!admin bitte mal prüfen able redet nicht", True),
        ("!admin able", True),
        ("!admin bitte mal prüfen able", True),
        ("!admin commander", True),
        ("!admin cheater", True),
        ("!administrator able", False),
        ("bitte !admin able", False),
        ("hello team", False),
        ("!yes please", False),
    ],
)
def test_public_webhook_privacy_classification(db, text, hidden):
    assert bool(domain.suppress_public_chat({"sub_content": text})) is hidden


@pytest.mark.parametrize(
    "text",
    ["!admin commander redet nicht", "!admin able", "!admin bitte mal prüfen able"],
)
def test_private_admin_report_kept_but_general_chat_webhook_suppressed(
    db, monkeypatch, text
):
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
    handler.send_chat_message({"sub_content": text})
    assert enqueued.call_count == 1
    assert enqueued.call_args.kwargs["message"].message_type.value == "admin_ping"


def test_public_report_privacy_disabled_and_config_failure(db, monkeypatch):
    storage.configure(1, Config(), "admin")
    log = {"sub_content": "!admin able"}
    assert not domain.suppress_public_chat(log)
    monkeypatch.setattr(
        Config, "load_from_db", Mock(side_effect=OSError("DB unavailable"))
    )
    assert domain.suppress_public_chat(log)
    assert not domain.suppress_public_chat({"sub_content": "hello team"})


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
        queued = list(sess.scalars(select(LeadershipMessage)))
        assert len(queued) == 6
        assert {m.player_id for m in queued} == {f"v{i}" for i in range(6)}
        assert all(m.purpose == "invite_de" for m in queued)


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
