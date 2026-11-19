"""Deliver private state changes independently of game ticks and moderator messages."""

import logging
import time
from datetime import datetime, timedelta, timezone

import requests
from django.db import close_old_connections
from sqlalchemy import select
from sqlalchemy.orm import aliased

from api.discord_capabilities import decrypt_capability
from api.models import DiscordReportIntegration
from rcon.models import AdminIncidentEvent, enter_session
from rcon.voice_language import render
from rcon.voice_player_delivery import answer_actions
from rcon.voice_player_store import VoicePlayerDelivery

logger = logging.getLogger(__name__)


def deliver_one(http):
    now = datetime.now(timezone.utc)
    with enter_session() as sess:
        prior = aliased(VoicePlayerDelivery)
        earlier = (
            select(prior.id)
            .where(
                prior.incident_id == VoicePlayerDelivery.incident_id,
                prior.discord_id == VoicePlayerDelivery.discord_id,
                prior.id < VoicePlayerDelivery.id,
                prior.done.is_(False),
            )
            .exists()
        )
        row = sess.scalar(
            select(VoicePlayerDelivery)
            .where(
                VoicePlayerDelivery.done.is_(False),
                VoicePlayerDelivery.due <= now,
                ~earlier,
            )
            .order_by(VoicePlayerDelivery.id)
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        if not row:
            return False
        p = row.payload
        fields = {
            "incident_id": row.incident_id,
            "server_number": p["server_number"],
            "discord_user_id": row.discord_id,
            "send_dm": p["send_dm"],
            "actions": [],
        }
        if p["question"]:
            event = sess.scalar(
                select(AdminIncidentEvent).where(
                    AdminIncidentEvent.incident_id == row.incident_id,
                    AdminIncidentEvent.event_type == "report_admin",
                )
            )
            voice = (event.payload if event else {}).get("voice") or {}
            if (
                voice.get("phase") != "awaiting_answer"
                or (voice.get("deadline") or 0) <= time.time()
            ):
                row.done = True
                return True
            fields["actions"] = answer_actions(sess, row.incident_id, p["locale"])
        fields["content"] = render(
            sess, p["key"], p["locale"], target=p["target"], case=row.incident_id[:8]
        )
        row.attempts += 1
        row.due = now + timedelta(seconds=min(300, 15 * row.attempts))
        job_id = row.id
    integration = DiscordReportIntegration.objects.filter(pk=1, enabled=True).first()
    if not integration or not integration.outbound_capability_ciphertext:
        return False
    fields["installation_id"] = str(integration.installation_id)
    r = http.post(
        integration.service_url.rstrip("/") + "/v1/player-notifications",
        headers={
            "Authorization": "Bearer "
            + decrypt_capability(integration.outbound_capability_ciphertext),
            "Idempotency-Key": f"voice:{integration.installation_id}:{job_id}",
        },
        json=fields,
        allow_redirects=False,
        timeout=(3, 8),
    )
    r.raise_for_status()
    receipt = r.json()
    if receipt.get("accepted") is not True:
        raise ValueError("Unconfirmed player notification")
    with enter_session() as sess:
        row = sess.get(VoicePlayerDelivery, job_id)
        if row and receipt.get("retry_ephemeral") is True:
            row.due = datetime.now(timezone.utc) + timedelta(
                seconds=min(30, 2 * row.attempts)
            )
        elif (
            row
            and receipt.get("delivery") == "disabled"
            and row.kind == "notice"
            and row.attempts < 3
        ):
            row.due = datetime.now(timezone.utc) + timedelta(seconds=2)
        elif row:
            row.done = True
    return True


def run():
    with requests.Session() as http:
        while True:
            try:
                close_old_connections()
                active = deliver_one(http)
            except Exception as exc:
                logger.warning(
                    "Private voice report update unavailable: %s", type(exc).__name__
                )
                active = False
            finally:
                close_old_connections()
            time.sleep(0.25 if active else 2)
