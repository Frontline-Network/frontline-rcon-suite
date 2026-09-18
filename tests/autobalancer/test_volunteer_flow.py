"""Regression coverage for HLL1's lost invitations and silent !balance replies."""

from datetime import datetime, timezone

import pytest

from rcon.autobalancer import hooks
from rcon.autobalancer.models import Phase
from rcon.autobalancer.store import AutobalancerStore
from rcon.user_config.autobalancer import AutobalancerUserConfig
from tests.autobalancer.test_service import FakeRcon, make_snapshot, service
from tests.autobalancer.test_store import FakeRedis


def at(seconds=3000):
    return datetime.fromtimestamp(seconds, timezone.utc)


def config(**kwargs):
    return AutobalancerUserConfig(
        **{
            "mode": "manual",
            "minimum_players": 0,
            "map_start_grace_minutes": 0,
            "map_end_guard_minutes": 0,
            "volunteer_phase_seconds": 30,
            **kwargs,
        }
    )


def invitation(**kwargs):
    return {
        "mode": "manual",
        "phase": Phase.VOLUNTEER,
        "round_id": "1000:test",
        "incident_id": "invitation",
        "source_team": "allies",
        "target_team": "axis",
        "volunteer_started_at": 3000,
        "volunteer_until": 3030,
        "volunteers": [],
        "volunteer_notified": ["a0", "a1"],
        **kwargs,
    }


def command(**kwargs):
    return {
        "type": "volunteer",
        "incident_id": "invitation",
        "timestamp_ms": 3001000,
        "player_id": "a0",
        "event_id": "test-command",
        "stream_id": "1-0",
        **kwargs,
    }


@pytest.fixture
def instance(monkeypatch):
    monkeypatch.setattr("rcon.autobalancer.service.load_history", lambda *a, **kw: {})
    result = service()
    result.store.state = invitation()
    return result


def tick(
    instance, seconds, *, counts_match=True, allies=50, axis=44, cfg=None, **kwargs
):
    snapshot = make_snapshot(at(seconds), allies=allies, axis=axis)
    snapshot.counts_match = counts_match
    for key, value in kwargs.items():
        setattr(snapshot, key, value)
    return instance.tick(cfg or config(), snapshot, at(seconds))


@pytest.fixture
def chat(monkeypatch):
    store = AutobalancerStore(FakeRedis(), server_number=1)
    store.set_active(True)
    store.save_state(invitation())
    rcon = FakeRcon()
    monkeypatch.setattr(hooks, "_store", lambda: store)
    monkeypatch.setattr(hooks.time, "time", lambda: 3001)
    monkeypatch.setattr(hooks.AutobalancerUserConfig, "load_from_db", lambda: config())
    log = {
        "sub_content": "!balance",
        "player_id_1": "a0",
        "timestamp_ms": 3001000,
        "raw": "chat-one",
    }
    return store, rcon, log


@pytest.mark.parametrize("text", ["!balance", " !BALANCE ", "\t!Balance\n"])
def test_chat_accepts_exact_trimmed_case_insensitive_command(chat, text):
    store, rcon, log = chat
    hooks.autobalancer_volunteer(rcon, {**log, "sub_content": text})
    assert store.read_events()[0]["incident_id"] == "invitation"
    assert rcon.messages == []  # The worker validates before acknowledging.


@pytest.mark.parametrize(
    "text", ["hello", "!balance please", "!balanced", "we need !balance", "!yes"]
)
def test_other_chat_is_unaffected(chat, text):
    store, rcon, log = chat
    hooks.autobalancer_volunteer(rcon, {**log, "sub_content": text})
    assert store.read_events() == []
    assert rcon.messages == []


@pytest.mark.parametrize(
    "timestamp", [None, "bad", float("nan"), float("inf"), 2940000, 3002000]
)
def test_missing_old_or_future_chat_is_not_replayed(chat, timestamp):
    store, rcon, log = chat
    hooks.autobalancer_volunteer(rcon, {**log, "timestamp_ms": timestamp})
    assert store.read_events() == []
    assert rcon.messages == []


