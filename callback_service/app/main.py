from __future__ import annotations

import hmac
import ipaddress
import re
import socket
import uuid
from datetime import datetime, timezone
from threading import Lock
from time import monotonic
from urllib.parse import urlsplit

import httpx
from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from .config import get_settings
from .db import Base, engine, session_dependency
from .models import InstallationRoute

Base.metadata.create_all(engine)
app = FastAPI(title="Frontline CRCON Callback Broker", version="1.0.0")
_rate_windows: dict[str, tuple[float, int]] = {}
_rate_lock = Lock()
_PATH_RE = re.compile(
    r"^/api/discord/v1/(?:"
    r"pairings/(?:verify|complete)|moderation-(?:feedback|results)|"
    r"diagnostics/ping|player-reports|"
    r"incidents/(?:transition|select-subject|logs)|action-templates|"
    r"actions/prepare|"
    r"actions/[0-9a-fA-F-]{36}/(?:prepare|execute)|"
    r"(?:message|punish|kick|temp_ban|perma_ban|blacklist|remove_from_squad|disband_squad)/prepare"
    r")$"
)
_FORWARDED_HEADERS = {"authorization", "content-type", "idempotency-key"}


class RouteUpsert(BaseModel):
    model_config = ConfigDict(extra="forbid")
    target_base_url: str = Field(min_length=12, max_length=500)
    service_id: str = Field(min_length=1, max_length=100)
    game: str = Field(pattern=r"^(?:hll|hllv|hll_vietnam)$")
    enabled: bool = True


class RouteState(BaseModel):
    model_config = ConfigDict(extra="forbid")
    enabled: bool


def _token(value: str | None) -> str:
    return value[7:] if value and value.startswith("Bearer ") else ""


def _require(expected: str, supplied: str | None) -> None:
    if not hmac.compare_digest(_token(supplied).encode(), expected.encode()):
        raise HTTPException(status_code=404, detail="Unknown capability")


def _rate_limit(key: str) -> None:
    now = monotonic()
    with _rate_lock:
        started, count = _rate_windows.get(key, (now, 0))
        if started <= now - 60:
            started, count = now, 0
        if count >= get_settings().rate_limit_per_minute:
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
        _rate_windows[key] = (started, count + 1)


def _validated_target(value: str) -> str:
    parsed = urlsplit(value.strip().rstrip("/"))
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or parsed.path not in {"", "/"}
        or parsed.port not in {None, 443}
    ):
        raise HTTPException(status_code=400, detail="Invalid public CRCON target URL")
    if not get_settings().allow_private_targets:
        try:
            addresses = {
                item[4][0].split("%", 1)[0]
                for item in socket.getaddrinfo(
                    parsed.hostname, 443, type=socket.SOCK_STREAM
                )
            }
        except socket.gaierror as exc:
            raise HTTPException(
                status_code=400, detail="CRCON target cannot be resolved"
            ) from exc
        if not addresses or any(
            not ipaddress.ip_address(item).is_global for item in addresses
        ):
            raise HTTPException(
                status_code=400,
                detail="CRCON target must resolve only to public addresses",
            )
    return f"https://{parsed.hostname.lower()}"


@app.get("/healthz")
def healthz():
    return {"ok": True}


@app.put("/v1/installations/{installation_id}")
def upsert_route(
    installation_id: uuid.UUID,
    payload: RouteUpsert,
    authorization: str | None = Header(default=None),
    session: Session = Depends(session_dependency),
):
    _require(get_settings().admin_token, authorization)
    _rate_limit(f"admin:{installation_id}")
    target = _validated_target(payload.target_base_url)
    key = str(installation_id)
    route = session.get(InstallationRoute, key) or InstallationRoute(
        installation_id=key,
        target_base_url=target,
        service_id=payload.service_id,
        game=payload.game,
    )
    route.target_base_url = target
    route.service_id = payload.service_id
    route.game = payload.game
    route.enabled = payload.enabled
    route.updated_at = datetime.now(timezone.utc)
    session.add(route)
    session.commit()
    return {"installation_id": key, "registered": True, "enabled": route.enabled}


@app.patch("/v1/installations/{installation_id}")
def set_route_state(
    installation_id: uuid.UUID,
    payload: RouteState,
    authorization: str | None = Header(default=None),
    session: Session = Depends(session_dependency),
):
    _require(get_settings().admin_token, authorization)
    route = session.get(InstallationRoute, str(installation_id))
    if route is None:
        raise HTTPException(status_code=404, detail="Unknown installation")
    route.enabled = payload.enabled
    route.updated_at = datetime.now(timezone.utc)
    session.commit()
    return {"installation_id": route.installation_id, "enabled": route.enabled}


@app.delete(
    "/v1/installations/{installation_id}", status_code=status.HTTP_204_NO_CONTENT
)
def delete_route(
    installation_id: uuid.UUID,
    authorization: str | None = Header(default=None),
    session: Session = Depends(session_dependency),
):
    _require(get_settings().admin_token, authorization)
    route = session.get(InstallationRoute, str(installation_id))
    if route is not None:
        session.delete(route)
        session.commit()
    return Response(status_code=204)


@app.api_route(
    "/v1/installations/{installation_id}/{crcon_path:path}",
    methods=["POST"],
)
async def forward_callback(
    installation_id: uuid.UUID,
    crcon_path: str,
    request: Request,
    broker_authorization: str | None = Header(
        default=None, alias="X-Frontline-Broker-Authorization"
    ),
    session: Session = Depends(session_dependency),
):
    _require(get_settings().discord_token, broker_authorization)
    _rate_limit(f"discord:{installation_id}")
    route = session.get(InstallationRoute, str(installation_id))
    if route is None or not route.enabled:
        raise HTTPException(status_code=404, detail="Unknown installation route")
    path = "/" + crcon_path.lstrip("/")
    if not _PATH_RE.fullmatch(path):
        raise HTTPException(status_code=404, detail="Callback path is not allowed")
    # Re-resolve for every request. This prevents a registered DNS name from being
    # rebound to loopback or an internal network after provisioning.
    target = _validated_target(route.target_base_url)
    body = await request.body()
    if len(body) > get_settings().max_body_bytes:
        raise HTTPException(status_code=413, detail="Callback payload is too large")
    headers = {
        key: value
        for key, value in request.headers.items()
        if key.lower() in _FORWARDED_HEADERS
    }
    try:
        timeout = httpx.Timeout(
            get_settings().request_timeout_seconds,
            connect=get_settings().connect_timeout_seconds,
        )
        async with httpx.AsyncClient(follow_redirects=False, timeout=timeout) as client:
            upstream = await client.post(
                f"{target}{path}", content=body, headers=headers
            )
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502, detail="CRCON callback is unavailable"
        ) from exc
    response_headers = {}
    content_type = upstream.headers.get("content-type")
    if content_type:
        response_headers["content-type"] = content_type
    return Response(
        content=upstream.content,
        status_code=upstream.status_code,
        headers=response_headers,
    )
