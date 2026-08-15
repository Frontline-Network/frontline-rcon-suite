from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, text as sql_text

from rcon.admin_incidents import create_incident
from rcon.incident_settings import ai_moderation_enabled
from rcon.models import (
    AdminIncident,
    AdminIncidentEvent,
    ModerationAnalysisRecord,
    ModerationCandidateOutbox,
    PlayerNameModerationState,
    enter_session,
)
from rcon.moderation import (
    ModerationAnalysis,
    ModerationPolicy,
    ModerationSource,
    analysis_visibility,
    normalize_candidate,
    prefilter_candidate,
    validate_analysis_policy,
)
from rcon.utils import get_server_number


def _json_value(value, fallback):
    if isinstance(value, type(fallback)):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, type(fallback)) else fallback
        except ValueError:
            return fallback
    return fallback


def runtime_moderation_config() -> tuple[dict, ModerationPolicy] | None:
    """Read the UI-managed policy without initializing Django in supervisors."""

    if not ai_moderation_enabled():
        return None
    try:
        with enter_session() as session:
            row = (
                session.execute(
                    sql_text(
                        "SELECT enabled, ai_config, policy "
                        "FROM api_discordreportintegration WHERE id = 1"
                    )
                )
                .mappings()
                .one_or_none()
            )
    except Exception:
        row = None
    if row and row["enabled"]:
        return (
            _json_value(row["ai_config"], {}),
            ModerationPolicy.model_validate(_json_value(row["policy"], {})),
        )
    raw_policy = os.getenv("AI_MODERATION_POLICY_JSON", "").strip()
    if not raw_policy:
        return None
    return (
        {
            "chat_enabled": True,
            "names_enabled": True,
            "shadow_mode": True,
        },
        ModerationPolicy.model_validate_json(raw_policy),
    )


def player_name_state_is_current(
    state: PlayerNameModerationState | None,
    *,
    normalized_name: str,
    model_version: str,
    policy: ModerationPolicy,
) -> bool:
    """Return whether this exact identity state has already been queued."""

    return bool(
        state
        and state.normalized_name == normalized_name
        and state.model_version == model_version
        and state.policy_profile_id == policy.profile_id
        and state.policy_version == policy.version
    )


def enqueue_candidate(
    *,
    source: ModerationSource,
    candidate_text: str,
    player_id: str | None,
    player_name: str | None,
) -> tuple[str, bool] | None:
    config = runtime_moderation_config()
    if config is None:
        return None
    ai_config, policy = config
    enabled_key = "chat_enabled" if source == ModerationSource.CHAT else "names_enabled"
    if not ai_config.get(enabled_key) or source not in policy.enabled_sources:
        return None
    if source == ModerationSource.PLAYER_NAME and not player_id:
        # A stable identity is required to detect a real name change. Scanning
        # anonymous log fragments repeatedly would waste tokens.
        return None
    prefilter = prefilter_candidate(candidate_text, policy)
    if source == ModerationSource.CHAT and not prefilter.suspicious:
        return None
    normalized = normalize_candidate(candidate_text)
    model_version = (
        os.getenv("AI_PLAYER_NAME_MODEL", "gpt-5-nano")
        if source == ModerationSource.PLAYER_NAME
        else os.getenv("AI_MODERATION_MODEL", "gpt-5.6-luna")
    )
    fingerprint = hashlib.sha256(
        (
            f"{source.value}:{player_id or ''}:{normalized}:"
            f"{model_version}:{policy.profile_id}:{policy.version}"
        ).encode("utf-8")
    ).hexdigest()
    now = datetime.now(tz=timezone.utc)
    with enter_session() as session:
        if source == ModerationSource.PLAYER_NAME:
            state = session.get(PlayerNameModerationState, player_id)
            if player_name_state_is_current(
                state,
                normalized_name=normalized,
                model_version=model_version,
                policy=policy,
            ):
                return state.candidate_fingerprint, False
        else:
            dedupe_since = now - timedelta(minutes=5)
            existing = session.execute(
                select(ModerationCandidateOutbox).where(
                    ModerationCandidateOutbox.candidate_fingerprint == fingerprint,
                    ModerationCandidateOutbox.created_at >= dedupe_since,
                )
            ).scalar_one_or_none()
            if existing:
                return existing.id, False
        item = ModerationCandidateOutbox(
            source=source.value,
            server_number=int(get_server_number()),
            player_id=(player_id or "")[:100] or None,
            player_name=(player_name or "")[:255] or None,
            candidate_text=candidate_text[:4000],
            candidate_fingerprint=fingerprint,
            matched_rule_ids=prefilter.matched_rule_ids,
            policy=policy.model_dump(mode="json"),
            shadow_only=bool(ai_config.get("shadow_mode", True)),
            next_attempt_at=now,
            created_at=now,
        )
        session.add(item)
        if source == ModerationSource.PLAYER_NAME:
            if state is None:
                state = PlayerNameModerationState(player_id=player_id)
                session.add(state)
            state.normalized_name = normalized[:255]
            state.model_version = model_version
            state.policy_profile_id = policy.profile_id
            state.policy_version = policy.version
            state.candidate_fingerprint = fingerprint
            state.checked_at = now
        session.flush()
        return item.id, True