def test_custom_command_is_respected(chat, monkeypatch):
    store, rcon, log = chat
    monkeypatch.setattr(
        hooks.AutobalancerUserConfig,
        "load_from_db",
        lambda: config(volunteer_command="!helpbalance"),
    )
    hooks.autobalancer_volunteer(rcon, log)
    assert store.read_events() == []
    hooks.autobalancer_volunteer(rcon, {**log, "sub_content": "!HELPBALANCE"})
    assert len(store.read_events()) == 1


def test_repeated_log_and_command_spam_are_suppressed(chat):
    store, rcon, log = chat
    hooks.autobalancer_volunteer(rcon, log)
    hooks.autobalancer_volunteer(rcon, log)
    hooks.autobalancer_volunteer(rcon, {**log, "raw": "chat-two"})
    assert len(store.read_events()) == 1


@pytest.mark.parametrize(
    "mode, expected", [("disabled", "ausgeschaltet"), ("shadow", "beobachtet nur")]
)
def test_disabled_and_shadow_reply_privately_without_queueing(
    chat, monkeypatch, mode, expected
):
    store, rcon, log = chat
    monkeypatch.setattr(
        hooks.AutobalancerUserConfig, "load_from_db", lambda: config(mode=mode)
    )
    hooks.autobalancer_volunteer(rcon, log)
    assert store.read_events() == []
    assert rcon.messages[0][0] == "a0"
    assert expected in rcon.messages[0][1]


def test_stopped_worker_gives_private_feedback(chat):
    store, rcon, log = chat
    store.set_active(False)
    hooks.autobalancer_volunteer(rcon, log)
    assert "nicht erreichbar" in rcon.messages[0][1]
    assert store.read_events() == []


def test_redis_failure_gives_feedback_without_throwing(chat, monkeypatch):
    store, rcon, log = chat
    monkeypatch.setattr(
        store, "load_state", lambda: (_ for _ in ()).throw(ConnectionError())
    )
    hooks.autobalancer_volunteer(rcon, log)
    assert "nicht erreichbar" in rcon.messages[0][1]


def test_idle_command_reaches_worker_and_gets_manual_explanation(chat, instance):
    store, rcon, log = chat
    store.save_state({"phase": "idle"})
    hooks.autobalancer_volunteer(rcon, log)
    instance.store.state = {"phase": "idle"}
    instance.store.events = store.read_events()
    tick(instance, 3002, allies=44, axis=44)
    assert "kein Aufruf" in instance.rcon.messages[0][1]
    assert "Ein Admin" in instance.rcon.messages[0][1]
    assert instance.rcon.switches == []


def test_transient_count_pause_preserves_invitation_and_pending_reply(instance):
    status = tick(instance, 3000, counts_match=False)
    assert status["phase"] == Phase.BLOCKED
    assert status["paused_phase"] == Phase.VOLUNTEER
    instance.store.events = [command()]
    tick(instance, 3005, counts_match=False)
    assert instance.store.state["pending_volunteers"]["a0"]["timestamp_ms"] == 3001000
    assert instance.rcon.messages == []
    assert instance.store.acknowledged[-1]["stream_id"] == "1-0"
    status = tick(instance, 3010)
    assert status["phase"] == Phase.VOLUNTEER
    assert status["incident_id"] == "invitation"
    assert status["volunteers"] == ["a0"]
    assert status["volunteer_until"] == 3030  # No misleading deadline extension.
    assert "pending_volunteers" not in instance.store.state
    assert "Ein Admin" in instance.rcon.messages[0][1]
    assert instance.rcon.switches == []


@pytest.mark.parametrize("recovered", [True, False])
def test_long_count_pause_ends_invitation_and_notifies_once(instance, recovered):
    instance.store.state["volunteers"] = ["a0"]
    tick(instance, 3000, counts_match=False)
    status = tick(instance, 3015, counts_match=recovered)
    assert status["phase"] == Phase.BLOCKED
    assert "incident_id" not in instance.store.state
    assert {p for p, _ in instance.rcon.messages} == {"a0"}
    assert all(
        "Teamausgleich wurde abgebrochen" in m for _, m in instance.rcon.messages
    )
    message_count = len(instance.rcon.messages)
    tick(instance, 3020, counts_match=False)
    assert len(instance.rcon.messages) == message_count
    assert instance.rcon.switches == []


