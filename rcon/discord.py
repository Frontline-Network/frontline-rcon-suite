import hashlib
import json
import logging
import re
from datetime import datetime, timezone
from functools import lru_cache
from typing import Any, List, Type

import requests
from discord_webhook import DiscordWebhook
from pydantic import HttpUrl

from discord.utils import escape_markdown
from rcon.user_config.rcon_server_settings import RconServerSettingsUserConfig
from rcon.user_config.utils import (
    DISCORD_AUDIT_FORMAT,
    BaseUserConfig,
    mask_sensitive_data,
)
from rcon.user_config.webhooks import (
    AuditWebhooksUserConfig,
    CameraWebhooksUserConfig,
    WatchlistWebhooksUserConfig,
)
from rcon.cache_utils import get_redis_client
from rcon.utils import dict_differences, get_server_number
from rcon.webhook_service import (
    enqueue_message,
    WebhookMessage,
    WebhookType,
    WebhookMessageType,
)


@lru_cache
def parse_webhook_url(url):
    """Parse and check validity of Discord webhook URL
    by performing a get request and checking existence
    of 'id' and 'token' in the JSON response.
    """
    if not url:
        return None, None
    diagnostic, payload = _probe_chat_webhook(str(url))
    _store_chat_webhook_diagnostic(str(url), diagnostic)
    if diagnostic["status"] != "valid":
        logger.warning(
            "Discord webhook rejected during initialization: %s",
            diagnostic.get("last_error"),
        )
        return None, None

    if not payload:
        return None, None
    return payload.get("id"), payload.get("token")


logger = logging.getLogger(__name__)

DISCORD_WEBHOOK_TIMEOUT_SECONDS = 10
CHAT_WEBHOOK_DIAGNOSTIC_PREFIX = "discord:chat_webhook_diagnostic"
CHAT_WEBHOOK_DIAGNOSTIC_TTL_SECONDS = 60 * 60 * 24 * 30


def _webhook_diagnostic_key(webhook_url: str) -> str:
    # Do not use the webhook URL (which includes Discord's capability token)
    # in Redis keys, logs, API results, or diagnostic records.
    fingerprint = hashlib.sha256(webhook_url.encode("utf-8")).hexdigest()
    return f"{CHAT_WEBHOOK_DIAGNOSTIC_PREFIX}:{fingerprint}"


def _diagnostic_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _store_chat_webhook_diagnostic(webhook_url: str, result: dict[str, Any]) -> None:
    try:
        get_redis_client().setex(
            _webhook_diagnostic_key(webhook_url),
            CHAT_WEBHOOK_DIAGNOSTIC_TTL_SECONDS,
            json.dumps(result),
        )
    except Exception:
        # Diagnostics must never break normal game-chat delivery.
        logger.warning("Could not persist Discord chat-webhook diagnostic", exc_info=True)


def _probe_chat_webhook(webhook_url: str) -> tuple[dict[str, Any], dict[str, Any] | None]:
    """Return a safe diagnostic and the private Discord response payload."""
    result: dict[str, Any] = {"status": "unreachable", "checked_at": _diagnostic_now()}
    response_payload: dict[str, Any] | None = None
    try:
        response = requests.get(webhook_url, timeout=DISCORD_WEBHOOK_TIMEOUT_SECONDS)
    except requests.Timeout:
        result["last_error"] = "Discord did not respond before the timeout."
    except requests.RequestException:
        result["last_error"] = "Discord could not be reached."
    else:
        if response.status_code == 200:
            try:
                response_payload = response.json()
            except ValueError:
                result["last_error"] = "Discord returned an invalid webhook response."
            else:
                if response_payload.get("id") and response_payload.get("token"):
                    result["status"] = "valid"
                    result["last_error"] = None
                else:
                    result["status"] = "invalid"
                    result["last_error"] = "Discord did not recognise this webhook."
        elif response.status_code in {401, 403, 404}:
            result["status"] = "invalid"
            result["last_error"] = "Discord rejected this webhook (removed or invalid)."
        else:
            result["last_error"] = (
                f"Discord returned HTTP {response.status_code} while checking the webhook."
            )

    return result, response_payload


def probe_chat_webhook(webhook_url: str) -> dict[str, Any]:
    """Check a configured Discord webhook without posting a message.

    Returned diagnostics intentionally contain no URL, response body, or token.
    They can therefore be shown to an administrator without exposing the
    webhook capability outside the configuration editor.
    """
    result, _ = _probe_chat_webhook(webhook_url)
    _store_chat_webhook_diagnostic(webhook_url, result)
    return result


def get_chat_webhook_diagnostics(webhook_urls: list[str]) -> list[dict[str, Any]]:
    """Return persisted safe diagnostics in the same order as configured hooks."""
    try:
        red = get_redis_client()
        diagnostics = []
        for index, webhook_url in enumerate(webhook_urls):
            raw = red.get(_webhook_diagnostic_key(webhook_url))
            if isinstance(raw, bytes):
                raw = raw.decode("utf-8")
            diagnostic = json.loads(raw) if raw else {"status": "unverified"}
            diagnostics.append({"index": index, **diagnostic})
        return diagnostics
    except Exception:
        logger.warning("Could not read Discord chat-webhook diagnostics", exc_info=True)
        return [{"index": index, "status": "unverified"} for index in range(len(webhook_urls))]


