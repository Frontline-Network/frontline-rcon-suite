"""Bounded background model calls, separate from Discord delivery and RCON ticks."""

import logging
import time

import requests
from django.db import close_old_connections
from sqlalchemy import select

from api.discord_capabilities import decrypt_capability
from api.models import DiscordReportIntegration
from rcon import report_admin as admin, report_reason
from rcon.models import AdminIncidentEvent
from rcon.report_reason_contract import ReportReasonRequest, ReportReasonDecision

logger = logging.getLogger(__name__)


def process_one(http):
    integration = DiscordReportIntegration.objects.filter(pk=1, enabled=True).first()
    if (
        not integration
        or not integration.service_url
        or not integration.outbound_capability_ciphertext
    ):
        return False  # Runtime expiry makes this manual, never a rules fallback.
    with admin.enter_session() as sess:
        event_id = sess.scalar(
            select(AdminIncidentEvent.id)
            .where(
                AdminIncidentEvent.event_type == "report_admin",
                AdminIncidentEvent.payload["status"].as_string() == "classifying",
                AdminIncidentEvent.payload["reason_request"]["status"].as_string()
                == "pending",
            )
            .order_by(AdminIncidentEvent.id)
            .limit(1)
        )
    if event_id is None:
        return False
    with admin.enter_session() as sess:
        event = sess.get(AdminIncidentEvent, event_id)
        server = event.incident.server_number
        admin.votes.lock(sess, server)
        sess.refresh(event)
        sess.refresh(event.incident)
        if (
            event.payload.get("status") != "classifying"
            or event.payload["reason_request"]["status"] != "pending"
        ):
            return False
        if problem := report_reason.invalid_request(sess, event, time.time()):
            admin.publish(sess, event, "manual", problem)
            return True
        if not admin.delivered(sess, event.incident_id):
            return False
        ai = dict(integration.ai_config or {})
        provider = ai.get("provider")
        model = ai.get("ai_model")
        api_key = None
        if provider == "api_key" and integration.ai_api_key_ciphertext:
            api_key = decrypt_capability(integration.ai_api_key_ciphertext)
        if (
            provider not in {"api_key", "codex"}
            or not model
            or (provider == "api_key" and not api_key)
        ):
            admin.publish(
                sess, event, "manual", "KI-Anbindung fehlt / AI provider not configured"
            )
            return True
        request = event.payload["reason_request"]
        job = ReportReasonRequest(
            installation_id=str(integration.installation_id),
            incident_id=event.incident_id,
            server_number=server,
            message=event.incident.raw_message,
            roster=[
                {
                    "name": str(p.get("name") or p.get("player_name") or ""),
                    "team": admin._normalize_team(p.get("team")) or "",
                    "role": str(p.get("role") or ""),
                    "squad": str(p.get("unit_name") or ""),
                }
                for p in request["roster"]
            ],
            reporter_name=event.incident.reporter_name or "",
            reporter_team=event.payload["reporter_team"] or "",
            ai_provider=provider,
            ai_model=model,
            api_key=api_key,
        )
        # Commit the claim before calling the service: competing worker loops
        # and crashes cannot replay this paid request or its eventual outcome.
        event.payload = {
            **event.payload,
            "reason_request": {**request, "status": "sending"},
        }
    result = None
    try:
        response = http.post(
            integration.service_url.rstrip("/") + "/v1/report-reason",
            headers={
                "Authorization": "Bearer "
                + decrypt_capability(integration.outbound_capability_ciphertext)
            },
            json=job.model_dump(),
            timeout=(3, 25),
            allow_redirects=False,
        )
        response.raise_for_status()
        data = response.json()
        result = {
            "decision": ReportReasonDecision.model_validate(
                data["decision"]
            ).model_dump(),
            "model": str(data["model"])[:100],
            "prompt_version": str(data["prompt_version"])[:64],
        }
    except Exception as exc:
        # Do not expose keys, responses, prompts or player data in diagnostics.
        logger.warning("Report reason unavailable: %s", type(exc).__name__)
    with admin.enter_session() as sess:
        admin.votes.lock(sess, server)
        event = sess.get(AdminIncidentEvent, event_id)
        if not event or event.payload.get("status") != "classifying":
            return True  # Manual takeover/configuration wins over a late reply.
        if problem := report_reason.invalid_request(sess, event, time.time()):
            admin.publish(sess, event, "manual", problem)
            return True
        event.payload = {
            **event.payload,
            "reason_request": {
                **event.payload["reason_request"],
                "status": "done" if result else "failed",
                "analysis": result,
            },
        }
    return True


def run():
    with requests.Session() as http:
        while True:
            try:
                close_old_connections()
                busy = process_one(http)
            except Exception as exc:
                logger.warning("Report reason worker failed: %s", type(exc).__name__)
                busy = False
            finally:
                close_old_connections()
            time.sleep(0.5 if busy else 2)
