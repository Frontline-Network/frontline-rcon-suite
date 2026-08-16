"""Capability primitives for CRCON <-> Frontline Discord communication."""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings


def new_capability(prefix: str) -> str:
    return f"{prefix}_{secrets.token_urlsafe(48)}"


def capability_digest(value: str) -> str:
    return hmac.new(
        settings.SECRET_KEY.encode("utf-8"),
        f"discord-capability:{value}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def capability_matches(value: str, expected_digest: str) -> bool:
    return bool(value and expected_digest) and hmac.compare_digest(
        capability_digest(value), expected_digest
    )


def _fernet() -> Fernet:
    key = hashlib.sha256(
        f"discord-outbound:{settings.SECRET_KEY}".encode("utf-8")
    ).digest()
    return Fernet(base64.urlsafe_b64encode(key))


def encrypt_capability(value: str) -> bytes:
    return _fernet().encrypt(value.encode("utf-8"))


def decrypt_capability(value: bytes | memoryview) -> str:
    try:
        return _fernet().decrypt(bytes(value)).decode("utf-8")
    except InvalidToken as exc:
        raise ValueError("Stored Discord capability cannot be decrypted") from exc
