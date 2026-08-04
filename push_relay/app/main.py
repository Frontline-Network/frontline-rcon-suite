import hashlib
import hmac
import os
import secrets
import uuid
from datetime import datetime, timedelta, timezone

import firebase_admin
from fastapi import Depends, FastAPI, Header, HTTPException, Response, status
from firebase_admin import credentials, messaging
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import DateTime, Integer, String, Text, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

DATABASE_URL = os.getenv("RELAY_DATABASE_URL", "sqlite:///./push-relay.sqlite")
RELAY_SECRET = os.getenv("RELAY_SECRET", "")
RATE_LIMIT_PER_MINUTE = int(os.getenv("RELAY_RATE_LIMIT_PER_MINUTE", "30"))
DRY_RUN = os.getenv("RELAY_DRY_RUN", "false").lower() in {"1", "true", "yes"}

if len(RELAY_SECRET) < 32:
    raise RuntimeError("RELAY_SECRET must contain at least 32 characters")


class Base(DeclarativeBase):
    pass


class RelayDevice(Base):
    __tablename__ = "relay_device"

    handle: Mapped[str] = mapped_column(String(36), primary_key=True)
    platform: Mapped[str] = mapped_column(String(16), nullable=False)
    push_token: Mapped[str] = mapped_column(Text, nullable=False)
    token_digest: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    capability_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    rate_window_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rate_window_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


engine = create_engine(
    DATABASE_URL,
    connect_args=(
        {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
    ),
)
SessionLocal = sessionmaker(engine, expire_on_commit=False)
Base.metadata.create_all(engine)


def _digest(value: str, purpose: str) -> str:
    return hmac.new(
        RELAY_SECRET.encode(), f"{purpose}:{value}".encode(), hashlib.sha256
    ).hexdigest()


def _session():
    with SessionLocal() as session:
        yield session


class RegistrationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    platform: str = Field(pattern="^(android|ios)$")
    push_token: str = Field(min_length=20, max_length=4096)


class RegistrationResponse(BaseModel):
    handle: str
    notify_capability: str


class NotificationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    connection_key: uuid.UUID
    incident_id: uuid.UUID
    event_type: str = Field(min_length=1, max_length=32, pattern="^[a-z_]+$")
    timestamp: datetime


app = FastAPI(title="CRCON Push Relay", version="1.0")


def _init_firebase():
    if firebase_admin._apps:
        return
    credential_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if credential_path:
        firebase_admin.initialize_app(credentials.Certificate(credential_path))
    else:
        firebase_admin.initialize_app()


@app.get("/healthz")
def healthz():
    return {"ok": True}


@app.post("/v1/devices", response_model=RegistrationResponse)
def register_device(payload: RegistrationRequest, session: Session = Depends(_session)):
    now = datetime.now(tz=timezone.utc)
    raw_capability = f"notify_{secrets.token_urlsafe(32)}"
    token_digest = _digest(payload.push_token, "push-token")
    device = session.execute(
        select(RelayDevice).where(RelayDevice.token_digest == token_digest)
    ).scalar_one_or_none()
    if device is None:
        device = RelayDevice(
            handle=str(uuid.uuid4()),
            platform=payload.platform,
            push_token=payload.push_token,
            token_digest=token_digest,
            capability_digest=_digest(raw_capability, "notify"),
            created_at=now,
            last_seen_at=now,
            rate_window_count=0,
        )
        session.add(device)
    else:
        device.platform = payload.platform
        device.push_token = payload.push_token
        device.capability_digest = _digest(raw_capability, "notify")
        device.last_seen_at = now
    session.commit()
    return RegistrationResponse(handle=device.handle, notify_capability=raw_capability)


def _authorized_device(
    handle: str,
    authorization: str | None,
    session: Session,
) -> RelayDevice:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing notify capability")
    raw_capability = authorization[7:]
    device = session.get(RelayDevice, handle)
    if device is None or not hmac.compare_digest(
        device.capability_digest, _digest(raw_capability, "notify")
    ):
        raise HTTPException(status_code=404, detail="Unknown device capability")
    return device


def _check_rate_limit(device: RelayDevice):
    now = datetime.now(tz=timezone.utc)
    window = device.rate_window_at
    if window is not None and window.tzinfo is None:
        # SQLite drops timezone offsets; production PostgreSQL preserves them.
        window = window.replace(tzinfo=timezone.utc)
    if window is None or window <= now - timedelta(minutes=1):
        device.rate_window_at = now
        device.rate_window_count = 0
    if device.rate_window_count >= RATE_LIMIT_PER_MINUTE:
        raise HTTPException(status_code=429, detail="Notification rate limit exceeded")
    device.rate_window_count += 1
    device.last_seen_at = now


@app.post("/v1/notify/{handle}", status_code=status.HTTP_202_ACCEPTED)
def notify(
    handle: str,
    payload: NotificationRequest,
    authorization: str | None = Header(default=None),
    session: Session = Depends(_session),
):
    device = _authorized_device(handle, authorization, session)
    _check_rate_limit(device)
    data = {
        "connection_key": str(payload.connection_key),
        "incident_id": str(payload.incident_id),
        "event_type": payload.event_type,
        "timestamp": payload.timestamp.astimezone(timezone.utc).isoformat(),
    }
    try:
        if not DRY_RUN:
            _init_firebase()
            messaging.send(messaging.Message(data=data, token=device.push_token))
    except messaging.UnregisteredError:
        session.delete(device)
        session.commit()
        raise HTTPException(status_code=410, detail="Push token is no longer valid")
    except Exception as exc:
        session.rollback()
        raise HTTPException(
            status_code=503, detail="Push provider unavailable"
        ) from exc
    session.commit()
    return {"accepted": True}


@app.delete("/v1/devices/{handle}", status_code=status.HTTP_204_NO_CONTENT)
def delete_device(
    handle: str,
    authorization: str | None = Header(default=None),
    session: Session = Depends(_session),
):
    device = _authorized_device(handle, authorization, session)
    session.delete(device)
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