def test_repeated_short_pauses_share_a_bounded_budget(instance):
    tick(instance, 3000, counts_match=False)
    tick(instance, 3010)
    tick(instance, 3011, counts_match=False)
    status = tick(instance, 3016, counts_match=False)
    assert status["phase"] == Phase.BLOCKED
    assert status["paused_phase"] is None


def test_uncertain_time_does_not_count_towards_stable_observation(instance):
    instance.store.state = invitation(
        phase=Phase.OBSERVING, observed_at=2980, volunteer_notified=[]
    )
    tick(instance, 3000, counts_match=False)
    tick(instance, 3010)
    assert instance.store.state["observed_at"] == 2990
    assert tick(instance, 3025)["phase"] == Phase.OBSERVING
    assert instance.rcon.messages == []


@pytest.mark.parametrize("block", [{"fail_count": 1}, {"stable_map": False}])
def test_other_safety_blocks_still_abort_immediately(instance, block):
    status = tick(instance, 3000, **block)
    assert status["phase"] == Phase.BLOCKED
    assert status["paused_phase"] is None
    assert not instance.store.state.get("incident_id")


def test_invitation_survives_short_balanced_counts_without_switching(instance):
    tick(instance, 3005, allies=44, axis=44)
    assert instance.store.state["incident_id"] == "invitation"
    instance.store.events = [command(timestamp_ms=3006000)]
    tick(instance, 3010)
    assert instance.store.state["volunteers"] == ["a0"]
    assert instance.rcon.switches == []


def test_balanced_teams_at_deadline_end_invitation_privately(instance):
    instance.store.state["volunteers"] = ["a0"]
    status = tick(instance, 3030, allies=44, axis=44)
    assert status["phase"] == Phase.IDLE
    assert len(instance.rcon.messages) == 1
    assert "Du bleibst in deinem Team" in instance.rcon.messages[0][1]
    assert instance.repository.created == []


@pytest.mark.parametrize("timestamp", [2999000, 3030000])
def test_outside_deadline_is_rejected_explicitly(instance, timestamp):
    instance.store.events = [command(timestamp_ms=timestamp)]
    tick(instance, 3031)
    assert not instance.store.state.get("volunteers")
    assert "außerhalb" in instance.rcon.messages[0][1]


def test_on_time_reply_processed_after_deadline_counts_before_manual_proposal(instance):
    instance.store.events = [command(timestamp_ms=3029000)]
    status = tick(instance, 3031)
    assert status["phase"] == Phase.PROPOSED
    assert status["volunteers"] == ["a0"]
    assert instance.repository.created[0]["volunteer"] is True
    assert instance.store.armed is None
    assert instance.rcon.switches == []


@pytest.mark.parametrize(
    "phase", [Phase.OBSERVING, Phase.PROPOSED, Phase.ARMED, Phase.COOLDOWN]
)
def test_closed_phase_always_explains_command(instance, phase):
    state = invitation(phase=phase)
    instance._apply_events(state, [command()], config(), make_snapshot(at(3005)))
    assert instance.rcon.messages[0][0] == "a0"
    assert not state.get("volunteers")


def test_command_from_previous_incident_cannot_join_new_invitation(instance):
    state = invitation(incident_id="new")
    instance._apply_events(state, [command()], config(), make_snapshot(at(3005)))
    assert state["volunteers"] == []
    assert instance.rcon.messages


@pytest.mark.parametrize("role", ["armycommander", "commander"])
def test_hll_and_hllv_commanders_receive_exclusion_reason(instance, role):
    snap = make_snapshot(at(3005))
    snap.players[0].role = role
    instance._apply_events(instance.store.state, [command()], config(), snap)
    assert instance.store.state["volunteers"] == []
    assert "Commander" in instance.rcon.messages[0][1]


@pytest.mark.parametrize(
    "scenario, expected",
    [
        ("team", "größeren Teams"),
        ("grace", "Schonzeit"),
        ("cooldown", "früheren Teamwechsel"),
    ],
)
def test_ineligible_volunteer_gets_specific_reason(instance, scenario, expected):
    snap = make_snapshot(at(3005))
    if scenario == "team":
        snap.players[0].team = "axis"
    elif scenario == "grace":
        snap.players[0].connected_seconds = 0
    else:
        instance.repository.cooldown_player_ids = lambda *a: {"a0"}
    instance._apply_events(instance.store.state, [command()], config(), snap)
    assert expected in instance.rcon.messages[0][1]
    assert instance.store.state["volunteers"] == []


