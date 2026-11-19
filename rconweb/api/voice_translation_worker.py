"""Warm fixed-message translations away from the game tick and Discord delivery."""

import logging
import time

import requests
from django.db import close_old_connections
from sqlalchemy import select

from api.discord_capabilities import decrypt_capability
from api.models import DiscordReportIntegration
from rcon.models import enter_session
from rcon.voice_language import VoiceTranslationCache
from rcon.voice_language_text import ENGLISH, VERSION, valid_templates

logger = logging.getLogger(__name__)


def process_one(http):
    now = time.time()
    with enter_session() as sess:
        row = sess.scalar(
            select(VoiceTranslationCache)
            .where(
                VoiceTranslationCache.version == VERSION,
                VoiceTranslationCache.next_attempt >= 0,
                VoiceTranslationCache.next_attempt <= now,
            )
            .order_by(
                VoiceTranslationCache.next_attempt, VoiceTranslationCache.language
            )
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        if row is None:
            return False
        language = row.language
        # Durable lease also limits retry costs for failed, timed-out or interrupted calls.
        row.next_attempt = now + 3600

    integration = DiscordReportIntegration.objects.filter(pk=1, enabled=True).first()
    if (
        not integration
        or not integration.outbound_capability_ciphertext
        or not integration.service_url
    ):
        return True
    config = integration.ai_config or {}
    provider, model = config.get("provider"), config.get("ai_model")
    if provider not in {"codex", "api_key"} or not model:
        return True
    key = None
    if provider == "api_key":
        if not integration.ai_api_key_ciphertext:
            return True
        key = decrypt_capability(integration.ai_api_key_ciphertext)
    reply = http.post(
        integration.service_url.rstrip("/") + "/v1/voice-translations",
        headers={
            "Authorization": "Bearer "
            + decrypt_capability(integration.outbound_capability_ciphertext)
        },
        json={
            "installation_id": str(integration.installation_id),
            "language": language,
            "texts": ENGLISH,
            "ai_provider": provider,
            "ai_model": model,
            "api_key": key,
        },
        timeout=(3, 135),
        allow_redirects=False,
    )
    if reply.status_code == 429:
        with enter_session() as sess:
            row = sess.get(VoiceTranslationCache, (language, VERSION))
            if row and row.next_attempt == now + 3600:
                row.next_attempt = time.time() + 60
        return True
    reply.raise_for_status()
    texts = reply.json().get("texts")
    if not valid_templates(texts):
        raise ValueError("invalid_voice_translation_catalog")
    with enter_session() as sess:
        row = sess.get(VoiceTranslationCache, (language, VERSION))
        if row and row.next_attempt == now + 3600:
            row.texts = texts
            row.next_attempt = -1
    return True


def run():
    with requests.Session() as http:
        while True:
            try:
                close_old_connections()
                active = process_one(http)
            except Exception as exc:
                # Never log report content, service URLs or credentials.
                logger.warning("Voice translation unavailable: %s", type(exc).__name__)
                active = False
            finally:
                close_old_connections()
            time.sleep(1 if active else 15)
