import hashlib
import hmac
import json
import logging
import os
import re
import secrets
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import requests

from rcon.player_history import get_player_profile
from rcon.utils import get_server_number

logger = logging.getLogger(__name__)

VERIFY_COMMAND = re.compile(
    r"^\s*!vipverify\s+([A-Za-z0-9-]{16,24})\s*$", re.IGNORECASE
)
CODE_FORMAT = re.compile(r"^[A-Z0-9]{16}$")
_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="frontline-vip")
_pending_slots = threading.BoundedSemaphore(20)
_attempt_lock = threading.Lock()
_attempts: dict[str, list[float]] = {}

# This language is independent of the browser UI language, which belongs to
# each individual administrator. It only selects our built-in responses;
# messages returned by the verification service remain untouched.
_MESSAGES = {
    "de": {
        "unavailable": "Die Frontline-VIP-Verifizierung ist auf diesem Server noch nicht verfügbar.",
        "network_error": "Die VIP-Verifizierung ist momentan nicht erreichbar. Dein Code bleibt gültig; versuche es später erneut.",
        "success": "Dein FLN-Konto wurde erfolgreich mit diesem Spieler verknüpft.",
        "invalid_code": "Der VIP-Code ist ungültig oder wurde bereits eingelöst.",
        "invalid_command": "Ungültiger Befehl. Nutze: !vipverify DEIN-CODE-AUS-DEM-FLN-KONTO",
        "rate_limit": "Zu viele VIP-Prüfungen. Bitte warte einige Minuten und versuche es erneut.",
        "busy": "Die VIP-Verifizierung ist gerade ausgelastet. Dein Code bleibt gültig; versuche es gleich erneut.",
        "checking": "Dein VIP-Code wird geprüft …",
        "queue_error": "Die VIP-Verifizierung konnte nicht gestartet werden. Dein Code bleibt gültig.",
    },
    "en": {
        "unavailable": "Frontline VIP verification is not yet available on this server.",
        "network_error": "VIP verification is currently unavailable. Your code remains valid; please try again later.",
        "success": "Your FLN account has been linked to this player.",
        "invalid_code": "The VIP code is invalid or has already been redeemed.",
        "invalid_command": "Invalid command. Use: !vipverify YOUR-CODE-FROM-YOUR-FLN-ACCOUNT",
        "rate_limit": "Too many VIP verification attempts. Please wait a few minutes and try again.",
        "busy": "VIP verification is busy. Your code remains valid; please try again shortly.",
        "checking": "Your VIP code is being checked …",
        "queue_error": "VIP verification could not be started. Your code remains valid.",
    },
    "fr": {
        "unavailable": "La vérification VIP Frontline n'est pas encore disponible sur ce serveur.",
        "network_error": "La vérification VIP est momentanément indisponible. Votre code reste valide ; réessayez plus tard.",
        "success": "Votre compte FLN a été associé à ce joueur.",
        "invalid_code": "Le code VIP est invalide ou a déjà été utilisé.",
        "invalid_command": "Commande invalide. Utilisez : !vipverify VOTRE-CODE-DU-COMPTE-FLN",
        "rate_limit": "Trop de tentatives de vérification VIP. Patientez quelques minutes et réessayez.",
        "busy": "La vérification VIP est occupée. Votre code reste valide ; réessayez dans quelques instants.",
        "checking": "Vérification de votre code VIP en cours …",
        "queue_error": "La vérification VIP n'a pas pu démarrer. Votre code reste valide.",
    },
}


def _message(key: str) -> str:
    language = os.getenv("FRONTLINE_VIP_VERIFICATION_LANGUAGE", "de").strip().lower()
    return _MESSAGES.get(language, _MESSAGES["de"])[key]