def test_failed_acknowledgement_does_not_erase_registration(instance):
    instance.rcon.message_player = lambda *a, **kw: (_ for _ in ()).throw(
        ConnectionError()
    )
    instance.store.events = [command()]
    tick(instance, 3005)
    assert instance.store.state["volunteers"] == ["a0"]
    assert instance.store.state["phase"] == Phase.VOLUNTEER


def test_failed_invitation_does_not_prevent_other_recipients(instance):
    original = instance.rcon.message_player

    def send(player_id, **kwargs):
        if player_id == "a0":
            raise ConnectionError()
        return original(player_id, **kwargs)

    instance.rcon.message_player = send
    state = {}
    instance._request_volunteers(
        state, make_snapshot(at()), config(volunteer_command="!teams")
    )
    assert state["volunteer_notified"] == ["a1", "a2", "a3"]
    assert all(
        "!teams" in message and "!balance" not in message
        for _, message in instance.rcon.messages
    )


def test_invitation_is_visible_to_chat_worker_before_first_message(instance):
    instance.store.state = {
        "phase": Phase.OBSERVING,
        "mode": "manual",
        "round_id": "1000:test",
        "source_team": "allies",
        "target_team": "axis",
        "observed_at": 2900,
    }
    original = instance.rcon.message_player

    def send(player_id, **kwargs):
        current = instance.store.load_state()
        assert current["phase"] == Phase.VOLUNTEER
        assert current["incident_id"]
        assert current["volunteer_until"] == 3030
        return original(player_id, **kwargs)

    instance.rcon.message_player = send
    tick(instance, 3000)
    assert len(instance.rcon.messages) == 4


def proposed(**kwargs):
    return invitation(
        phase=Phase.PROPOSED,
        decision_id="decision",
        candidate={"player_id": "a0", "base_tier": 0},
        proposal_expires_at=3120,
        **kwargs,
    )


def test_pause_never_arms_approved_manual_proposal_until_safe(instance):
    instance.store.state = proposed(approved_at=2999)
    tick(instance, 3000, counts_match=False)
    assert instance.store.armed is None
    assert instance.rcon.switches == []
    assert instance.store.state["decision_id"] == "decision"
    status = tick(instance, 3010)
    assert status["phase"] == Phase.ARMED
    assert instance.store.armed == "a0"
    assert instance.rcon.switches == []  # Still requires a NEW death event.


def test_expired_approval_does_not_arm_after_pause(instance):
    instance.store.state = {**proposed(approved_at=2999), "proposal_expires_at": 3005}
    tick(instance, 3000, counts_match=False)
    tick(instance, 3010)
    assert instance.store.armed is None
    assert (
        instance.repository.updated[-1][1]["reason"]["abort_reason"]
        == "Manuelle Freigabe ist abgelaufen"
    )


def test_unapproved_manual_proposal_survives_pause_without_switching(instance):
    instance.store.state = proposed()
    tick(instance, 3000, counts_match=False)
    status = tick(instance, 3010)
    assert status["phase"] == Phase.PROPOSED
    assert instance.store.armed is None
    assert instance.repository.updated == []


def test_armed_candidate_aborts_on_mismatch_and_does_not_replay_death(instance):
    instance.store.state = {
        **proposed(),
        "phase": Phase.ARMED,
        "candidate_expires_at": 3120,
    }
    instance.store.armed = "a0"
    instance.store.events = [
        {"type": "death", "player_id": "a0", "timestamp_ms": 2999000}
    ]
    tick(instance, 3000, counts_match=False)
    tick(instance, 3005)
    assert instance.store.armed is None
    assert instance.rcon.switches == []
    assert instance.repository.updated[0][1]["status"] == "aborted"


