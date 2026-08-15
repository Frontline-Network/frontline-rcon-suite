"""Reliable CRCON incident outbox for the centrally hosted Discord service."""

from __future__ import annotations

import os
import time
from datetime import datetime, timedelta, timezone

import requests
from django.core.management.base import BaseCommand
from sqlalchemy import and_, or_, select

from api.discord_capabilities import decrypt_capability
from api.models import DiscordReportIntegration
from rcon.incident_settings import ai_moderation_enabled, discord_reports_enabled
from rcon.models import (
    AdminIncidentDiscordDelivery,
    AdminIncidentEvent,
    ModerationAnalysisRecord,
    ModerationCandidateOutbox,
    enter_session,
)
from rcon.moderation import (
    IncidentEventEnvelope,
    ModerationAnalysis,
    ModerationAnalysisJobEnvelope,
)


def _server_label(server_number: int) -> tuple[str, str]:
    suffix = "" if server_number == 1 else f"_{server_number}"
    name = os.getenv(f"HLL_SERVER_NAME{suffix}") or f"CRCON Server {server_number}"
    raw_game = (os.getenv(f"HLL_GAME{suffix}") or "hll").strip().lower()
    game = "hll_vietnam" if raw_game in {"hllv", "hll_vietnam", "vietnam"} else "hll"
    return name[:255], game