def diagnose_chat_webhooks(webhook_urls: list[str]) -> list[dict[str, Any]]:
    return [
        {"index": index, **probe_chat_webhook(webhook_url)}
        for index, webhook_url in enumerate(webhook_urls)
    ]


def test_chat_webhook(webhook_url: str) -> dict[str, Any]:
    """Deliver a neutral, non-mentioning diagnostic message to one webhook."""
    result = probe_chat_webhook(webhook_url)
    if result["status"] != "valid":
        return result

    try:
        response = requests.post(
            webhook_url,
            json={
                "username": "CRCON Diagnostics",
                "content": "CRCON chat-webhook test: delivery is working.",
                "allowed_mentions": {"parse": []},
            },
            timeout=DISCORD_WEBHOOK_TIMEOUT_SECONDS,
        )
    except requests.Timeout:
        result.update(status="unreachable", last_error="Discord timed out delivering the test message.")
    except requests.RequestException:
        result.update(status="unreachable", last_error="Discord could not deliver the test message.")
    else:
        if response.status_code not in {200, 204}:
            result.update(
                status="invalid" if response.status_code in {401, 403, 404} else "unreachable",
                last_error=f"Discord returned HTTP {response.status_code} while delivering the test message.",
            )
        else:
            result.update(status="valid", last_error=None, test_message_delivered=True)

    result["checked_at"] = _diagnostic_now()
    _store_chat_webhook_diagnostic(webhook_url, result)
    return result


def make_hook(webhook_url) -> DiscordWebhook | None:
    webhook_id, webhook_token = parse_webhook_url(webhook_url)
    if not all([webhook_id, webhook_token]):
        return None

    # Keep webhook delivery from blocking the caller indefinitely.
    return DiscordWebhook(
        url=str(webhook_url), timeout=DISCORD_WEBHOOK_TIMEOUT_SECONDS
    )


def make_allowed_mentions(user_ids, role_ids):
    allowed_mentions = {}
    for r in user_ids + role_ids:
        if match := re.fullmatch(r"<@!?(\d+)>", r):
            allowed_mentions.setdefault("users", []).append(match.group(1))
        if match := re.fullmatch(r"<@&(\d+)>", r):
            allowed_mentions.setdefault("roles", []).append(match.group(1))
        if r == "@everyone" or r == "@here":
            allowed_mentions["parse"] = r.replace("@", "")
    # allowed_mentions = {"parse": ["users"]}
    return allowed_mentions


def get_prepared_discord_hooks(
    hook_type: Type[CameraWebhooksUserConfig | WatchlistWebhooksUserConfig],
) -> List[DiscordWebhook]:
    hooks = hook_type.load_from_db().hooks

    return [
        DiscordWebhook(
            url=str(hook.url),
            allowed_mentions=make_allowed_mentions(
                hook.user_mentions, hook.role_mentions
            ),
            content=" ".join(
                [v for v in hook.user_mentions] + [v for v in hook.role_mentions]
            ),
        )
        for hook in hooks
    ]


def dict_to_discord(d):
    return "   ".join([f"{k}: `{v}`" for k, v in d.items()])


def audit_user_config_differences(
    old_model: dict[str, Any] | BaseUserConfig,
    new_model: dict[str, Any] | BaseUserConfig,
    command_name,
    author,
):
    if isinstance(old_model, BaseUserConfig):
        old_model = old_model.model_dump()
    if isinstance(new_model, BaseUserConfig):
        new_model = new_model.model_dump()

    differences = dict_differences(old_model, new_model)
    mask_sensitive_data(differences)
    message = DISCORD_AUDIT_FORMAT.format(differences=str(differences))
    send_to_discord_audit(
        message=message,
        command_name=command_name,
        by=author,
        md_escape_message=False,
    )


def send_to_discord_audit(
    message: str,
    command_name: str,
    by: str | None = None,
    silent=True,
    webhookurls: list[HttpUrl | None] | None = None,
    md_escape_message: bool = True,
    md_escape_author: bool = True,
    flatten: bool = True,
):
    by = by or "CRCON"
    config = None

    if webhookurls is None:
        config = AuditWebhooksUserConfig.load_from_db()
        webhookurls = [hook.url for hook in config.hooks]

    server_config = RconServerSettingsUserConfig.load_from_db()

    # Flatten messages with newlines
    if flatten:
        message = message.replace("\n", " ")
    logger.info("Audit: [%s] %s, %s", by, command_name, message.replace("\n", " "))
    if not webhookurls:
        logger.debug("No webhooks set for audit log")
        return
    try:
        content = "[`{}`][`{}`]][**{}**] {}".format(
            server_config.short_name,
            command_name,
            escape_markdown(by) if md_escape_author else by,
            escape_markdown(message) if md_escape_message else message,
        )
        logger.info(f"send_to_discord_audit {content=}")
        # TODO: fix typing or set `by` to something besides None
        dh_webhooks = [
            DiscordWebhook(
                url=str(url),
                content=content,
            )
            for url in webhookurls
            if url
        ]

        for hook in dh_webhooks:
            enqueue_message(
                message=WebhookMessage(
                    payload=hook.json,
                    webhook_type=WebhookType.DISCORD,
                    message_type=WebhookMessageType.AUDIT,
                    server_number=int(get_server_number()),
                )
            )
    except:
        logger.exception("Can't send audit log")
        if not silent:
            raise
