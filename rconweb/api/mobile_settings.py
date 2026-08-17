"""Lightweight Mobile Admin settings shared by HTTP and background workers."""

from __future__ import annotations

import os
import uuid

from django.conf import settings


def mobile_integration_enabled() -> bool:
    return os.getenv("MOBILE_INTEGRATION_ENABLED", "false").lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def mobile_installation_id() -> str:
    configured = os.getenv("MOBILE_INSTALLATION_ID")
    if configured:
        return configured
    database_name = os.getenv("HLL_DB_NAME", "rcon")
    return str(
        uuid.uuid5(
            uuid.NAMESPACE_URL,
            f"crcon:{settings.SECRET_KEY}:{database_name}",
        )
    )
