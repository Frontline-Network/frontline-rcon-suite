"""Generic incident settings with backwards-compatible Mobile Admin fallbacks."""

from __future__ import annotations

import os

TRUE_VALUES = {"1", "true", "yes", "on", "enabled"}


def _enabled(name: str, fallback: str | None = None) -> bool:
    value = os.getenv(name)
    if value is None and fallback:
        value = os.getenv(fallback)
    return str(value or "").strip().lower() in TRUE_VALUES


def incident_capture_enabled() -> bool:
    """Capture incidents whenever any incident consumer is enabled."""

    return any(
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
    raw = os.getenv("INCIDENT_TRIGGERS")
    if raw is None:
        raw = os.getenv("MOBILE_INCIDENT_TRIGGERS", "")
    return tuple(
        dict.fromkeys(item.strip().lower() for item in raw.split(",") if item.strip())
    )


def incident_context_mode() -> str:
    raw = (
        os.getenv("INCIDENT_CONTEXT_MODE", os.getenv("MOBILE_CONTEXT_V2", "disabled"))
        .strip()
        .lower()
    )
    if raw in TRUE_VALUES:
        return "enabled"
    if raw == "shadow":
        return "shadow"
    return "disabled"


def incident_context_fuzzy_threshold(default: float = 0.74) -> float:
    raw = os.getenv(
        "INCIDENT_CONTEXT_FUZZY_THRESHOLD",
        os.getenv("MOBILE_CONTEXT_FUZZY_THRESHOLD", str(default)),
    )
    try:
        value = float(raw)
    except (TypeError, ValueError):
        value = default
    return max(0.0, min(value, 1.0))


def incident_retention_days(default: int = 90) -> int:
    raw = os.getenv(
        "INCIDENT_RETENTION_DAYS",
        os.getenv("MOBILE_INCIDENT_RETENTION_DAYS", str(default)),
    )
    try:
        return max(1, min(int(raw), 3650))
    except (TypeError, ValueError):
        return default
