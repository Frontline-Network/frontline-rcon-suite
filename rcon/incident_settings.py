"""Generic incident settings with backwards-compatible Mobile Admin fallbacks."""

from __future__ import annotations

import os

TRUE_VALUES = {"1", "true", "yes", "on", "enabled"}


def _value(name: str, fallback: str | None = None, default: str = "") -> str:
    """Return a setting while treating an empty Compose value as unset."""

    value = os.getenv(name)
    if (value is None or not value.strip()) and fallback:
        value = os.getenv(fallback)
    return str(value if value is not None else default).strip()


def _enabled(name: str, fallback: str | None = None) -> bool:
    return _value(name, fallback).lower() in TRUE_VALUES


def incident_capture_enabled() -> bool:
    """Capture incidents whenever any incident consumer is enabled."""

    from rcon.user_config.report_admin import ReportAdminUserConfig
    return ReportAdminUserConfig.load_from_db().enabled or any(
        (
            _enabled("INCIDENT_CAPTURE_ENABLED", "MOBILE_INTEGRATION_ENABLED"),
            _enabled("DISCORD_REPORTS_ENABLED"),
            _enabled("AI_MODERATION_ENABLED"),
        )
    )


def discord_reports_enabled() -> bool:
    return _enabled("DISCORD_REPORTS_ENABLED")


def ai_moderation_enabled() -> bool:
    return _enabled("AI_MODERATION_ENABLED")


def incident_triggers() -> tuple[str, ...]:
    raw = _value("INCIDENT_TRIGGERS", "MOBILE_INCIDENT_TRIGGERS")
    return tuple(
        dict.fromkeys(item.strip().lower() for item in raw.split(",") if item.strip())
    )


def incident_context_mode() -> str:
    raw = _value("INCIDENT_CONTEXT_MODE", "MOBILE_CONTEXT_V2", "disabled").lower()
    if raw in TRUE_VALUES:
        return "enabled"
    if raw == "shadow":
        return "shadow"
    return "disabled"


def incident_context_fuzzy_threshold(default: float = 0.74) -> float:
    raw = _value(
        "INCIDENT_CONTEXT_FUZZY_THRESHOLD",
        "MOBILE_CONTEXT_FUZZY_THRESHOLD",
        str(default),
    )
    try:
        value = float(raw)
    except (TypeError, ValueError):
        value = default
    return max(0.0, min(value, 1.0))


def incident_retention_days(default: int = 90) -> int:
    raw = _value(
        "INCIDENT_RETENTION_DAYS",
        "MOBILE_INCIDENT_RETENTION_DAYS",
        str(default),
    )
    try:
        return max(1, min(int(raw), 3650))
    except (TypeError, ValueError):
        return default
