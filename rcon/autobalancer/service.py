from __future__ import annotations

import logging
import threading
import time
import uuid
from datetime import datetime, timezone
from statistics import median
from typing import Any

from rcon.automods import action_guard
from rcon.user_config.autobalancer import AutobalancerUserConfig
from rcon.utils import get_server_number

from .feedback import event_seconds, fresh_command
from .messages import closed_key, send as send_message
from .history import load_history
from .models import BalancePlan, BalanceSnapshot, Phase
from .planner import (
    build_plan,
    build_strength_swap_recommendations,
    build_strategy_plans,
    eligible_players,
    protection_tier,
    team_rating,
)
from .rating import RATING_MODEL_VERSION, calculate_ratings
from .repository import DecisionRepository
from .snapshot import build_snapshot
from .seeding import block_reason as seeding_block_reason, read_seeding_active
from .store import AutobalancerStore, new_instance_token
from .telemetry import persist_snapshot, prune_snapshots

logger = logging.getLogger(__name__)
COUNTS_MISMATCH = "Teamzählungen stimmen nicht überein"
DATA_PAUSE_MAX_SECONDS = 15
SWITCH_GUARD_RULE = 'AutobalancerSwitch'


class AutobalancerService:
    def __init__(self, rcon=None, store=None, repository=None):
        if rcon is None:
            # Importing the full RCON stack also initializes legacy Django/
            # Channels compatibility modules. Keep that side effect out of
            # pure planner/service imports and load it only for the real worker.
            from rcon.rcon import get_rcon

            rcon = get_rcon()
        self.rcon = rcon
        self.server_number = int(get_server_number())
        self.store = store or AutobalancerStore(server_number=self.server_number)
        self.repository = repository or DecisionRepository(self.server_number)
        self.action_guard = action_guard
        self.token = new_instance_token()
        self._is_leader = False

    def run(self, stop_event: threading.Event | None = None) -> None:
        stop_event = stop_event or threading.Event()
        while not stop_event.is_set():
            config = AutobalancerUserConfig.load_from_db()
            try:
                if not self._is_leader:
                    self._is_leader = self.store.acquire_leader(self.token)
                    if self._is_leader:
                        self.repository.abort_unfinished(
                            "autobalancer service restarted"
                        )
                        self.store.clear_runtime_state(preserve_cursor=True)
                elif not self.store.renew_leader(self.token):
                    self._is_leader = False
                if self._is_leader:
                    self.tick(config=config)
            except Exception as exc:
                logger.exception("Autobalancer tick failed")
                try:
                    state = self.store.load_state()
                    self.store.arm_player(None)
                    self.store.save_state({})
                    try:
                        self._abort_state(state, f"Interner Fehler: {exc}")
                    except Exception:
                        logger.exception("Unable to abort failed autobalancer decision")
                    self.store.save_status(
                        {
                            "mode": config.mode,
                            "phase": Phase.BLOCKED,
                            "block_reasons": [f"Interner Fehler: {exc}"],
                        }
                    )
                except Exception:
                    logger.exception("Unable to publish autobalancer failure status")
            if stop_event.wait(config.poll_interval_seconds):
                break
        if self._is_leader:
            self.store.release_leader(self.token)

    def tick(
        self,
        config: AutobalancerUserConfig | None = None,
        snapshot: BalanceSnapshot | None = None,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        config = config or AutobalancerUserConfig.load_from_db()
        self._feedback_config = config
        now = now or datetime.now(timezone.utc)
        if config.mode == "disabled":
            state = self.store.load_state()
            self.store.arm_player(None)
            self.store.set_active(False)
            self.store.save_state({})
            self._abort_state(state, "Autobalancer wurde deaktiviert")
            events = self.store.read_events()
            for event in events:
                if event.get("type") == "volunteer" and fresh_command(
                    event, now.timestamp()
                ):
                    send_message(
                        self.rcon,
                        event.get("player_id"),
                        config,
                        "disabled",
                    )
            if events:
                self.store.acknowledge_events(events)
            status = {
                "mode": "disabled",
                "phase": Phase.IDLE,
                "block_reasons": ["Autobalancer ist deaktiviert"],
            }
            self.store.save_status(status)
            return status

        self.store.set_active(True)
        snapshot = snapshot or build_snapshot(self.rcon, self.store, now=now)
        history_servers = config.history_server_numbers or [self.server_number]
        historical = self._load_history(snapshot, history_servers, now)
        ratings = calculate_ratings(
            snapshot.players,
            historical,
            now=now,
            half_life_days=config.history_half_life_days,
        )
        for player in snapshot.players:
            player.rating = ratings[player.player_id]

        if getattr(self.store, "claim_snapshot_slot", lambda: False)():
            try:
                persist_snapshot(self.server_number, snapshot)
            except Exception:
                logger.exception("Unable to persist autobalancer live snapshot")
        if getattr(self.store, "claim_snapshot_prune", lambda: False)():
            try:
                prune_snapshots(now)
            except Exception:
                logger.exception("Unable to prune old autobalancer snapshots")

        state = self.store.load_state()
        new_events = self.store.read_events()
        events = list((state.get("pending_volunteers", {}) or {}).values()) + new_events
        hard_blocks = self._hard_blocks(snapshot, config)
        warnings = self._warnings(snapshot, config)

        if state.get("mode") and state["mode"] != config.mode:
            self._abort_state(state, "Betriebsart wurde geändert")
            self.store.arm_player(None)
            state = {}
        if state.get("round_id") and state["round_id"] != snapshot.round_id:
            self._abort_state(state, "Kartenwechsel")
            self.store.arm_player(None)
            state = {}
        elif any(event.get("type") in {"match_start", "match_end"} for event in events):
            self._abort_state(state, "Matchwechsel")
            self.store.arm_player(None)
            state = {}
        paused = self._pause_for_counts(state, hard_blocks, now)
        state = self._apply_events(
            state,
            events,
            config,
            snapshot,
            now,
            defer_volunteers=paused,
            blocked=bool(hard_blocks),
        )

        if hard_blocks and paused and state.get("data_pause_started_at") is not None:
            # Keep the incident, but never advance, arm or execute on unsafe data.
            self.store.arm_player(None)
        elif hard_blocks:
            self._abort_state(state, "; ".join(hard_blocks))
            self.store.arm_player(None)
            state = {
                "phase": Phase.BLOCKED,
                "round_id": snapshot.round_id,
                "observed_at": now.timestamp(),
            }
        elif state.get("phase") == Phase.VERIFYING:
            # A successful switch can itself put the counts within the target.
            # Confirm and record it before the generic "already balanced" reset.
            state = self._advance(state, snapshot, config, events, now)
        elif abs(snapshot.difference) <= config.target_difference:
            self.store.arm_player(None)
            if not (
                state.get("phase") == Phase.VOLUNTEER
                and now.timestamp() < float(state.get("volunteer_until", 0))
            ):
                self._abort_state(state, "Teams sind bereits ausgeglichen")
                state = {"phase": Phase.IDLE, "round_id": snapshot.round_id}
        else:
            direction = snapshot.larger_team
            if state.get("source_team") and state.get("source_team") != direction:
                self._abort_state(state, "Richtung des Ungleichgewichts hat gewechselt")
                self.store.arm_player(None)
                state = {}
            state = self._advance(state, snapshot, config, events, now)

        state["mode"] = config.mode
        self.store.save_state(state)
        status = self._status(state, snapshot, config, hard_blocks, warnings)
        self.store.save_status(status)
        if new_events:
            self.store.acknowledge_events(new_events)
        return status

    def _pause_for_counts(
        self, state: dict[str, Any], hard_blocks: list[str], now: datetime
    ) -> bool:
        """Tolerate at most 15s of count-only jitter per observation/incident.

        Invitations and approval deadlines are not extended. Pending chat keeps
        its original timestamp; no death events are saved for later execution.
        Armed candidates are disarmed during a short pause; recovery requires a
        newly observed death. The original candidate deadline is never extended.
        """
        now_ts = now.timestamp()
        if hard_blocks == [COUNTS_MISMATCH] and state.get("phase") in {
            Phase.OBSERVING,
            Phase.VOLUNTEER,
            Phase.PROPOSED,
            Phase.ARMED,
            Phase.VERIFYING,
        }:
            started = state.setdefault("data_pause_started_at", now_ts)
            elapsed = max(0, now_ts - float(started))
            used = float(state.get("data_pause_seconds", 0)) + elapsed
            if state.get("phase") == Phase.ARMED and now_ts >= float(
                state.get("candidate_expires_at", 0)
            ):
                return False
            if state.get("phase") == Phase.VERIFYING and now_ts >= float(
                state.get("confirmation_expires_at", 0)
            ):
                return False
            return used < DATA_PAUSE_MAX_SECONDS
        if not hard_blocks and "data_pause_started_at" in state:
            elapsed = max(0, now_ts - float(state.pop("data_pause_started_at")))
            used = float(state.get("data_pause_seconds", 0)) + elapsed
            state["data_pause_seconds"] = used
            if used >= DATA_PAUSE_MAX_SECONDS:
                hard_blocks.append("Teamzählungen waren zu lange nicht verlässlich")
            elif state.get("phase") == Phase.OBSERVING:
                state["observed_at"] = float(state.get("observed_at", now_ts)) + elapsed
            elif state.get("phase") == Phase.ARMED:
                state["death_not_before"] = now_ts
        return False

    def _load_history(
        self,
        snapshot: BalanceSnapshot,
        history_servers: list[int],
        now: datetime,
    ):
        player_ids = tuple(sorted(player.player_id for player in snapshot.players))
        cache = getattr(self, "_history_cache", None)
        if (
            cache
            and cache["player_ids"] == player_ids
            and cache["servers"] == tuple(history_servers)
            and now.timestamp() - cache["loaded_at"] < 60
        ):
            return cache["value"]
        value = load_history(
            list(player_ids), history_servers, now=now.replace(tzinfo=None)
        )
        self._history_cache = {
            "player_ids": player_ids,
            "servers": tuple(history_servers),
            "loaded_at": now.timestamp(),
            "value": value,
        }
        return value

    def _hard_blocks(
        self, snapshot: BalanceSnapshot, config: AutobalancerUserConfig
    ) -> list[str]:
        reasons: list[str] = []
        if reason := seeding_block_reason(snapshot.seeding_active):
            reasons.append(reason)
        if snapshot.fail_count:
            reasons.append("Spielerdaten sind unvollständig")
        if not snapshot.counts_match:
            reasons.append(COUNTS_MISMATCH)
        if not snapshot.stable_map:
            reasons.append("Kartendaten sind nicht stabil")
        if snapshot.allies_count + snapshot.axis_count < config.minimum_players:
            reasons.append("Mindestspielerzahl ist nicht erreicht")
        if snapshot.map_elapsed_seconds < config.map_start_grace_minutes * 60:
            reasons.append("Kartenschutz nach Rundenstart ist aktiv")
        if snapshot.time_remaining_seconds <= config.map_end_guard_minutes * 60:
            reasons.append("Kartenschutz vor Rundenende ist aktiv")
        return reasons

    def _warnings(
        self, snapshot: BalanceSnapshot, config: AutobalancerUserConfig
    ) -> list[str]:
        warnings: list[str] = []
        if snapshot.native_autobalance_enabled is False:
            warnings.append("Der native HLL-Autobalancer ist deaktiviert")
        if (
            snapshot.native_autobalance_threshold is not None
            and snapshot.native_autobalance_threshold > config.target_difference
        ):
            warnings.append(
                "Der native HLL-Autobalancer hat einen höheren Schwellenwert als CRCON"
            )
        if snapshot.native_autobalance_enabled is None:
            warnings.append(
                "Native Autobalance-Konfiguration konnte nicht gelesen werden"
            )
        confidences = [
            player.rating.confidence
            for player in snapshot.players
            if player.rating.role_family != "commander"
        ]
        if confidences and median(confidences) < 0.6:
            warnings.append(
                "Die mediane Ratingkonfidenz liegt noch unter dem Pilotziel von 60 %"
            )
        return warnings

    def _advance(
        self,
        state: dict[str, Any],
        snapshot: BalanceSnapshot,
        config: AutobalancerUserConfig,
        events: list[dict[str, Any]],
        now: datetime,
    ) -> dict[str, Any]:
        phase = state.get("phase")
        now_ts = now.timestamp()
        if phase == Phase.COOLDOWN:
            if now_ts < float(state.get("cooldown_until", 0)):
                return state
            return {
                "phase": Phase.OBSERVING,
                "round_id": snapshot.round_id,
                "source_team": snapshot.larger_team,
                "target_team": snapshot.smaller_team,
                "observed_at": state.get("cooldown_started_at", now_ts),
                "executed_count": 0,
            }
        if phase in (None, Phase.IDLE, Phase.BLOCKED, Phase.COOLDOWN):
            return {
                "phase": Phase.OBSERVING,
                "round_id": snapshot.round_id,
                "source_team": snapshot.larger_team,
                "target_team": snapshot.smaller_team,
                "observed_at": now_ts,
                "executed_count": 0,
            }
        if phase == Phase.OBSERVING:
            stable_for = now_ts - float(state.get("observed_at", now_ts))
            if stable_for < config.stable_difference_seconds:
                return state
            state["incident_id"] = uuid.uuid4().hex
            state["volunteers"] = []
            if config.mode == "shadow" or config.volunteer_phase_seconds == 0:
                return self._propose(state, snapshot, config, now)
            state["phase"] = Phase.VOLUNTEER
            state["volunteer_started_at"] = now_ts
            state["volunteer_until"] = now_ts + config.volunteer_phase_seconds
            # A quick reply can reach the log worker while invitations are still
            # being sent. Make the context visible before the first message.
            self.store.save_state({**state, "mode": config.mode})
            self._request_volunteers(state, snapshot, config)
            return state
        if phase == Phase.VOLUNTEER:
            if now_ts >= float(state.get("volunteer_until", 0)):
                return self._propose(state, snapshot, config, now)
            return state
        if phase == Phase.PROPOSED:
            if config.mode == "shadow":
                return self._validate_candidate(state, snapshot, now)
            if config.mode == "manual" and now_ts >= float(
                state.get("proposal_expires_at", 0)
            ):
                self._abort_state(state, "Manuelle Freigabe ist abgelaufen")
                return self._restart_observation(snapshot, now)
            if config.mode == "manual" and state.get("approved_at"):
                validated = self._validate_candidate(state, snapshot, now)
                if validated.get("phase") != Phase.PROPOSED:
                    return validated
                return self._arm(validated, config, now)
            return state
        if phase == Phase.ARMED:
            candidate = state.get("candidate") or {}
            if now_ts >= float(state.get("candidate_expires_at", 0)):
                self._abort_state(state, "Kandidaten-Timeout")
                self.store.arm_player(None)
                return self._restart_observation(snapshot, now)
            validated = self._validate_candidate(state, snapshot, now)
            if validated.get("phase") != Phase.ARMED:
                return validated
            self.store.arm_player(candidate.get("player_id"))
            death = next(
                (
                    event
                    for event in events
                    if event.get("type") == "death"
                    and event.get("player_id") == candidate.get("player_id")
                ),
                None,
            )
            if death:
                return self._execute_after_death(state, snapshot, config, death, now)
            return self._validate_candidate(state, snapshot, now)
        if phase == Phase.VERIFYING:
            candidate = state.get("candidate") or {}
            player = next(
                (
                    player
                    for player in snapshot.players
                    if player.player_id == candidate.get("player_id")
                ),
                None,
            )
            confirmed = (
                state.get("team_switch_seen")
                and player is not None
                and player.team == state.get("target_team")
                and abs(snapshot.difference)
                < int(state.get("pre_switch_difference", 101))
            )
            if confirmed:
                return self._complete_switch(state, snapshot, config, now)
            if now_ts >= float(state.get("confirmation_expires_at", 0)):
                self._abort_state(state, "Teamwechsel wurde nicht bestätigt")
                self.store.arm_player(None)
                return self._restart_observation(snapshot, now)
        return state

    def _restart_observation(
        self, snapshot: BalanceSnapshot, now: datetime
    ) -> dict[str, Any]:
        return {
            "phase": Phase.OBSERVING,
            "round_id": snapshot.round_id,
            "source_team": snapshot.larger_team,
            "target_team": snapshot.smaller_team,
            "observed_at": now.timestamp(),
            "executed_count": 0,
        }

    def _request_volunteers(
        self,
        state: dict[str, Any],
        snapshot: BalanceSnapshot,
        config: AutobalancerUserConfig,
    ) -> None:
        if snapshot.smaller_team is None:
            return
        recipients = eligible_players(
            snapshot,
            cooldown_player_ids=self._cooldown_ids(snapshot, config),
            connection_grace_seconds=config.connection_grace_seconds,
            allow_individual_squad_fallback=config.allow_individual_squad_fallback,
        )
        state["volunteer_notified"] = []
        for player in recipients:
            # Reserve before delivery: uncertain/failed sends must not spam retries.
            if not self.store.claim_volunteer_invitation(player.player_id):
                continue
            if send_message(
                self.rcon,
                player.player_id,
                config,
                "volunteer_request",
                target_team=snapshot.team_labels.get(
                    snapshot.smaller_team, snapshot.smaller_team.capitalize()
                ),
                seconds=config.volunteer_phase_seconds,
                manual=True,
            ):
                state["volunteer_notified"].append(player.player_id)

    def _cooldown_ids(
        self,
        snapshot: BalanceSnapshot,
        config: AutobalancerUserConfig,
    ) -> set[str]:
        round_started_at = datetime.fromtimestamp(
            int(snapshot.round_id.split(":", 1)[0] or 0), timezone.utc
        ).replace(tzinfo=None)
        cooldown = self.repository.cooldown_player_ids(
            config.cooldown_maps, round_started_at
        )
        pending = self.action_guard.pending_players(self.server_number, SWITCH_GUARD_RULE)
        if '*' in pending:
            return cooldown | {player.player_id for player in snapshot.players}
        return cooldown | pending

    def _plan(
        self,
        state: dict[str, Any],
        snapshot: BalanceSnapshot,
        config: AutobalancerUserConfig,
    ) -> BalancePlan | None:
        return build_plan(
            snapshot,
            target_difference=config.target_difference,
            volunteers=state.get("volunteers") or [],
            cooldown_player_ids=self._cooldown_ids(snapshot, config),
            pending_player_ids=(
                [state["candidate"]["player_id"]] if state.get("candidate") else []
            ),
            connection_grace_seconds=config.connection_grace_seconds,
            max_switches=max(
                0,
                config.max_switches_per_incident - int(state.get("executed_count", 0)),
            ),
            allow_individual_squad_fallback=config.allow_individual_squad_fallback,
            strategy=config.skill_strategy,
            skill_gap_soft_limit=config.skill_gap_soft_limit,
            skill_gap_hard_warning=config.skill_gap_hard_warning,
            skill_gap_min_improvement=config.skill_gap_min_improvement,
        )

    def _strategy_plans(
        self,
        state: dict[str, Any],
        snapshot: BalanceSnapshot,
        config: AutobalancerUserConfig,
        cooldown_player_ids: set[str] | None = None,
    ) -> dict[str, BalancePlan | None]:
        cooldown_player_ids = (
            self._cooldown_ids(snapshot, config)
            if cooldown_player_ids is None
            else cooldown_player_ids
        )
        return build_strategy_plans(
            snapshot,
            target_difference=config.target_difference,
            volunteers=state.get("volunteers") or [],
            cooldown_player_ids=cooldown_player_ids,
            pending_player_ids=(
                [state["candidate"]["player_id"]] if state.get("candidate") else []
            ),
            connection_grace_seconds=config.connection_grace_seconds,
            max_switches=max(
                0,
                config.max_switches_per_incident - int(state.get("executed_count", 0)),
            ),
            allow_individual_squad_fallback=config.allow_individual_squad_fallback,
            skill_gap_soft_limit=config.skill_gap_soft_limit,
            skill_gap_hard_warning=config.skill_gap_hard_warning,
            skill_gap_min_improvement=config.skill_gap_min_improvement,
        )

    def _propose(
        self,
        state: dict[str, Any],
        snapshot: BalanceSnapshot,
        config: AutobalancerUserConfig,
        now: datetime,
    ) -> dict[str, Any]:
        cooldown_player_ids = self._cooldown_ids(snapshot, config)
        strategy_plans = self._strategy_plans(
            state,
            snapshot,
            config,
            cooldown_player_ids=cooldown_player_ids,
        )
        plan = strategy_plans.get(config.skill_strategy)
        if plan is None or not plan.candidates:
            state["phase"] = Phase.BLOCKED
            state["block_reasons"] = (
                plan.blocked_reasons if plan else ["Kein Wechsel erforderlich"]
            )
            self._abort_state(state, "; ".join(state["block_reasons"]))
            return state
        candidate = plan.candidates[0]
        decision_id = uuid.uuid4().hex
        status = "shadow" if config.mode == "shadow" else "proposed"
        round_started_at = datetime.fromtimestamp(
            int(snapshot.round_id.split(":", 1)[0] or 0), timezone.utc
        ).replace(tzinfo=None)
        self.repository.create(
            {
                "decision_id": decision_id,
                "incident_id": state["incident_id"],
                "round_id": snapshot.round_id,
                "round_started_at": round_started_at,
                "mode": config.mode,
                "status": status,
                "source_team": plan.source_team,
                "target_team": plan.target_team,
                "player_id": candidate.player.player_id,
                "player_name": candidate.player.name,
                "volunteer": candidate.volunteer,
                "protection_tier": candidate.base_tier,
                "rating": candidate.player.rating.value,
                "rating_confidence": candidate.player.rating.confidence,
                "rating_model_version": RATING_MODEL_VERSION,
                "strategy_version": config.skill_strategy,
                "reason": {
                    "selection": candidate.reason,
                    "plan": plan.public_dict(),
                    "safety": {
                        "candidate_in_cooldown": (
                            candidate.player.player_id in cooldown_player_ids
                        ),
                        "candidate_is_commander": (
                            candidate.player.rating.role_family == "commander"
                        ),
                        "snapshot_complete": bool(
                            snapshot.counts_match
                            and snapshot.fail_count == 0
                            and snapshot.stable_map
                        ),
                        "simulated_difference_after_first": abs(
                            snapshot.difference - (2 if snapshot.difference > 0 else -2)
                        ),
                    },
                    "strategies": {
                        name: candidate_plan.public_dict() if candidate_plan else None
                        for name, candidate_plan in strategy_plans.items()
                    },
                },
                "before_snapshot": snapshot.audit_dict(),
            }
        )
        state.update(
            {
                "phase": Phase.PROPOSED,
                "decision_id": decision_id,
                "candidate": candidate.public_dict(),
                "plan": plan.public_dict(),
                "strategy_plans": {
                    name: candidate_plan.public_dict() if candidate_plan else None
                    for name, candidate_plan in strategy_plans.items()
                },
                "team_labels": dict(snapshot.team_labels),
                "proposal_expires_at": now.timestamp()
                + config.manual_proposal_timeout_seconds,
            }
        )
        if config.mode == "auto":
            return self._arm(state, config, now)
        return state

    def _arm(
        self,
        state: dict[str, Any],
        config: AutobalancerUserConfig,
        now: datetime,
    ) -> dict[str, Any]:
        candidate = state["candidate"]
        self.store.arm_player(candidate["player_id"])
        send_message(
            self.rcon,
            candidate["player_id"],
            config,
            "candidate_selected",
            target_team=(state.get("team_labels") or {}).get(
                state["target_team"], str(state["target_team"]).capitalize()
            ),
            cooldown_maps=config.cooldown_maps,
        )
        state["phase"] = Phase.ARMED
        state["armed_at"] = now.timestamp()
        state["candidate_expires_at"] = (
            now.timestamp() + config.candidate_timeout_seconds
        )
        self.repository.update(
            state["decision_id"],
            status="armed",
            approved_by=state.get("approved_by"),
        )
        return state

    def _validate_candidate(
        self, state: dict[str, Any], snapshot: BalanceSnapshot, now: datetime
    ) -> dict[str, Any]:
        candidate_data = state.get("candidate") or {}
        player = next(
            (
                player
                for player in snapshot.players
                if player.player_id == candidate_data.get("player_id")
            ),
            None,
        )
        reason = None
        if player is None:
            reason = "Kandidat hat den Server verlassen"
        elif player.team != state.get("source_team"):
            reason = "Kandidat hat das Team gewechselt"
        else:
            tier, _ = protection_tier(player)
            if tier is None:
                reason = "Kandidat ist jetzt Commander"
            elif tier > int(candidate_data.get("base_tier", tier)):
                reason = "Kandidat ist in einen stärker geschützten Squad gewechselt"
        if reason:
            self._abort_state(state, reason)
            self.store.arm_player(None)
            return self._restart_observation(snapshot, now)
        return state

    def _execute_after_death(
        self,
        state: dict[str, Any],
        snapshot: BalanceSnapshot,
        config: AutobalancerUserConfig,
        death: dict[str, Any],
        now: datetime,
    ) -> dict[str, Any]:
        death_time = event_seconds(death)
        if (
            death_time is None
            or not 0
            <= now.timestamp() - death_time
            <= config.death_event_max_age_seconds
            or death_time
            < max(
                float(state.get("armed_at", 0)), float(state.get("death_not_before", 0))
            )
            or self._hard_blocks(snapshot, config)
        ):
            return state
        validated = self._validate_candidate(state, snapshot, now)
        if validated.get("phase") != Phase.ARMED:
            return validated
        before = abs(snapshot.difference)
        after = abs(snapshot.difference - (2 if snapshot.difference > 0 else -2))
        if after >= before:
            self._abort_state(state, "Wechsel würde die Teamdifferenz nicht reduzieren")
            self.store.arm_player(None)
            return self._restart_observation(snapshot, now)
        candidate = state["candidate"]
        execution_token = (
            f"{getattr(self, 'token', 'autobalancer')}:{state['decision_id']}"
        )
        if not self.store.acquire_execution(execution_token):
            logger.warning("Another autobalancer execution is already in progress")
            return state
        try:
            # Recheck current seeding configuration at the execution boundary,
            # including changes after the candidate was selected.
            if reason := seeding_block_reason(
                read_seeding_active(snapshot.allies_count + snapshot.axis_count)
            ):
                self._abort_state(state, reason)
                self.store.arm_player(None)
                return self._restart_observation(snapshot, now)
            try:
                guard_token = self.action_guard.reserve(
                    self.server_number, candidate['player_id'], [SWITCH_GUARD_RULE], 'switch'
                )
            except Exception:
                logger.exception('Autobalancer switch not sent: durable reservation unavailable')
                self._abort_state(state, 'Teamwechsel-Sicherung nicht verfügbar')
                self.store.arm_player(None)
                return self._restart_observation(snapshot, now)
            if guard_token is None:
                self._abort_state(state, 'Vorheriger Teamwechsel wartet auf Prüfung')
                self.store.arm_player(None)
                return self._restart_observation(snapshot, now)
            if self.repository.update(state["decision_id"], status="executing") is None:
                logger.error('Autobalancer switch not sent: decision is unavailable')
                self.store.arm_player(None)
                return self._restart_observation(snapshot, now)
            try:
                switch = (self.rcon.switch_volunteer_now if candidate.get("volunteer")
                          else self.rcon.switch_player_now)
                switched = switch(candidate["player_id"])
            except Exception as exc:
                logger.exception("Autobalancer RCON team switch failed")
                switched = None
                error = str(exc)
            else:
                error = ("RCON hat den Teamwechsel abgelehnt" if switched is False
                         else "RCON hat den Teamwechsel nicht eindeutig bestätigt")
        finally:
            self.store.release_execution(execution_token)
        if switched is not True:
            if switched is False:
                try:
                    self.action_guard.finish(self.server_number, candidate['player_id'],
                                             guard_token, 'rejected', expected=1)
                except Exception:
                    logger.exception('Could not record rejected switch; reservation retained')
            self.repository.update(
                state["decision_id"],
                status="error",
                reason={
                    "error": error,
                    "selection": candidate.get("reason"),
                    "plan": state.get("plan"),
                },
            )
            self.store.arm_player(None)
            self._notify_ended(state, "Teamwechsel wurde nicht bestätigt")
            return self._restart_observation(snapshot, now)
        state["phase"] = Phase.VERIFYING
        state['switch_guard_token'] = guard_token
        state["pre_switch_difference"] = before
        state["confirmation_expires_at"] = (
            now.timestamp() + config.switch_confirmation_timeout_seconds
        )
        state["team_switch_seen"] = False
        self.repository.update(state["decision_id"], status="verifying")
        return state

    def _complete_switch(
        self,
        state: dict[str, Any],
        snapshot: BalanceSnapshot,
        config: AutobalancerUserConfig,
        now: datetime,
    ) -> dict[str, Any]:
        candidate = state["candidate"]
        decision = self.repository.update(
            state["decision_id"],
            status="executed",
            executed_at=now.replace(tzinfo=None),
            after_snapshot=snapshot.audit_dict(),
        )
        guard_token = state.get('switch_guard_token')
        if guard_token and decision is not None:
            try:
                self.action_guard.finish(self.server_number, candidate['player_id'],
                                         guard_token, 'confirmed', expected=1)
            except Exception:
                logger.exception('Could not record confirmed switch; reservation retained')
        elif guard_token:
            logger.error('Confirmed switch decision is unavailable; reservation retained')
        self.store.arm_player(None)
        send_message(
            self.rcon,
            candidate["player_id"],
            config,
            "switch_completed",
            target_team=snapshot.team_labels.get(
                state["target_team"], str(state["target_team"]).capitalize()
            ),
            cooldown_maps=config.cooldown_maps,
        )
        executed_count = int(state.get("executed_count", 0)) + 1
        if (
            abs(snapshot.difference) <= config.target_difference
            or executed_count >= config.max_switches_per_incident
        ):
            return {
                "phase": Phase.COOLDOWN,
                "round_id": snapshot.round_id,
                "source_team": snapshot.larger_team,
                "target_team": snapshot.smaller_team,
                "executed_count": executed_count,
                "cooldown_started_at": now.timestamp(),
                "cooldown_until": now.timestamp() + config.stable_difference_seconds,
            }
        next_state = {
            "phase": Phase.PROPOSED,
            "round_id": snapshot.round_id,
            "incident_id": state.get("incident_id"),
            "source_team": snapshot.larger_team,
            "target_team": snapshot.smaller_team,
            "volunteers": state.get("volunteers") or [],
            "executed_count": executed_count,
        }
        return self._propose(next_state, snapshot, config, now)

    def _apply_events(
        self,
        state: dict[str, Any],
        events: list[dict[str, Any]],
        config: AutobalancerUserConfig,
        snapshot: BalanceSnapshot,
        now: datetime | None = None,
        *,
        defer_volunteers: bool = False,
        blocked: bool = False,
    ) -> dict[str, Any]:
        now = now or snapshot.captured_at
        state.pop("pending_volunteers", None)
        for event in events:
            if (
                event.get("type") == "approval"
                and state.get("phase") == Phase.PROPOSED
                and event.get("decision_id") == state.get("decision_id")
                and config.mode == "manual"
            ):
                state["approved_at"] = float(
                    event.get("approved_at") or snapshot.captured_at.timestamp()
                )
                state["approved_by"] = event.get("approved_by")
            elif (
                event.get("type") == "cancel"
                and event.get("incident_id")
                and event.get("incident_id")
                in {state.get("incident_id"), state.get("cancelled_incident_id")}
            ):
                if state.get("cancel_notification"):
                    self._notify_ended(
                        state["cancel_notification"], "Manuell abgebrochen"
                    )
                self._abort_state(
                    state, str(event.get("reason") or "Manuell abgebrochen")
                )
                self.store.arm_player(None)
                cancelled_at = float(
                    event.get("cancelled_at") or snapshot.captured_at.timestamp()
                )
                state = {
                    "phase": Phase.COOLDOWN,
                    "round_id": state.get("round_id"),
                    "cooldown_started_at": cancelled_at,
                    "cooldown_until": cancelled_at + config.stable_difference_seconds,
                    "cancelled_by": event.get("cancelled_by"),
                    "cancel_reason": event.get("reason"),
                }
            elif event.get("type") == "volunteer" and event.get("player_id"):
                self._register_volunteer(
                    state, event, config, snapshot, now, defer_volunteers, blocked
                )
            elif (
                event.get("type") == "team_switch"
                and state.get("phase") == Phase.VERIFYING
                and (
                    event.get("player_id")
                    == (state.get("candidate") or {}).get("player_id")
                    or (
                        event.get("player_name")
                        and str(event["player_name"]).strip().casefold()
                        == str((state.get("candidate") or {}).get("player_name") or "")
                        .strip()
                        .casefold()
                    )
                )
            ):
                state["team_switch_seen"] = True
        return state

    def _register_volunteer(
        self,
        state: dict[str, Any],
        event: dict[str, Any],
        config: AutobalancerUserConfig,
        snapshot: BalanceSnapshot,
        now: datetime,
        defer: bool,
        blocked: bool,
    ) -> None:
        if not fresh_command(event, now.timestamp()):
            return
        player_id = event["player_id"]
        if snapshot.seeding_active:
            send_message(self.rcon, player_id, config, "seeding")
            return
        timestamp = event_seconds(event)
        until = float(state.get("volunteer_until", 0))
        started = float(
            state.get("volunteer_started_at", until - config.volunteer_phase_seconds)
        )
        if (
            config.mode not in {"manual", "auto"}
            or state.get("phase") != Phase.VOLUNTEER
            or not state.get("incident_id")
            or event.get("incident_id") != state.get("incident_id")
        ):
            send_message(
                self.rcon,
                player_id,
                config,
                closed_key(config.mode, state),
                manual=True,
            )
            return
        if not started <= timestamp < until:
            send_message(
                self.rcon,
                player_id,
                config,
                "expired",
            )
            return
        if defer:
            # One pending command per player, with its original incident/deadline.
            pending = state.setdefault("pending_volunteers", {})
            pending.setdefault(player_id, event)
            return
        if blocked or self._hard_blocks(snapshot, config):
            send_message(
                self.rcon,
                player_id,
                config,
                "blocked",
            )
            return
        player = next((p for p in snapshot.players if p.player_id == player_id), None)
        reason = None
        if player is None or player.team != state.get("source_team"):
            reason = "wrong_team"
        elif protection_tier(player)[0] is None:
            reason = "commander"
        elif player.connected_seconds < config.connection_grace_seconds:
            reason = "connection"
        elif not config.allow_individual_squad_fallback and player.unit_size > 1:
            reason = "squad"
        elif player_id in self._cooldown_ids(snapshot, config):
            reason = "cooldown"
        if reason:
            send_message(self.rcon, player_id, config, reason)
            return
        volunteers = set(state.get("volunteers") or [])
        already_registered = player_id in volunteers
        volunteers.add(player_id)
        state["volunteers"] = sorted(volunteers)
        send_message(
            self.rcon,
            player_id,
            config,
            "registered" if already_registered else "volunteer_registered",
            manual=True,
        )

    def _abort_state(self, state: dict[str, Any], reason: str) -> None:
        if state.get("incident_id"):
            logger.info(
                "Autobalancer incident %s ended in %s: %s",
                state["incident_id"],
                state.get("phase"),
                reason,
            )
        if state.get("decision_id"):
            self.repository.update(
                state["decision_id"],
                status="aborted",
                reason={
                    "abort_reason": reason,
                    "selection": (state.get("candidate") or {}).get("reason"),
                    "plan": state.get("plan"),
                    "strategies": state.get("strategy_plans"),
                },
            )
        self._notify_ended(state, reason)

    def _notify_ended(self, state: dict[str, Any], reason: str) -> None:
        if state.get("mode") != "shadow" and not state.get("abort_notified"):
            recipients = set(state.get("volunteers") or []) | set(
                state.get("pending_volunteers") or {}
            )
            if state.get("phase") in {Phase.ARMED, Phase.VERIFYING} and (
                state.get("candidate") or {}
            ).get("player_id"):
                recipients.add(state["candidate"]["player_id"])
            state["abort_notified"] = True
            for player_id in sorted(recipients):
                send_message(
                    self.rcon,
                    player_id,
                    getattr(self, "_feedback_config", None) or AutobalancerUserConfig(),
                    (
                        "uncertain"
                        if state.get("phase") == Phase.VERIFYING
                        or reason == "Teamwechsel wurde nicht bestätigt"
                        else "ended"
                    ),
                )

    def _status(
        self,
        state: dict[str, Any],
        snapshot: BalanceSnapshot,
        config: AutobalancerUserConfig,
        hard_blocks: list[str],
        warnings: list[str],
    ) -> dict[str, Any]:
        confidences = [
            player.rating.confidence
            for player in snapshot.players
            if player.rating.role_family != "commander"
        ]
        team_confidences = {
            team: [
                player.rating.confidence
                for player in snapshot.players
                if player.team == team and player.rating.role_family != "commander"
            ]
            for team in ("allies", "axis")
        }
        required_switch_count = max(
            0,
            (abs(snapshot.difference) - config.target_difference + 1) // 2,
        )
        strength_swaps = (
            build_strength_swap_recommendations(
                snapshot,
                connection_grace_seconds=config.connection_grace_seconds,
                skill_gap_soft_limit=config.skill_gap_soft_limit,
                skill_gap_min_improvement=config.skill_gap_min_improvement,
                allow_individual_squad_fallback=config.allow_individual_squad_fallback,
            )
            if not hard_blocks and required_switch_count == 0
            else []
        )
        return {
            "mode": config.mode,
            "phase": (
                Phase.BLOCKED
                if "data_pause_started_at" in state
                else state.get("phase", Phase.IDLE)
            ),
            "paused_phase": (
                state.get("phase") if "data_pause_started_at" in state else None
            ),
            "volunteer_until": state.get("volunteer_until"),
            "incident_id": state.get("incident_id"),
            "decision_id": state.get("decision_id"),
            "round_id": snapshot.round_id,
            "team_counts": snapshot.team_counts,
            "team_labels": dict(snapshot.team_labels),
            "team_difference": snapshot.difference,
            "target_difference": config.target_difference,
            "required_switches": required_switch_count,
            "team_ratings": {
                "allies": round(team_rating(snapshot.players, "allies"), 2),
                "axis": round(team_rating(snapshot.players, "axis"), 2),
            },
            "team_rating_confidence": {
                team: round(
                    sum(values) / len(values) if values else 0.0,
                    3,
                )
                for team, values in team_confidences.items()
            },
            "rating_model_version": RATING_MODEL_VERSION,
            "strategy": config.skill_strategy,
            "strength_thresholds": {
                "soft_limit": config.skill_gap_soft_limit,
                "hard_warning": config.skill_gap_hard_warning,
                "minimum_improvement": config.skill_gap_min_improvement,
            },
            "strength_swap": (
                strength_swaps[0].public_dict() if strength_swaps else None
            ),
            "strength_swap_alternatives": [
                recommendation.public_dict() for recommendation in strength_swaps[1:]
            ],
            "data_confidence": round(
                sum(confidences) / len(confidences) if confidences else 0.0, 3
            ),
            "volunteers": state.get("volunteers") or [],
            "proposal": state.get("candidate"),
            "plan": state.get("plan"),
            "strategy_plans": state.get("strategy_plans"),
            "block_reasons": hard_blocks + (state.get("block_reasons") or []),
            "warnings": warnings,
            "native_autobalance": {
                "enabled": snapshot.native_autobalance_enabled,
                "threshold": snapshot.native_autobalance_threshold,
            },
            "updated_at": snapshot.captured_at.isoformat(),
        }


def run(stop_event: threading.Event | None = None) -> None:
    AutobalancerService().run(stop_event=stop_event)
