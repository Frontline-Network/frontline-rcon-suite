import os
from datetime import datetime, timezone

os.environ.setdefault("HLL_MAINTENANCE_CONTAINER", "1")
os.environ.setdefault("SERVER_NUMBER", "1")

from rcon.autobalancer.models import BalanceSnapshot, Phase, PlayerSnapshot
from rcon.autobalancer.service import AutobalancerService
from rcon.user_config.autobalancer import AutobalancerUserConfig


class FakeRcon:
    def __init__(self):
        self.messages = []
        self.switches = []

    def message_player(self, player_id, message="", **kwargs):
        self.messages.append((player_id, message))
        return True

    def switch_player_now(self, player_id):
        self.switches.append(player_id)
        return True


class FakeStore:
    def __init__(self):
        self.state = {}
        self.status = {}
        self.events = []
        self.armed = None
        self.invitation_claims = set()

    def claim_volunteer_invitation(self, player_id):
        if player_id in self.invitation_claims:
            return False
        self.invitation_claims.add(player_id)
        return True

    def arm_player(self, player_id):
        self.armed = player_id

    def set_active(self, active):
        self.active = active

    def save_state(self, state):
        self.state = state

    def load_state(self):
        return self.state

    def save_status(self, status):
        self.status = status

    def read_events(self):
        events, self.events = self.events, []
        return events

    def acknowledge_events(self, events):
        self.acknowledged = events

    def acquire_execution(self, token):
        self.execution = token
        return True

    def release_execution(self, token):
        if getattr(self, "execution", None) == token:
            self.execution = None


class FakeRepository:
    def __init__(self):
        self.created = []
        self.updated = []

    def create(self, values):
        self.created.append(values)
        return values

    def update(self, decision_id, **values):
        self.updated.append((decision_id, values))
        return values

    def cooldown_player_ids(self, cooldown_maps, round_started_at):
        return set()


def make_snapshot(now, allies=50, axis=44):
    players = [
        PlayerSnapshot(
            player_id=f"a{index}",
            name=f"Allied {index}",
            team="allies",
            unit_id=None,
            unit_name=None,
            connected_seconds=600,
        )
        for index in range(4)
    ]
    players += [
        PlayerSnapshot(
            player_id="axis",
            name="Axis",
            team="axis",
            unit_id="dog",
            unit_name="dog",
            connected_seconds=600,
        )
    ]
    return BalanceSnapshot(
        round_id="1000:test",
        captured_at=now,
        map_name="test",
        map_elapsed_seconds=600,
        time_remaining_seconds=3600,
        allies_count=allies,
        axis_count=axis,
        players=players,
        native_autobalance_enabled=True,
        native_autobalance_threshold=2,
    )


def service():
    instance = AutobalancerService.__new__(AutobalancerService)
    instance.rcon = FakeRcon()
    instance.server_number = 1
    instance.store = FakeStore()
    instance.repository = FakeRepository()
    instance.token = "test-token"
    return instance


def test_shadow_creates_audit_proposal_without_messages_or_rcon(monkeypatch):
    instance = service()
    monkeypatch.setattr(
        "rcon.autobalancer.service.load_history", lambda *args, **kwargs: {}
    )
    config = AutobalancerUserConfig(
        mode="shadow",
        minimum_players=0,
        stable_difference_seconds=45,
        map_start_grace_minutes=0,
        map_end_guard_minutes=0,
    )
    start = datetime.fromtimestamp(2000, timezone.utc)
    instance.tick(config, make_snapshot(start), start)
    later = datetime.fromtimestamp(2046, timezone.utc)
    status = instance.tick(config, make_snapshot(later), later)
    assert status["phase"] == Phase.PROPOSED
    assert instance.repository.created[0]["status"] == "shadow"
    assert instance.repository.created[0]["rating_model_version"] == "role-aware-v2"
    assert instance.repository.created[0]["strategy_version"] == "balanced-v2"
    assert set(instance.repository.created[0]["reason"]["strategies"]) == {
        "squad-first",
        "balanced-v2",
        "skill-first",
    }
    assert status["rating_model_version"] == "role-aware-v2"
    assert status["strategy"] == "balanced-v2"
    assert instance.rcon.messages == []
    assert instance.rcon.switches == []


