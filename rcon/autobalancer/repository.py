from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import func, select

from rcon.models import AutobalanceDecision, Maps, enter_session


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
