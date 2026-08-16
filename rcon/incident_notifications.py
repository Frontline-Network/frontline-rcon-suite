from __future__ import annotations

import json

from sqlalchemy import text as sql_text

from rcon.models import enter_session

DEFAULT_RECEIVED_TEMPLATE = "Dein Admin-Report ist eingegangen."


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
