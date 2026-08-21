"""Dependency-free validation helpers for deployment configuration."""

from __future__ import annotations

import os
from urllib.parse import urlparse


def read_bool_env(name: str, default: bool = False) -> bool:
    """Read an environment flag without treating arbitrary strings as truthy."""

    value = os.getenv(name)
    if value is None or not value.strip():
        return default

    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"{name} must be one of 1/0, true/false, yes/no or on/off.")


def load_secret(*, test_mode: bool) -> str:
    """Return the configured secret or reject non-test startup without one."""

    secret = os.getenv("RCONWEB_API_SECRET", "").strip()
    if not secret:
        if test_mode:
            return "test-only-rconweb-secret-not-for-production"
        raise ValueError("RCONWEB_API_SECRET must be set for every non-test RCON deployment.")
    if len(secret) < 32:
        raise ValueError("RCONWEB_API_SECRET must contain at least 32 characters.")
    return secret


def normalize_cors_origin(origin: str, *, allow_insecure: bool) -> str:
    """Validate one browser origin used with credentialed CORS requests."""

    parsed = urlparse(origin.strip())
    if (
        parsed.scheme not in {"https", "http"}
        or not parsed.netloc
        or parsed.path not in {"", "/"}
        or parsed.params
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError(
            "CORS_ALLOWED_ORIGINS entries must be complete origins without a path, "
            "query or fragment."
        )
    if parsed.scheme == "http" and not allow_insecure:
        raise ValueError(
            "CORS_ALLOWED_ORIGINS may only contain HTTPS origins outside Django DEBUG."
        )
    return f"{parsed.scheme}://{parsed.netloc}"