class Command(BaseCommand):
    help = "Deliver complete incident events to the Frontline Discord service"

    def handle(self, *args, **options):
        self.stdout.write("CRCON Discord report worker started")
        while True:
            try:
                delivered = self._deliver_batch()
            except Exception as exc:
                # Never include payloads or capabilities in worker logs.
                self.stderr.write(
                    f"Discord outbox iteration failed: {type(exc).__name__}"
                )
                delivered = 0
            time.sleep(0.25 if delivered else 1.0)

    def _deliver_batch(self) -> int:
        if not discord_reports_enabled():
            return 0
        integration = DiscordReportIntegration.objects.filter(
            pk=1, enabled=True
        ).first()
        if (
            integration is None
            or not integration.service_url
            or not integration.outbound_capability_ciphertext
        ):
            return 0
        capability = decrypt_capability(integration.outbound_capability_ciphertext)
        now = datetime.now(tz=timezone.utc)
        delivery_started_at = integration.delivery_started_at
        if delivery_started_at is None:
            # Safe upgrade path for installations paired before the cut-over
            # field existed: do not replay their complete incident history.
            integration.delivery_started_at = now
            integration.save(update_fields=["delivery_started_at", "updated_at"])
            return 0
        delivered_count = 0
        with enter_session() as session:
            rows = session.execute(
                select(AdminIncidentEvent, AdminIncidentDiscordDelivery)
                .outerjoin(
                    AdminIncidentDiscordDelivery,
                    AdminIncidentDiscordDelivery.event_id == AdminIncidentEvent.id,
                )
                .where(
                    AdminIncidentEvent.created_at >= delivery_started_at,
                    AdminIncidentEvent.event_type != "action_started",
                    or_(
                        AdminIncidentDiscordDelivery.id.is_(None),
                        and_(
                            AdminIncidentDiscordDelivery.delivered_at.is_(None),
                            AdminIncidentDiscordDelivery.next_attempt_at <= now,
                        ),
                    ),
                )
                .order_by(AdminIncidentEvent.id.asc())
                .limit(50)
            ).all()
            for event, delivery in rows:
                if delivery is None:
                    delivery = AdminIncidentDiscordDelivery(
                        event_id=event.id, next_attempt_at=now
                    )
                    session.add(delivery)
                    session.flush()
                incident = event.incident
                analysis_record = session.execute(
                    select(ModerationAnalysisRecord)
                    .where(ModerationAnalysisRecord.incident_id == incident.id)
                    .order_by(ModerationAnalysisRecord.created_at.desc())
                    .limit(1)
                ).scalar_one_or_none()
                server_name, game = _server_label(incident.server_number)
                analysis = None
                if analysis_record:
                    analysis = ModerationAnalysis.model_validate(
                        analysis_record.analysis
                    )
                incident_payload = incident.to_dict(include_events=True)
                incident_payload["moderation_policy"] = integration.policy or {}
                ai_config = dict(integration.ai_config or {})
                if not ai_moderation_enabled():
                    ai_config.update(
                        reports_enabled=False,
                        chat_enabled=False,
                        names_enabled=False,
                    )
                incident_payload["ai_config"] = ai_config
                incident_payload["discord_language"] = integration.language
                incident_payload["allowed_actions"] = integration.allowed_actions or []
                if analysis_record:
                    incident_payload["analysis_id"] = analysis_record.id
                envelope = IncidentEventEnvelope(
                    installation_id=str(integration.installation_id),
                    event_id=event.id,
                    event_type=event.event_type,
                    incident_id=incident.id,
                    incident_revision=incident.revision,
                    occurred_at=event.created_at,
                    server_number=incident.server_number,
                    server_name=server_name,
                    game=game,
                    incident=incident_payload,
                    analysis=analysis,
                )
                try:
                    response = requests.post(
                        f"{integration.service_url.rstrip('/')}/v1/events",
                        headers={
                            "Authorization": f"Bearer {capability}",
                            "Idempotency-Key": (
                                f"{integration.installation_id}:{event.id}"
                            ),
                        },
                        json=envelope.model_dump(mode="json"),
                        timeout=10,
                    )
                    response.raise_for_status()
                except requests.RequestException as exc:
                    delivery.attempts += 1
                    delivery.last_error = (
                        f"{type(exc).__name__}:status="
                        f"{getattr(exc.response, 'status_code', None)}"
                    )[:500]
                    delivery.next_attempt_at = now + timedelta(
                        seconds=min(300, 2 ** min(delivery.attempts, 8))
                    )
                else:
                    delivery.attempts += 1
                    delivery.delivered_at = now
                    delivery.last_error = None
                    delivered_count += 1
                delivery.updated_at = now
                session.flush()
            if not ai_moderation_enabled():
                return delivered_count
            candidates = session.execute(
                select(ModerationCandidateOutbox)
                .where(
                    ModerationCandidateOutbox.delivered_at.is_(None),
                    ModerationCandidateOutbox.next_attempt_at <= now,
                )
                .order_by(ModerationCandidateOutbox.created_at.asc())
                .limit(50)
            ).scalars()
            for candidate in candidates:
                job = ModerationAnalysisJobEnvelope(
                    installation_id=str(integration.installation_id),
                    job_id=candidate.id,
                    source=candidate.source,
                    server_number=candidate.server_number,
                    player_id=candidate.player_id,
                    player_name=candidate.player_name,
                    candidate_text=candidate.candidate_text,
                    matched_rule_ids=candidate.matched_rule_ids,
                    policy=candidate.policy,
                    shadow_only=candidate.shadow_only,
                    created_at=candidate.created_at,
                )
                try:
                    response = requests.post(
                        f"{integration.service_url.rstrip('/')}/v1/analysis-jobs",
                        headers={
                            "Authorization": f"Bearer {capability}",
                            "Idempotency-Key": (
                                f"{integration.installation_id}:analysis:{candidate.id}"
                            ),
                        },
                        json=job.model_dump(mode="json"),
                        timeout=20,
                    )
                    response.raise_for_status()
                except requests.RequestException as exc:
                    candidate.attempts += 1
                    candidate.last_error = (
                        f"{type(exc).__name__}:status="
                        f"{getattr(exc.response, 'status_code', None)}"
                    )[:500]
                    candidate.next_attempt_at = now + timedelta(
                        seconds=min(300, 2 ** min(candidate.attempts, 8))
                    )
                else:
                    candidate.attempts += 1
                    candidate.delivered_at = now
                    candidate.last_error = None
                    delivered_count += 1
                session.flush()
        return delivered_count
