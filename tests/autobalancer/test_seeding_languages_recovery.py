import pytest
from pydantic import ValidationError

from rcon.autobalancer.messages import SYSTEM, render, send
from rcon.autobalancer.seeding import (
    seeding_active,
    read_seeding_active,
    SEEDING_ACTIVE,
    SEEDING_UNKNOWN,
)
from rcon.autobalancer.models import Phase
from rcon.user_config.auto_mod_seeding import AutoModSeedingUserConfig
from rcon.user_config.autobalancer import AutobalancerUserConfig, AutobalancerMessages
from tests.autobalancer.test_service import service, make_snapshot, FakeRcon
from tests.autobalancer.test_volunteer_flow import at, config, proposed, command, tick


def seed(**kwargs):
    return AutoModSeedingUserConfig(
        enabled=True,
        enforce_cap_fight={"enabled": True, "min_players": 10, "max_players": 50},
        **kwargs
    )


@pytest.mark.parametrize(
    "players,active",
    [(0, True), (9, True), (40, True), (49, True), (50, False), (51, False)],
)
def test_seeding_threshold_matches_enforcement_end_but_protects_below_minimum(
    players, active
):
    assert seeding_active(seed(), players) is active


def test_disabled_empty_rules_and_unrelated_default_100_do_not_extend_seeding():
    cfg = seed()
    assert not seeding_active(cfg, 60)  # Empty weapon/role rules default to 100.
    cfg.enforce_cap_fight.enabled = False
    assert not seeding_active(cfg, 20)
    cfg.disallowed_weapons.weapons = {"Rifle": "Rifle"}
    cfg.disallowed_weapons.max_players = 70
    assert seeding_active(cfg, 60)
    cfg.enabled = False
    assert not seeding_active(cfg, 20)


def test_unknown_seeding_config_fails_closed(monkeypatch):
    def failed():
        raise ConnectionError("test database unavailable")

    monkeypatch.setattr(AutoModSeedingUserConfig, "load_from_db", failed)
    assert read_seeding_active(40) is None


@pytest.fixture
def worker(monkeypatch):
    monkeypatch.setattr("rcon.autobalancer.service.load_history", lambda *a, **kw: {})
    result = service()
    result.store.state = {
        **proposed(),
        "mode": "auto",
        "phase": Phase.ARMED,
        "armed_at": 2990,
        "candidate_expires_at": 3120,
    }
    result.store.armed = "a0"
    return result


@pytest.mark.parametrize("game", ["hll", "hllv"])
@pytest.mark.parametrize(
    "active,reason", [(True, SEEDING_ACTIVE), (None, SEEDING_UNKNOWN)]
)
@pytest.mark.parametrize(
    "phase", [Phase.OBSERVING, Phase.VOLUNTEER, Phase.PROPOSED, Phase.ARMED]
)
def test_seeding_stops_all_automatic_phases_even_with_fresh_death(
    worker, game, active, reason, phase
):
    worker.store.state["phase"] = phase
    worker.store.events = [
        {"type": "death", "player_id": "a0", "timestamp_ms": 2999000}
    ]
    status = tick(
        worker, 3000, cfg=config(mode="auto"), game=game, seeding_active=active
    )
    assert reason in status["block_reasons"]
    assert status["phase"] == Phase.BLOCKED
    assert worker.store.armed is None
    assert worker.rcon.switches == []
    assert "incident_id" not in worker.store.state


def test_no_seed_invites_and_explicit_balance_gets_both_explanations(worker):
    worker.store.state = {}
    cfg = config(mode="auto", message_language="de+en")
    tick(worker, 3000, cfg=cfg, seeding_active=True)
    assert worker.rcon.messages == []
    worker.store.events = [command()]
    tick(worker, 3001, cfg=cfg, seeding_active=True)
    assert len(worker.rcon.messages) == 2
    assert "Seedings" in worker.rcon.messages[0][1]
    assert "seeding" in worker.rcon.messages[1][1]
    assert worker.rcon.switches == []


def test_seed_ending_starts_new_observation_not_old_candidate(worker):
    tick(worker, 3000, cfg=config(mode="auto"), seeding_active=True)
    tick(worker, 3005, cfg=config(mode="auto"), seeding_active=False)
    assert worker.store.state["phase"] == Phase.OBSERVING
    assert worker.store.state["observed_at"] == 3005
    assert worker.store.armed is None


def test_seeding_enabled_between_snapshot_and_execution_prevents_switch(
    worker, monkeypatch
):
    monkeypatch.setattr(AutoModSeedingUserConfig, "load_from_db", seed)
    worker.store.events = [
        {"type": "death", "player_id": "a0", "timestamp_ms": 2999000}
    ]
    tick(worker, 3000, allies=25, axis=19, cfg=config(mode="auto"))
    assert worker.rcon.switches == []
    assert worker.store.armed is None
    assert worker.store.execution is None
    assert worker.repository.updated[-1][1]["reason"]["abort_reason"] == SEEDING_ACTIVE