def persist_candidate_analysis(
    *, analysis_id: str, job_id: str, analysis: ModerationAnalysis
) -> tuple[dict | None, str, bool]:
    with enter_session() as session:
        existing = session.get(ModerationAnalysisRecord, analysis_id)
        if existing:
            return None, existing.visibility, False
        job = session.get(ModerationCandidateOutbox, job_id)
        if job is None:
            raise ValueError("Moderation job not found")
        policy = ModerationPolicy.model_validate(job.policy)
        validate_analysis_policy(
            analysis, policy, expected_source=ModerationSource(job.source)
        )
        visibility = analysis_visibility(analysis, policy)
        if job.shadow_only and visibility == "incident":
            visibility = "shadow"
        payload = {
            "source": job.source,
            "server_number": job.server_number,
            "player_id": job.player_id,
            "player_name": job.player_name,
            "candidate_text": job.candidate_text,
            "fingerprint": job.candidate_fingerprint,
            "policy": job.policy,
        }
    incident = None
    if visibility == "incident":
        subjects = []
        if payload["player_id"] and payload["player_name"]:
            subjects.append(
                {
                    "kind": "player",
                    "state": "confirmed",
                    "is_primary": True,
                    "display_name": payload["player_name"],
                    "player_id": payload["player_id"],
                    "confidence": 1.0,
                    "match_method": "ai_candidate",
                    "parser_version": analysis.prompt_version,
                    "snapshot": {},
                }
            )
        incident, _ = create_incident(
            server_number=payload["server_number"],
            source=payload["source"],
            reason=(
                f"Verdächtiger Spielername: {payload['candidate_text']}"
                if payload["source"] == ModerationSource.PLAYER_NAME.value
                else payload["candidate_text"]
            ),
            raw_message=payload["candidate_text"],
            actor="system:ai",
            target_id=payload["player_id"],
            target_name=payload["player_name"],
            subjects=subjects,
            idempotency_key=f"ai-job:{job_id}"[:64],
        )
    now = datetime.now(tz=timezone.utc)
    with enter_session() as session:
        job = session.get(ModerationCandidateOutbox, job_id)
        session.add(
            ModerationAnalysisRecord(
                id=analysis_id,
                incident_id=incident["id"] if incident else None,
                source=analysis.source.value,
                player_id=job.player_id,
                candidate_fingerprint=job.candidate_fingerprint,
                candidate_text=job.candidate_text,
                analysis=analysis.model_dump(mode="json"),
                visibility=visibility,
                model_version=analysis.model_version,
                prompt_version=analysis.prompt_version,
                policy_profile_id=analysis.policy_profile_id,
                policy_version=analysis.policy_version,
                dedupe_until=None,
                created_at=now,
            )
        )
        job.analysis_received_at = now
        if incident:
            stored_incident = session.get(AdminIncident, incident["id"])
            stored_incident.revision += 1
            stored_incident.updated_at = now
            stored_incident.events.append(
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
        if incident:
            incident = stored_incident.to_dict(include_events=True)
    return incident, visibility, True