def test_status_exposes_count_and_strength_decision_limits(monkeypatch):
    instance = service()
    monkeypatch.setattr(
        "rcon.autobalancer.service.load_history", lambda *args, **kwargs: {}
    )
    config = AutobalancerUserConfig(
        mode="shadow",
        minimum_players=0,
        target_difference=3,
        skill_gap_soft_limit=7,
        skill_gap_hard_warning=11,
        skill_gap_min_improvement=2,
        map_start_grace_minutes=0,
        map_end_guard_minutes=0,
    )
    now = datetime.fromtimestamp(3000, timezone.utc)
    status = instance.tick(config, make_snapshot(now, allies=40, axis=40), now)
    assert status["target_difference"] == 3
    assert status["strength_thresholds"] == {
        "soft_limit": 7,
        "hard_warning": 11,
        "minimum_improvement": 2,
    }


def test_stale_death_event_never_switches():
    instance = service()
    now = datetime.fromtimestamp(3000, timezone.utc)
    snapshot = make_snapshot(now)
    state = {
        "phase": Phase.ARMED,
        "decision_id": "decision",
        "source_team": "allies",
        "target_team": "axis",
        "candidate": {
            "player_id": "a0",
            "base_tier": 0,
        },
    }
    result = instance._execute_after_death(
        state,
        snapshot,
        AutobalancerUserConfig(mode="auto"),
        {"timestamp_ms": 2_990_000, "player_id": "a0"},
        now,
    )
    assert result["phase"] == Phase.ARMED
    assert instance.rcon.switches == []


def test_fresh_death_revalidates_then_switches_exactly_once():
    instance = service()
    now = datetime.fromtimestamp(3000, timezone.utc)
    snapshot = make_snapshot(now)
    state = {
        "phase": Phase.ARMED,
        "decision_id": "decision",
        "source_team": "allies",
        "target_team": "axis",
        "candidate": {"player_id": "a0", "base_tier": 0},
    }
    result = instance._execute_after_death(
        state,
        snapshot,
        AutobalancerUserConfig(mode="auto"),
        {"timestamp_ms": 2_999_000, "player_id": "a0"},
        now,
    )
    assert result["phase"] == Phase.VERIFYING
    assert instance.rcon.switches == ["a0"]


def test_rejected_rcon_switch_is_recorded_and_disarmed():
    instance = service()
    instance.rcon.switch_player_now = lambda player_id: False
    now = datetime.fromtimestamp(3000, timezone.utc)
    result = instance._execute_after_death(
        {
            "phase": Phase.ARMED,
            "decision_id": "decision",
            "source_team": "allies",
            "target_team": "axis",
            "candidate": {"player_id": "a0", "base_tier": 0},
        },
        make_snapshot(now),
        AutobalancerUserConfig(mode="auto"),
        {"timestamp_ms": 2_999_000, "player_id": "a0"},
        now,
    )
    assert result["phase"] == Phase.OBSERVING
    assert instance.store.armed is None
    assert instance.repository.updated[-1][1]["status"] == "error"


def test_volunteer_request_reaches_all_eligible_players():
    instance = service()
    now = datetime.fromtimestamp(3000, timezone.utc)
    snap = make_snapshot(now)
    snap.players[3].role = "armycommander"
    snap.players[3].unit_type = "commander"
    state = {}
    instance._request_volunteers(
        state,
        snap,
        AutobalancerUserConfig(mode="auto", volunteer_phase_seconds=30),
    )
    notified = {player_id for player_id, _ in instance.rcon.messages}
    assert notified == {"a0", "a1", "a2"}
    assert set(state["volunteer_notified"]) == notified


def test_team_switch_log_without_player_id_can_confirm_by_name():
    instance = service()
    state = instance._apply_events(
        {
            "phase": Phase.VERIFYING,
            "candidate": {"player_id": "a0", "player_name": "Allied 0"},
        },
        [{"type": "team_switch", "player_name": "Allied 0"}],
        AutobalancerUserConfig(mode="auto"),
        make_snapshot(datetime.fromtimestamp(3000, timezone.utc)),
    )
    assert state["team_switch_seen"] is True


def test_commander_role_change_cancels_armed_candidate():
    instance = service()
    now = datetime.fromtimestamp(3000, timezone.utc)
    snapshot = make_snapshot(now)
    snapshot.players[0].role = "armycommander"
    snapshot.players[0].unit_type = "commander"
    result = instance._validate_candidate(
        {
            "phase": Phase.ARMED,
            "decision_id": "decision",
            "source_team": "allies",
            "candidate": {"player_id": "a0", "base_tier": 0},
        },
        snapshot,
        now,
    )
    assert result["phase"] == Phase.OBSERVING
    assert instance.store.armed is None


