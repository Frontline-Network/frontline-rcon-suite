from __future__ import annotations

import base64
import hashlib
import hmac

from cryptography.fernet import Fernet

from .config import get_settings


def digest(value: str, purpose: str) -> str:
    return hmac.new(
        get_settings().secret.encode("utf-8"),
        f"{purpose}:{value}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def matches(value: str, expected: str, purpose: str) -> bool:
    return bool(value and expected) and hmac.compare_digest(
        digest(value, purpose), expected
    )


def derive_capability(identifier: str, purpose: str) -> str:
    """Derive a retry-stable, installation-scoped pseudorandom capability."""

    material = hmac.new(
        get_settings().secret.encode("utf-8"),
        f"derive:{purpose}:{identifier}".encode("utf-8"),
        hashlib.sha384,
    ).hexdigest()
    return f"{purpose}_{material}"


def _fernet() -> Fernet:
    key = hashlib.sha256(
        f"action-capability:{get_settings().secret}".encode("utf-8")
    ).digest()
    return Fernet(base64.urlsafe_b64encode(key))


def encrypt(value: str) -> str:
    return _fernet().encrypt(value.encode("utf-8")).decode("ascii")


def decrypt(value: str) -> str:
    return _fernet().decrypt(value.encode("ascii")).decode("utf-8")