def test_armed_pause_discards_delayed_deaths_then_executes_once_on_new_death(worker):
    cfg = config(mode="auto")
    tick(worker, 3000, cfg=cfg, counts_match=False)
    assert worker.store.armed is None
    # Arriving during recovery does not make an old death eligible.
    worker.store.events = [
        {"type": "death", "player_id": "a0", "timestamp_ms": 3004000}
    ]
    tick(worker, 3005, cfg=cfg)
    assert worker.store.armed == "a0"
    assert worker.rcon.switches == []
    assert worker.rcon.messages == []  # No repeat of the selection popup.
    worker.store.events = [
        {"type": "death", "player_id": "a0", "timestamp_ms": 3009000}
    ]
    tick(worker, 3010, cfg=cfg)
    assert worker.rcon.switches == ["a0"]
    assert worker.store.state["phase"] == Phase.VERIFYING
    worker.store.events = [
        {"type": "death", "player_id": "a0", "timestamp_ms": 3009000}
    ]
    tick(worker, 3011, cfg=cfg)
    assert worker.rcon.switches == ["a0"]


@pytest.mark.parametrize("recovered", [False, True])
def test_armed_pause_has_cumulative_15_second_limit(worker, recovered):
    cfg = config(mode="auto")
    tick(worker, 3000, cfg=cfg, counts_match=False)
    tick(worker, 3007, cfg=cfg)
    tick(worker, 3010, cfg=cfg, counts_match=False)
    tick(worker, 3018, cfg=cfg, counts_match=recovered)
    assert worker.store.armed is None
    assert worker.repository.updated[-1][1]["status"] == "aborted"
    assert worker.rcon.switches == []


def test_pause_does_not_extend_candidate_deadline(worker):
    cfg = config(mode="auto")
    worker.store.state["candidate_expires_at"] = 3003
    tick(worker, 3000, cfg=cfg, counts_match=False)
    tick(worker, 3005, cfg=cfg)
    assert worker.store.armed is None
    assert (
        worker.repository.updated[-1][1]["reason"]["abort_reason"]
        == "Kandidaten-Timeout"
    )


@pytest.mark.parametrize("change", ["commander", "team", "disconnect", "balanced"])
def test_pause_recovery_revalidates_candidate_and_need(worker, change):
    cfg = config(mode="auto")
    tick(worker, 3000, cfg=cfg, counts_match=False)
    snapshot = make_snapshot(at(3005))
    if change == "commander":
        snapshot.players[0].role = "armycommander"
    elif change == "team":
        snapshot.players[0].team = "axis"
    elif change == "disconnect":
        snapshot.players.pop(0)
    else:
        snapshot.axis_count = snapshot.allies_count
    worker.tick(cfg, snapshot, at(3005))
    assert worker.store.armed is None
    assert worker.rcon.switches == []


@pytest.mark.parametrize(
    "timestamp", [None, float("nan"), float("inf"), 3001000, 2989000]
)
def test_invalid_future_or_pre_arm_death_is_never_used(worker, timestamp):
    worker.store.events = [
        {"type": "death", "player_id": "a0", "timestamp_ms": timestamp}
    ]
    tick(worker, 3000, cfg=config(mode="auto"))
    assert worker.rcon.switches == []


@pytest.mark.parametrize("key", list(SYSTEM) + list(AutobalancerMessages.model_fields))
def test_every_player_message_has_distinct_de_and_en_packets(key):
    values = {
        "target_team": "US",
        "seconds": 30,
        "cooldown_maps": 3,
        "squad_name": "Able",
    }
    if key in SYSTEM:
        values = {}
    texts = render(config(message_language="de+en"), key, **values)
    assert len(texts) == 2 and all(texts) and texts[0] != texts[1]
    assert "{" not in "".join(texts)


def test_custom_german_survives_roundtrip_and_english_is_separately_editable():
    cfg = config(
        message_language="de+en",
        messages={"volunteer_registered": "Danke, Test!"},
        messages_en={"volunteer_registered": "Thanks, test!"},
    )
    restored = AutobalancerUserConfig.model_validate(cfg.model_dump())
    assert render(restored, "volunteer_registered") == ["Danke, Test!", "Thanks, test!"]
    restored.message_language = "en"
    assert render(restored, "volunteer_registered") == ["Thanks, test!"]


def test_old_config_preserves_german_default_and_bad_english_placeholder_rejected():
    assert (
        AutobalancerUserConfig.model_validate(
            {"messages": {"volunteer_registered": "Custom"}}
        ).message_language
        == "de"
    )
    with pytest.raises(ValidationError):
        config(messages_en={"volunteer_request": "Hello {secret}"})
    with pytest.raises(ValidationError):
        config(message_language="fr")


def test_failure_of_german_delivery_does_not_suppress_english():
    rcon = FakeRcon()

    def deliver(pid, message):
        rcon.messages.append((pid, message))
        if len(rcon.messages) == 1:
            raise TimeoutError("uncertain")
        return True

    rcon.message_player = deliver
    assert not send(rcon, "p", config(message_language="de+en"), "ended")
    assert len(rcon.messages) == 2
    assert "Team balancing" in rcon.messages[1][1]


def test_manual_mode_and_custom_command_are_in_both_invitations():
    texts = render(
        config(message_language="de+en", volunteer_command="!helpbalance"),
        "volunteer_request",
        target_team="NVA",
        seconds=30,
        manual=True,
    )
    assert all("!helpbalance" in text and "NVA" in text for text in texts)
    assert "Admin" in texts[0] and "admin" in texts[1]