@pytest.mark.parametrize("change", ["map", "mode", "cancel", "disable", "direction"])
def test_pause_cannot_survive_explicit_invalidation(instance, change):
    tick(instance, 3000, counts_match=False)
    if change == "map":
        tick(instance, 3005, round_id="3005:new")
    elif change == "mode":
        tick(instance, 3005, cfg=config(mode="auto"))
    elif change == "cancel":
        instance.store.events = [{"type": "cancel", "incident_id": "invitation"}]
        tick(instance, 3005)
    elif change == "disable":
        tick(instance, 3005, cfg=config(mode="disabled"))
    else:
        tick(instance, 3005, allies=44, axis=50)
    assert instance.store.state.get("incident_id") != "invitation"
    assert instance.rcon.switches == []


def test_confirmed_switch_is_recorded_even_when_teams_are_now_balanced(instance):
    instance.store.state = {
        **proposed(),
        "phase": Phase.VERIFYING,
        "pre_switch_difference": 4,
        "confirmation_expires_at": 3015,
    }
    instance.store.events = [{"type": "team_switch", "player_id": "a0"}]
    snap = make_snapshot(at(3005), allies=46, axis=44)
    snap.players[0].team = "axis"
    status = instance.tick(config(), snap, at(3005))
    assert status["phase"] == Phase.COOLDOWN
    assert instance.repository.updated[-1][1]["status"] == "executed"
    assert instance.rcon.switches == []
    assert instance.store.armed is None


def test_unconfirmed_switch_waits_until_timeout_without_retry(instance):
    instance.store.state = {
        **proposed(),
        "phase": Phase.VERIFYING,
        "pre_switch_difference": 4,
        "confirmation_expires_at": 3015,
    }
    assert tick(instance, 3005, allies=46, axis=44)["phase"] == Phase.VERIFYING
    tick(instance, 3015, allies=46, axis=44)
    assert instance.repository.updated[-1][1]["status"] == "aborted"
    assert instance.rcon.switches == []


def test_pending_command_does_not_rewind_durable_stream_cursor(instance, monkeypatch):
    store = AutobalancerStore(FakeRedis(), server_number=1)
    monkeypatch.setattr(store, "claim_snapshot_slot", lambda: False)
    monkeypatch.setattr(store, "claim_snapshot_prune", lambda: False)
    instance.store = store
    store.save_state(invitation())
    tick(instance, 3000, counts_match=False)
    store.publish_event("volunteer", command())
    tick(instance, 3005, counts_match=False)
    store.publish_event("death", {"event_id": "later-death", "player_id": "other"})
    tick(instance, 3007, counts_match=False)
    cursor = store.red.get(store.key("event_cursor"))
    assert cursor == "2-0"
    tick(instance, 3010)
    assert store.red.get(store.key("event_cursor")) == cursor
    assert store.read_events() == []
    assert store.load_state()["volunteers"] == ["a0"]


def test_technical_abort_details_are_not_sent_to_players(instance):
    instance.store.state["volunteers"] = ["a0"]
    instance._abort_state(
        instance.store.state, "Interner Fehler: secret-database-connection"
    )
    assert instance.rcon.messages
    assert all(
        "secret-database-connection" not in text for _, text in instance.rcon.messages
    )


def test_completed_switch_survives_failed_completion_message(instance):
    instance.rcon.message_player = lambda *a, **kw: (_ for _ in ()).throw(
        ConnectionError()
    )
    instance.store.state = {
        **proposed(),
        "phase": Phase.VERIFYING,
        "team_switch_seen": True,
        "pre_switch_difference": 4,
        "confirmation_expires_at": 3015,
    }
    snap = make_snapshot(at(3005), allies=46, axis=44)
    snap.players[0].team = "axis"
    status = instance.tick(config(), snap, at(3005))
    assert status["phase"] == Phase.COOLDOWN
    assert instance.repository.updated[-1][1]["status"] == "executed"


def test_keep_squad_together_rule_is_explained_to_volunteer(instance):
    snap = make_snapshot(at(3005))
    snap.players[0].unit_size = 6
    instance._apply_events(
        instance.store.state,
        [command()],
        config(allow_individual_squad_fallback=False),
        snap,
    )
    assert instance.store.state["volunteers"] == []
    assert "zusammenbleiben" in instance.rcon.messages[0][1]
