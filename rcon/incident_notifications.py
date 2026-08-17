from __future__ import annotations

import json

from sqlalchemy import text as sql_text

from rcon.models import enter_session

DEFAULT_RECEIVED_TEMPLATE = "Dein Admin-Report ist eingegangen."


def notify_incident_reporter(
    rcon_api,
    incident: dict,
    *,
    message: str,
    by: str | None = None,
    save_message: bool | None = None,
) -> bool:
    """Send incident status only to the player who submitted the report.

    Keeping this routing in one helper prevents report subjects from ever being
    used as recipients when Discord actions update an incident.
    """

    reporter_id = str(incident.get("reporter_id") or "").strip()
    if not reporter_id or not message:
        return False

    kwargs = {
        "player_id": reporter_id,
        "message": message,
        "player_name": incident.get("reporter_name"),
    }
    if by is not None:
        kwargs["by"] = by
    if save_message is not None:
        kwargs["save_message"] = save_message
    rcon_api.message_player(**kwargs)
    return True


def received_reporter_template() -> str | None:
    """Read the UI-managed template without initializing Django in the log loop."""

    try:
        with enter_session() as session:
            row = (
                session.execute(
                    sql_text(
                        "SELECT enabled, reporter_templates "
                        "FROM api_discordreportintegration WHERE id = 1"
                    )
                )
                .mappings()
                .one_or_none()
            )
    except Exception:
        return None
    if not row or not row["enabled"]:
        return None
    templates = row["reporter_templates"] or {}
    if isinstance(templates, str):
        try:
            templates = json.loads(templates)
        except ValueError:
            templates = {}
    return str(templates.get("received") or DEFAULT_RECEIVED_TEMPLATE)[:500]