def _normalize_code(value: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", value.upper())


def _detect_platform(player_id: str, profile: dict[str, Any] | None) -> str:
    if profile:
        soldier = profile.get("soldier") or {}
        platform = str(soldier.get("platform") or "").strip().lower()
        if platform:
            return platform.rsplit("::", 1)[-1]

    if len(player_id) == 17 and player_id.isdigit():
        return "steam"
    if len(player_id) == 32 and all(
        char in "0123456789abcdefABCDEF" for char in player_id
    ):
        return "eos"
    return "unknown"


def _game_name() -> str:
    return "hll_vietnam" if os.getenv("HLL_GAME", "hll").lower() == "hllv" else "hll"


def _signed_headers(secret: str, body: bytes) -> dict[str, str]:
    timestamp = str(int(time.time()))
    nonce = secrets.token_hex(16)
    signed_value = b"\n".join((timestamp.encode(), nonce.encode(), body))
    signature = hmac.new(secret.encode(), signed_value, hashlib.sha256).hexdigest()
    return {
        "Content-Type": "application/json",
        "X-FLN-Timestamp": timestamp,
        "X-FLN-Nonce": nonce,
        "X-FLN-Signature": signature,
    }


def _allow_attempt(player_id: str) -> bool:
    now = time.monotonic()
    cutoff = now - 600
    with _attempt_lock:
        recent = [
            attempt for attempt in _attempts.get(player_id, []) if attempt >= cutoff
        ]
        if len(recent) >= 5:
            _attempts[player_id] = recent
            return False
        recent.append(now)
        _attempts[player_id] = recent
        return True


def _message_player(rcon, player_id: str, message: str) -> None:
    try:
        rcon.message_player(player_id=player_id, message=message, save_message=False)
    except Exception:
        logger.exception("Unable to send Frontline VIP verification result to player")


def _redeem(rcon, player_id: str, player_name: str, code: str) -> None:
    url = os.getenv("FRONTLINE_VIP_REDEEM_URL", "").strip()
    secret = os.getenv("FRONTLINE_VIP_REDEEM_SECRET", "")
    if not url or len(secret) < 32:
        _message_player(
            rcon,
            player_id,
            _message("unavailable"),
        )
        return

    try:
        profile = get_player_profile(player_id, 0)
    except Exception:
        logger.exception("Unable to load player profile for Frontline VIP verification")
        profile = None

    payload = {
        "code": code,
        "player_id": player_id,
        "player_name": player_name,
        "platform": _detect_platform(player_id, profile),
        "game": _game_name(),
        "server": str(get_server_number()),
    }
    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode(
        "utf-8"
    )

    try:
        response = requests.post(
            url,
            data=body,
            headers=_signed_headers(secret, body),
            timeout=10,
        )
        response_payload = response.json() if response.content else {}
    except (requests.RequestException, ValueError):
        logger.exception("Frontline VIP verification endpoint request failed")
        _message_player(
            rcon,
            player_id,
            _message("network_error"),
        )
        return

    message = str(response_payload.get("message") or "").strip()
    if response.ok and response_payload.get("success"):
        _message_player(
            rcon,
            player_id,
            message or _message("success"),
        )
        return

    _message_player(
        rcon,
        player_id,
        message or _message("invalid_code"),
    )


def _redeem_with_slot(rcon, player_id: str, player_name: str, code: str) -> None:
    try:
        _redeem(rcon, player_id, player_name, code)
    finally:
        _pending_slots.release()


def handle_chat_verification(rcon, struct_log: dict[str, Any]) -> bool:
    message = str(struct_log.get("sub_content") or "")
    if "!vipverify" not in message.lower():
        return False

    player_id = str(struct_log.get("player_id_1") or "").strip()
    player_name = str(struct_log.get("player_name_1") or "").strip()
    if not player_id:
        return True

    match = VERIFY_COMMAND.match(message)
    code = _normalize_code(match.group(1)) if match else ""
    if not CODE_FORMAT.match(code):
        _message_player(
            rcon,
            player_id,
            _message("invalid_command"),
        )
        return True

    if not _allow_attempt(player_id):
        _message_player(
            rcon,
            player_id,
            _message("rate_limit"),
        )
        return True

    if not _pending_slots.acquire(blocking=False):
        _message_player(
            rcon,
            player_id,
            _message("busy"),
        )
        return True

    _message_player(rcon, player_id, _message("checking"))
    try:
        _executor.submit(_redeem_with_slot, rcon, player_id, player_name, code)
    except Exception:
        _pending_slots.release()
        logger.exception("Unable to queue Frontline VIP verification")
        _message_player(
            rcon,
            player_id,
            _message("queue_error"),
        )
    return True
