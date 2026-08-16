from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


class Integration(Base):
    __tablename__ = "discord_integration"

    installation_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    crcon_base_url: Mapped[str] = mapped_column(String(500), nullable=False)
    guild_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    channel_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    event_capability_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    action_capability_ciphertext: Mapped[str] = mapped_column(Text, nullable=False)
    enabled: Mapped[bool] = mapped_column(default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(tz=timezone.utc)
    )


class OAuthInstallIntent(Base):
    __tablename__ = "discord_oauth_install_intent"

    state_digest: Mapped[str] = mapped_column(String(64), primary_key=True)
    installation_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class InstallationGuildBinding(Base):
    __tablename__ = "discord_installation_guild_binding"

    installation_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    guild_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    guild_name: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    authorized: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(tz=timezone.utc)
    )


class IncidentMessage(Base):
    __tablename__ = "discord_incident_message"
    __table_args__ = (
        UniqueConstraint(
            "installation_id", "incident_id", name="uq_discord_incident_message"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    installation_id: Mapped[str] = mapped_column(String(64), index=True)
    incident_id: Mapped[str] = mapped_column(String(36), index=True)
    message_id: Mapped[str] = mapped_column(String(32), nullable=False)
    channel_id: Mapped[str] = mapped_column(String(32), nullable=False)
    last_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    analysis_id: Mapped[str | None] = mapped_column(String(36))
    suggested_action: Mapped[str | None] = mapped_column(String(32))
    suggested_duration_hours: Mapped[int | None] = mapped_column(Integer)
    primary_subject_id: Mapped[str | None] = mapped_column(String(36))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(tz=timezone.utc)
    )


class EventReceipt(Base):
    __tablename__ = "discord_event_receipt"

    idempotency_key: Mapped[str] = mapped_column(String(160), primary_key=True)
    installation_id: Mapped[str] = mapped_column(String(64), index=True)
    event_id: Mapped[int] = mapped_column(Integer, nullable=False)
    event_type: Mapped[str] = mapped_column(String(32), nullable=False)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(tz=timezone.utc)
    )


class TechnicalUsageMetric(Base):
    """Content-free operational usage accounting."""

    __tablename__ = "discord_technical_usage"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    installation_id: Mapped[str] = mapped_column(String(64), index=True)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    model: Mapped[str | None] = mapped_column(String(100))
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    success: Mapped[bool] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(tz=timezone.utc)
    )


class PreparedActionRelay(Base):
    """Short-lived opaque bridge; the CRCON confirmation secret stays encrypted."""

    __tablename__ = "discord_prepared_action_relay"

    handle: Mapped[str] = mapped_column(String(36), primary_key=True)
    installation_id: Mapped[str] = mapped_column(String(64), index=True)
    incident_id: Mapped[str] = mapped_column(String(36), index=True)
    preparation_id: Mapped[str] = mapped_column(String(36), nullable=False)
    confirmation_ciphertext: Mapped[str] = mapped_column(Text, nullable=False)
    actor_id: Mapped[str] = mapped_column(String(32), nullable=False)
    guild_id: Mapped[str] = mapped_column(String(32), nullable=False)
    channel_id: Mapped[str] = mapped_column(String(32), nullable=False)
    analysis_id: Mapped[str | None] = mapped_column(String(36))
    suggested_action: Mapped[str | None] = mapped_column(String(32))
    actual_action: Mapped[str] = mapped_column(String(32), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
