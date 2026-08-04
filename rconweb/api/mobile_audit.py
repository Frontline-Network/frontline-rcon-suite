import json
import logging
from typing import Any

from rcon.models import AuditLog, enter_session
from rcon.utils import get_server_number

logger = logging.getLogger("rconweb")

_SENSITIVE_KEY_PARTS = (
    "token",
    "secret",
    "password",
    "push_handle",
    "push_capability",
    "verification_code",
    "qr_payload",
)


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            str(key): _sanitize(item)
            for key, item in value.items()
            if not any(part in str(key).lower() for part in _SENSITIVE_KEY_PARTS)
        }
    if isinstance(value, (list, tuple)):
        return [_sanitize(item) for item in value]
    return value


def record_mobile_audit(
    *,
    username: str,
    command: str,
    request=None,
    device_id: str | None = None,
    server_number: int | None = None,
    incident_id: str | None = None,
    arguments: dict | None = None,
    result: Any = None,
) -> None:
    """Record mobile mutations without ever persisting credentials or push handles."""

    request_device = getattr(request, "mobile_device", None) if request else None
    try:
        resolved_server_number = int(
            server_number if server_number is not None else get_server_number()
        )
    except (TypeError, ValueError):
        resolved_server_number = None
    context = {
        "device_id": device_id or (str(request_device.id) if request_device else None),
        "server_number": resolved_server_number,
        "incident_id": incident_id,
        **(arguments or {}),
    }
    try:
        with enter_session() as session:
            session.add(
                AuditLog(
                    username=username,
                    command=command,
                    command_arguments=json.dumps(_sanitize(context), default=str),
                    command_result=json.dumps(_sanitize(result), default=str),
                )
            )
    except Exception:
        # An audit database outage must be visible, but must not duplicate an already
        # completed administrative action when the client retries the HTTP request.
        logger.exception("Unable to record mobile audit event %s", command)
