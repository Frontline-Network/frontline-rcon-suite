from __future__ import annotations

from collections import Counter
from datetime import datetime
from typing import Any

from sqlalchemy import func, select

from rcon.models import AutobalanceDecision, Maps, enter_session


def _shadow_decision_summary(decision: dict[str, Any]) -> dict[str, Any]:
    snapshot = decision.get("before_snapshot") or {}
    reason = decision.get("reason") or {}
    plan = reason.get("plan") or {}
    players = snapshot.get("players") or []
    player = next(
        (
            item
            for item in players
            if item.get("player_id") == decision.get("player_id")
        ),
        {},
    )
    allies = snapshot.get("allies_count")
    axis = snapshot.get("axis_count")
    warnings: list[str] = []
    if not snapshot.get("counts_match", False):
        warnings.append("Teamzählungen stimmten im Snapshot nicht überein")
    if snapshot.get("fail_count", 0) != 0:
        warnings.append("Snapshot enthielt fehlgeschlagene Datenabfragen")
    if not snapshot.get("stable_map", False):
        warnings.append("Kartendaten waren nicht stabil")
    if not player:
        warnings.append("Kandidat fehlt im gespeicherten Snapshot")
    else:
        role = str(player.get("role") or "").replace(" ", "").lower()
        unit_type = str(player.get("unit_type") or "").lower()
        if role in {"armycommander", "commander"} or unit_type == "commander":
            warnings.append("Commander wurde als Kandidat vorgeschlagen")
        if player.get("team") != decision.get("source_team"):
            warnings.append("Kandidat war nicht im gespeicherten Quellteam")
    if isinstance(allies, int) and isinstance(axis, int) and allies != axis:
        expected_source = "allies" if allies > axis else "axis"
        if decision.get("source_team") != expected_source:
            warnings.append("Quellteam war nicht das größere Team")

    candidate_plan = next(
        (
            item
            for item in (plan.get("candidates") or [])
            if item.get("player_id") == decision.get("player_id")
        ),
        {},
    )
    difference = (
        abs(allies - axis)
        if isinstance(allies, int) and isinstance(axis, int)
        else None
    )
    return {
        "decision_id": decision.get("decision_id"),
        "incident_id": decision.get("incident_id"),
        "round_id": decision.get("round_id"),
        "created_at": decision.get("created_at"),
        "map_name": snapshot.get("map_name"),
        "allies_count": allies,
        "axis_count": axis,
        "difference": difference,
        "source_team": decision.get("source_team"),
        "target_team": decision.get("target_team"),
        "player_name": decision.get("player_name"),
        "volunteer": bool(decision.get("volunteer")),
        "protection_tier": decision.get("protection_tier"),
        "rating": decision.get("rating"),
        "rating_confidence": decision.get("rating_confidence"),
        "selection_reason": reason.get("selection"),
        "required_switches": plan.get("required_switches"),
        "projected_rating_gap": candidate_plan.get("projected_rating_gap"),
        "unit_name": player.get("unit_name"),
        "unit_type": player.get("unit_type"),
        "unit_size": player.get("unit_size"),
        "role": player.get("role"),
        "is_leader": player.get("is_leader"),
        "connected_seconds": player.get("connected_seconds"),
        "squad_seconds": player.get("squad_seconds"),
        "review_verdict": decision.get("review_verdict"),
        "review_category": decision.get("review_category"),
        "review_comment": decision.get("review_comment"),
        "reviewed_by": decision.get("reviewed_by"),
        "reviewed_at": decision.get("reviewed_at"),
        "audit_warnings": warnings,
    }


