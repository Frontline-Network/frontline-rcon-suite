from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any


class Mode(StrEnum):
    DISABLED = "disabled"
    SHADOW = "shadow"
    MANUAL = "manual"
    AUTO = "auto"


class Phase(StrEnum):
    IDLE = "idle"
    OBSERVING = "observing"
    VOLUNTEER = "volunteer"
    PROPOSED = "proposed"
    ARMED = "armed"
    VERIFYING = "verifying"
    COOLDOWN = "cooldown"
    BLOCKED = "blocked"


@dataclass(slots=True)
class SkillRating:
    version: str = "legacy"
    value: float = 50.0
    raw_value: float = 50.0
    confidence: float = 0.0
    role_family: str = "combat_infantry"
    level_component: float = 50.0
    history_component: float = 50.0
    live_component: float = 50.0
    history_seconds: int = 0
    history_maps: int = 0
    history_source: str = "none"

    def asdict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class PlayerSnapshot:
    player_id: str
    name: str
    team: str
    role: str = ""
    level: int | None = None
    unit_id: int | str | None = None
    unit_name: str | None = None
    unit_type: str | None = None
    unit_size: int = 0
    is_leader: bool = False
    connected_seconds: int = 0
    squad_seconds: int = 0
    map_playtime_seconds: int = 0
    kills: int = 0
    combat: int = 0
    offense: int = 0
    defense: int = 0
    support: int = 0
    deaths: int = 0
    teamkills: int = 0
    rating: SkillRating = field(default_factory=SkillRating)

    @property
    def squad_key(self) -> str | None:
        if self.unit_id is None and not self.unit_name:
            return None
        return f"{self.team}:{self.unit_id or self.unit_name}"


@dataclass(slots=True)
class BalanceSnapshot:
    round_id: str
    captured_at: datetime
    map_name: str
    map_elapsed_seconds: int
    time_remaining_seconds: int
    allies_count: int
    axis_count: int
    players: list[PlayerSnapshot]
    game: str = "hll"
    fail_count: int = 0
    counts_match: bool = True
    stable_map: bool = True
    native_autobalance_enabled: bool | None = None
    native_autobalance_threshold: int | None = None
    team_labels: dict[str, str] = field(
        default_factory=lambda: {"allies": "Allies", "axis": "Axis"}
    )

    @property
    def team_counts(self) -> dict[str, int]:
        return {"allies": self.allies_count, "axis": self.axis_count}

    @property
    def difference(self) -> int:
        return self.allies_count - self.axis_count

    @property
    def larger_team(self) -> str | None:
        if self.difference > 0:
            return "allies"
        if self.difference < 0:
            return "axis"
        return None

    @property
    def smaller_team(self) -> str | None:
        if self.difference > 0:
            return "axis"
        if self.difference < 0:
            return "allies"
        return None

    def public_dict(self) -> dict[str, Any]:
        return {
            "round_id": self.round_id,
            "captured_at": self.captured_at.isoformat(),
            "map_name": self.map_name,
            "game": self.game,
            "map_elapsed_seconds": self.map_elapsed_seconds,
            "time_remaining_seconds": self.time_remaining_seconds,
            "allies_count": self.allies_count,
            "axis_count": self.axis_count,
            "fail_count": self.fail_count,
            "counts_match": self.counts_match,
            "stable_map": self.stable_map,
            "team_labels": dict(self.team_labels),
        }

    def audit_dict(self) -> dict[str, Any]:
        """Detailed immutable evidence used to review a balancing decision."""
        return {
            **self.public_dict(),
            "native_autobalance_enabled": self.native_autobalance_enabled,
            "native_autobalance_threshold": self.native_autobalance_threshold,
            "players": [
                {
                    "player_id": player.player_id,
                    "name": player.name,
                    "team": player.team,
                    "role": player.role,
                    "level": player.level,
                    "unit_id": player.unit_id,
                    "unit_name": player.unit_name,
                    "unit_type": player.unit_type,
                    "unit_size": player.unit_size,
                    "is_leader": player.is_leader,
                    "connected_seconds": player.connected_seconds,
                    "squad_seconds": player.squad_seconds,
                    "map_playtime_seconds": player.map_playtime_seconds,
                    "kills": player.kills,
                    "deaths": player.deaths,
                    "teamkills": player.teamkills,
                    "combat": player.combat,
                    "offense": player.offense,
                    "defense": player.defense,
                    "support": player.support,
                    "rating": player.rating.asdict(),
                }
                for player in self.players
            ],
        }


@dataclass(slots=True)
class Candidate:
    player: PlayerSnapshot
    base_tier: int
    effective_tier: int
    volunteer: bool
    projected_rating_gap: float
    reason: str

    def public_dict(self) -> dict[str, Any]:
        return {
            "player_id": self.player.player_id,
            "player_name": self.player.name,
            "team": self.player.team,
            "unit_name": self.player.unit_name,
            "unit_type": self.player.unit_type,
            "base_tier": self.base_tier,
            "effective_tier": self.effective_tier,
            "volunteer": self.volunteer,
            "rating": round(self.player.rating.value, 2),
            "rating_confidence": round(self.player.rating.confidence, 3),
            "projected_rating_gap": round(self.projected_rating_gap, 2),
            "reason": self.reason,
        }


@dataclass(slots=True)
class BalancePlan:
    source_team: str
    target_team: str
    required_switches: int
    candidates: list[Candidate]
    blocked_reasons: list[str] = field(default_factory=list)
    strategy: str = "squad-first"
    rating_gap_before: float = 0.0
    projected_rating_gap: float = 0.0
    warnings: list[str] = field(default_factory=list)

    def public_dict(self) -> dict[str, Any]:
        return {
            "source_team": self.source_team,
            "target_team": self.target_team,
            "required_switches": self.required_switches,
            "candidates": [candidate.public_dict() for candidate in self.candidates],
            "blocked_reasons": self.blocked_reasons,
            "strategy": self.strategy,
            "rating_gap_before": round(self.rating_gap_before, 2),
            "projected_rating_gap": round(self.projected_rating_gap, 2),
            "warnings": self.warnings,
        }


def utcnow() -> datetime:
    return datetime.now(timezone.utc)