def test_incomplete_snapshot_blocks_all_actions(monkeypatch):
    instance = service()
    monkeypatch.setattr(
        "rcon.autobalancer.service.load_history", lambda *args, **kwargs: {}
    )
    config = AutobalancerUserConfig(
        mode="auto",
        minimum_players=0,
        map_start_grace_minutes=0,
        map_end_guard_minutes=0,
    )
    now = datetime.fromtimestamp(3000, timezone.utc)
    snap = make_snapshot(now)
    snap.fail_count = 1
    status = instance.tick(config, snap, now)
    assert status["phase"] == Phase.BLOCKED
    assert instance.rcon.messages == []
    assert instance.rcon.switches == []


def test_manual_approval_revalidates_candidate_before_arming():
    instance = service()
    now = datetime.fromtimestamp(3000, timezone.utc)
    snap = make_snapshot(now)
    snap.players[0].role = "armycommander"
    snap.players[0].unit_type = "commander"
    result = instance._advance(
        {
            "phase": Phase.PROPOSED,
            "decision_id": "decision",
            "source_team": "allies",
            "target_team": "axis",
            "approved_at": now.timestamp(),
            "candidate": {"player_id": "a0", "base_tier": 0},
        },
        snap,
        AutobalancerUserConfig(mode="manual"),
        [],
        now,
    )
    assert result["phase"] == Phase.OBSERVING
    assert instance.store.armed is None
    assert instance.repository.updated[-1][1]["status"] == "aborted"


def test_candidate_timeout_aborts_without_rcon_action():
    instance = service()
    now = datetime.fromtimestamp(3000, timezone.utc)
    result = instance._advance(
        {
            "phase": Phase.ARMED,
            "decision_id": "decision",
            "source_team": "allies",
            "target_team": "axis",
            "candidate_expires_at": now.timestamp() - 1,
            "candidate": {"player_id": "a0", "base_tier": 0},
        },
        make_snapshot(now),
        AutobalancerUserConfig(mode="auto"),
        [],
        now,
    )
    assert result["phase"] == Phase.OBSERVING
    assert instance.rcon.switches == []


def test_direction_change_invalidates_existing_incident(monkeypatch):
    instance = service()
    monkeypatch.setattr(
        "rcon.autobalancer.service.load_history", lambda *args, **kwargs: {}
    )
    now = datetime.fromtimestamp(3000, timezone.utc)
    instance.store.state = {
        "phase": Phase.ARMED,
        "round_id": "1000:test",
        "decision_id": "decision",
        "source_team": "allies",
        "target_team": "axis",
        "candidate": {"player_id": "a0", "base_tier": 0},
    }
    status = instance.tick(
        AutobalancerUserConfig(
            mode="auto",
            minimum_players=0,
            map_start_grace_minutes=0,
            map_end_guard_minutes=0,
        ),
        make_snapshot(now, allies=44, axis=50),
        now,
    )
    assert status["phase"] == Phase.OBSERVING
    assert instance.store.state["source_team"] == "axis"
    assert instance.repository.updated[-1][1]["status"] == "aborted"


def test_map_change_invalidates_existing_incident(monkeypatch):
    instance = service()
    monkeypatch.setattr(
        "rcon.autobalancer.service.load_history", lambda *args, **kwargs: {}
    )
    now = datetime.fromtimestamp(3000, timezone.utc)
    instance.store.state = {
        "phase": Phase.PROPOSED,
        "round_id": "900:old",
        "decision_id": "decision",
        "source_team": "allies",
        "target_team": "axis",
        "candidate": {"player_id": "a0", "base_tier": 0},
    }
    instance.tick(
        AutobalancerUserConfig(
            mode="shadow",
            minimum_players=0,
            map_start_grace_minutes=0,
            map_end_guard_minutes=0,
        ),
        make_snapshot(now),
        now,
    )
    assert instance.store.state["round_id"] == "1000:test"
    assert instance.repository.updated[-1][1]["status"] == "aborted"


def test_disabling_aborts_and_disarms_active_decision():
    instance = service()
    instance.store.state = {
        "phase": Phase.ARMED,
        "decision_id": "decision",
        "candidate": {"player_id": "a0", "reason": "selected"},
    }
    status = instance.tick(AutobalancerUserConfig(mode="disabled"))
    assert status["phase"] == Phase.IDLE
    assert instance.store.state == {}
    assert instance.store.armed is None
    assert instance.repository.updated[-1][1]["status"] == "aborted"