def summarize_shadow_decisions(
    decisions: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build a compact, privacy-conscious dashboard payload from audit records."""
    items = [_shadow_decision_summary(decision) for decision in decisions]
    reviewed = [
        item
        for item in items
        if item["review_verdict"] in {"accepted", "rejected"}
    ]
    accepted = sum(item["review_verdict"] == "accepted" for item in reviewed)
    rejected = len(reviewed) - accepted
    acceptance_rate = accepted / len(reviewed) if reviewed else None
    round_ids = {item["round_id"] for item in items if item["round_id"]}
    reviewed_round_ids = {
        item["round_id"] for item in reviewed if item["round_id"]
    }
    tier_counts = Counter(
        str(item["protection_tier"])
        for item in items
        if item["protection_tier"] is not None
    )
    rejection_categories = Counter(
        item["review_category"]
        for item in reviewed
        if item["review_verdict"] == "rejected" and item["review_category"]
    )
    confidences = [
        float(item["rating_confidence"])
        for item in items
        if item["rating_confidence"] is not None
    ]
    rule_warning_proposals = sum(bool(item["audit_warnings"]) for item in items)
    goals = {
        "reviewed_rounds_target": 10,
        "acceptance_rate_target": 0.9,
        "reviewed_rounds_met": len(reviewed_round_ids) >= 10,
        "acceptance_rate_met": acceptance_rate is not None
        and acceptance_rate >= 0.9,
        "hard_rules_clean": rule_warning_proposals == 0,
    }
    goals["ready_for_manual"] = all(
        (
            goals["reviewed_rounds_met"],
            goals["acceptance_rate_met"],
            goals["hard_rules_clean"],
        )
    )
    return {
        "summary": {
            "proposals": len(items),
            "reviewed": len(reviewed),
            "pending_review": len(items) - len(reviewed),
            "accepted": accepted,
            "rejected": rejected,
            "acceptance_rate": acceptance_rate,
            "rounds_observed": len(round_ids),
            "reviewed_rounds": len(reviewed_round_ids),
            "average_rating_confidence": (
                sum(confidences) / len(confidences) if confidences else None
            ),
            "rule_warning_proposals": rule_warning_proposals,
            "protection_tiers": dict(sorted(tier_counts.items())),
            "rejection_categories": dict(rejection_categories.most_common()),
        },
        "pilot_goals": goals,
        "decisions": items,
    }


class DecisionRepository:
    def __init__(self, server_number: int):
        self.server_number = server_number

    def create(self, values: dict[str, Any]) -> dict[str, Any]:
        decision = AutobalanceDecision(server_number=self.server_number, **values)
        with enter_session() as session:
            session.add(decision)
            session.flush()
            result = decision.to_dict()
        return result

    def update(self, decision_id: str, **values: Any) -> dict[str, Any] | None:
        with enter_session() as session:
            decision = session.scalar(
                select(AutobalanceDecision).where(
                    AutobalanceDecision.decision_id == decision_id,
                    AutobalanceDecision.server_number == self.server_number,
                )
            )
            if decision is None:
                return None
            for key, value in values.items():
                setattr(decision, key, value)
            decision.updated_at = datetime.utcnow()
            session.flush()
            return decision.to_dict()

    def abort_unfinished(self, reason: str) -> int:
        unfinished = {"proposed", "approved", "armed", "executing", "verifying"}
        changed = 0
        with enter_session() as session:
            decisions = session.scalars(
                select(AutobalanceDecision).where(
                    AutobalanceDecision.server_number == self.server_number,
                    AutobalanceDecision.status.in_(unfinished),
                )
            ).all()
            for decision in decisions:
                decision.status = "aborted"
                decision.updated_at = datetime.utcnow()
                decision.reason = {**(decision.reason or {}), "abort_reason": reason}
                changed += 1
        return changed

    def history(
        self,
        limit: int = 100,
        round_id: str | None = None,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        query = select(AutobalanceDecision).where(
            AutobalanceDecision.server_number == self.server_number
        )
        if round_id:
            query = query.where(AutobalanceDecision.round_id == round_id)
        if status:
            query = query.where(AutobalanceDecision.status == status)
        query = query.order_by(AutobalanceDecision.created_at.desc()).limit(
            min(max(1, limit), 500)
        )
        with enter_session() as session:
            return [decision.to_dict() for decision in session.scalars(query).all()]

    def shadow_overview(
        self, limit: int = 200, round_id: str | None = None
    ) -> dict[str, Any]:
        query = select(AutobalanceDecision).where(
            AutobalanceDecision.server_number == self.server_number,
            AutobalanceDecision.mode == "shadow",
        )
        if round_id:
            query = query.where(AutobalanceDecision.round_id == round_id)
        query = query.order_by(AutobalanceDecision.created_at.desc()).limit(
            min(max(1, limit), 500)
        )
        with enter_session() as session:
            decisions = [
                decision.to_dict() for decision in session.scalars(query).all()
            ]
        return summarize_shadow_decisions(decisions)

    def review_shadow_decision(
        self,
        decision_id: str,
        verdict: str,
        category: str | None,
        comment: str | None,
        reviewed_by: str,
    ) -> dict[str, Any] | None:
        with enter_session() as session:
            decision = session.scalar(
                select(AutobalanceDecision).where(
                    AutobalanceDecision.decision_id == decision_id,
                    AutobalanceDecision.server_number == self.server_number,
                    AutobalanceDecision.mode == "shadow",
                )
            )
            if decision is None:
                return None
            decision.review_verdict = verdict
            decision.review_category = category
            decision.review_comment = comment
            decision.reviewed_by = reviewed_by
            decision.reviewed_at = datetime.utcnow()
            decision.updated_at = datetime.utcnow()
            session.flush()
            return _shadow_decision_summary(decision.to_dict())

    def cooldown_player_ids(
        self, cooldown_maps: int, current_round_started_at: datetime
    ) -> set[str]:
        if cooldown_maps <= 0:
            return set()
        with enter_session() as session:
            last_switches = session.execute(
                select(
                    AutobalanceDecision.player_id,
                    func.max(AutobalanceDecision.round_started_at),
                )
                .where(
                    AutobalanceDecision.server_number == self.server_number,
                    AutobalanceDecision.status == "executed",
                    AutobalanceDecision.player_id.is_not(None),
                )
                .group_by(AutobalanceDecision.player_id)
            ).all()
            protected: set[str] = set()
            for player_id, switched_round in last_switches:
                completed_rounds = (
                    session.scalar(
                        select(func.count(Maps.id)).where(
                            Maps.server_number == self.server_number,
                            Maps.start > switched_round,
                            Maps.start < current_round_started_at,
                            Maps.end.is_not(None),
                        )
                    )
                    or 0
                )
                if completed_rounds < cooldown_maps:
                    protected.add(player_id)
            return protected
