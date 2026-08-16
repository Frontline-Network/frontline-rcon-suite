import os
from unittest.mock import patch

os.environ.setdefault("SERVER_NUMBER", "1")
os.environ.setdefault("HLL_MAINTENANCE_CONTAINER", "1")

from rcon.incident_settings import (
    incident_capture_enabled,
    incident_context_mode,
    incident_retention_days,
    incident_triggers,
)


def test_generic_incident_settings_fall_back_to_mobile_values():
    with patch.dict(
        "os.environ",
        {
            "MOBILE_INTEGRATION_ENABLED": "true",
            "MOBILE_INCIDENT_TRIGGERS": "!admin, @admin",
            "MOBILE_CONTEXT_V2": "shadow",
            "MOBILE_INCIDENT_RETENTION_DAYS": "45",
        },
        clear=True,
    ):
        assert incident_capture_enabled()
        assert incident_triggers() == ("!admin", "@admin")
        assert incident_context_mode() == "shadow"
        assert incident_retention_days() == 45


def test_discord_or_ai_can_enable_capture_without_mobile_app():
    with patch.dict("os.environ", {"DISCORD_REPORTS_ENABLED": "true"}, clear=True):
        assert incident_capture_enabled()
    with patch.dict("os.environ", {"AI_MODERATION_ENABLED": "true"}, clear=True):
        assert incident_capture_enabled()


def test_generic_values_override_legacy_values():
    with patch.dict(
        "os.environ",
        {
            "INCIDENT_TRIGGERS": "!help",
            "MOBILE_INCIDENT_TRIGGERS": "!admin",
            "INCIDENT_CONTEXT_MODE": "enabled",
            "MOBILE_CONTEXT_V2": "disabled",
        },
        clear=True,
    ):
        assert incident_triggers() == ("!help",)
        assert incident_context_mode() == "enabled"
