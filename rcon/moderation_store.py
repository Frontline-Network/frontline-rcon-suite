from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select

from rcon.models import (
    AdminIncident,
    AdminIncidentEvent,
    ModerationAnalysisRecord,
    enter_session,
)
from rcon.moderation import (
    ModerationAnalysis,
    ModerationPolicy,
    analysis_visibility,
    validate_analysis_policy,
)


def persist_analysis(
    *,
    analysis_id: str,
    incident_id: str,
    analysis: ModerationAnalysis,
    policy: ModerationPolicy,
    candidate_text: str | None = None,
    player_id: str | None = None,
) -> tuple[dict, bool]:
    validate_analysis_policy(analysis, policy)
    visibility = analysis_visibility(analysis, policy)
    now = datetime.now(tz=timezone.utc)
    fingerprint = hashlib.sha256(
        f"{analysis.source.value}:{player_id or ''}:{candidate_text or incident_id}".encode(
            "utf-8"
        )
    ).hexdigest()
    with enter_session() as session:
        existing = session.get(ModerationAnalysisRecord, analysis_id)
        if existing:
            incident = session.get(AdminIncident, existing.incident_id)
            return incident.to_dict(include_events=True), False
        incident = session.execute(
            select(AdminIncident)
            .where(AdminIncident.id == incident_id)
            .with_for_update()
        ).scalar_one_or_none()
        if incident is None:
            raise ValueError("Incident not found")
        record = ModerationAnalysisRecord(
            id=str(uuid.UUID(analysis_id)),
            incident_id=incident.id,
            source=analysis.source.value,
            player_id=player_id,
            candidate_fingerprint=fingerprint,
            candidate_text=(candidate_text or "")[:4000] or None,
            analysis=analysis.model_dump(mode="json"),
            visibility=visibility,
            model_version=analysis.model_version,
            prompt_version=analysis.prompt_version,
            policy_profile_id=analysis.policy_profile_id,
            policy_version=analysis.policy_version,
            dedupe_until=(
                now + timedelta(hours=24)
                if analysis.source.value == "ai_player_name"
                else None
            ),
            created_at=now,
        )
        session.add(record)
        incident.revision += 1
        incident.updated_at = now
        incident.events.append(
            AdminIncidentEvent(
                actor="system:ai",
                event_type="analysis_updated",
                idempotency_key=f"analysis:{analysis_id}"[:64],
                payload={
                    "analysis_id": analysis_id,
                    "risk_score": analysis.risk_score,
                    "suggested_action": analysis.suggested_action.value,
                    "visibility": visibility,
                },
                created_at=now,
            )
        )
        session.flush()
        return incident.to_dict(include_events=True), True


def purge_shadow_reviews(retention_days: int = 30) -> int:
    cutoff = datetime.now(tz=timezone.utc) - timedelta(days=max(1, retention_days))
    with enter_session() as session:
        result = session.execute(
            delete(ModerationAnalysisRecord).where(
                ModerationAnalysisRecord.visibility.in_({"shadow", "ignore"}),
                ModerationAnalysisRecord.created_at < cutoff,
            )
        )
        return int(result.rowcount or 0)
