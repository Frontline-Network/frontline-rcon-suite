import hashlib
import ipaddress
import json
import os


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _authenticated_identity(request) -> str | None:
    user = getattr(request, "user", None)
    if user is not None and getattr(user, "is_authenticated", False):
        return f"user:{user.pk}"

    authorization = request.META.get("HTTP_AUTHORIZATION", "")
    if authorization:
        return f"bearer:{_digest(authorization)}"

    session = getattr(request, "session", None)
    session_key = getattr(session, "session_key", None)
    if not session_key:
        session_key = request.COOKIES.get("sessionid")
    if session_key:
        return f"session:{_digest(session_key)}"

    return None


def _proxy_client_ip(request) -> str:
    remote_address = request.META.get("REMOTE_ADDR", "unknown")
    try:
        remote_ip = ipaddress.ip_address(remote_address)
    except ValueError:
        return remote_address

    # The shipped deployment exposes Django only through the frontend container.
    # Never trust a forwarded address when Django is reached from a public peer.
    if not (remote_ip.is_private or remote_ip.is_loopback):
        return remote_address

    forwarded = [
        item.strip()
        for item in request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")
        if item.strip()
    ]
    try:
        proxy_depth = max(1, int(os.getenv("RATELIMIT_PROXY_DEPTH", "1")))
    except ValueError:
        proxy_depth = 1

    if len(forwarded) < proxy_depth:
        return remote_address

    candidate = forwarded[-proxy_depth]
    try:
        return str(ipaddress.ip_address(candidate))
    except ValueError:
        return remote_address


def request_rate_limit_key(group, request) -> str:
    identity = _authenticated_identity(request)
    if identity:
        return identity
    return f"client:{_proxy_client_ip(request)}"


def login_account_rate_limit_key(group, request) -> str:
    try:
        data = json.loads(request.body or b"{}")
    except (json.JSONDecodeError, UnicodeDecodeError):
        data = {}

    username = str(data.get("username") or "").strip().casefold()
    if username:
        return f"account:{_digest(username)}"
    return request_rate_limit_key(group, request)
