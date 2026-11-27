"""Private, best-effort feedback; a failed message must not reset balancing."""

from __future__ import annotations

import logging
import math

logger = logging.getLogger(__name__)
COMMAND_MAX_AGE_SECONDS = 60

MANUAL_NOTICE = (
    "Manueller Modus: Ein Admin muss den Wechsel freigeben. "
    "Der Befehl löst keinen sofortigen Teamwechsel aus."
)

# Do not forward arbitrary admin text, planner details or exception messages
# (which can contain player data or connection details) to game clients.
PUBLIC_ABORT_REASONS = {
    "Teams sind bereits ausgeglichen": "Die Teams sind bereits ausgeglichen",
    "Teamzählungen stimmen nicht überein": "Die Spielerzahlen konnten nicht sicher bestätigt werden",
    "Teamzählungen waren zu lange nicht verlässlich": "Die Spielerzahlen konnten nicht sicher bestätigt werden",
    "Autobalancer wurde deaktiviert": "Der Autobalancer wurde ausgeschaltet",
    "Betriebsart wurde geändert": "Der Betriebsmodus wurde geändert",
    "Kartenwechsel": "Die Karte hat gewechselt",
    "Matchwechsel": "Die Runde hat gewechselt",
    "Manuelle Freigabe ist abgelaufen": "Es gab keine rechtzeitige Admin-Freigabe",
    "Manuell abgebrochen": "Ein Admin hat den Aufruf beendet",
    "Kandidaten-Timeout": "Die Zeit für den angekündigten Wechsel ist abgelaufen",
    "Teamwechsel wurde nicht bestätigt": "Der Teamwechsel konnte nicht sicher bestätigt werden; bitte frage einen Admin",
    "Richtung des Ungleichgewichts hat gewechselt": "Jetzt benötigt das andere Team Unterstützung",
}


def ended_message(reason: str, *, switch_uncertain: bool = False) -> str:
    # Technical details belong in the admin audit, not a popup to every invitee.
    # Never promise an unchanged team after a switch may already have been sent.
    if switch_uncertain or reason == "Teamwechsel wurde nicht bestätigt":
        return (
            "Der Teamausgleich ist beendet. Bitte lass deinen Teamwechsel von einem Admin prüfen.\n"
            "Team balancing has ended. Please ask an admin to check your team switch."
        )
    return (
        "Der Teamausgleich wurde abgebrochen. Du bleibst in deinem Team.\n"
        "Team balancing was cancelled. You stay on your current team."
    )


def event_seconds(event: dict) -> float | None:
    try:
        value = float(event.get("timestamp_ms")) / 1000
    except (TypeError, ValueError, OverflowError):
        return None
    return value if math.isfinite(value) else None


def fresh_command(event: dict, now: float) -> bool:
    timestamp = event_seconds(event)
    return timestamp is not None and 0 <= now - timestamp <= COMMAND_MAX_AGE_SECONDS


def send_private(rcon, player_id: str | None, message: str) -> bool:
    if not player_id:
        return False
    try:
        from rcon.player_messages import localize_automated
        message = localize_automated(player_id, message, group='autobalancer')
        result = rcon.message_player(player_id, message=message)
        if result is False:
            logger.warning("Autobalancer private message was rejected")
            return False
        if result is not True:
            logger.warning("Autobalancer private message was not confirmed")
            return False
        return True
    except Exception:
        logger.exception("Unable to send autobalancer private message")
        return False


def closed_command_message(mode: str, state: dict) -> str:
    if mode == "disabled":
        return "Der Autobalancer ist ausgeschaltet. Es ist kein Wechsel vorgemerkt."
    if mode == "shadow":
        return "Der Autobalancer beobachtet nur (Shadow-Modus). Es erfolgt kein Teamwechsel."
    if state.get("phase") in {"proposed", "armed", "verifying"}:
        message = "Die Freiwilligenphase ist beendet."
        if mode == "manual" and state.get("phase") == "proposed":
            return f"{message} Der Vorschlag wartet auf einen Admin. {MANUAL_NOTICE}"
        return f"{message} Ein Wechsel wird bereits vorbereitet oder geprüft."
    message = (
        "Aktuell ist kein Aufruf für Freiwillige offen. "
        "Bitte warte auf eine neue Einladung zum Teamausgleich."
    )
    return f"{message} {MANUAL_NOTICE}" if mode == "manual" else message
