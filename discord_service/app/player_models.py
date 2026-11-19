"""Discord transport addresses only. Moderation data belongs to the installation."""

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


class PlayerPanel(Base):
    __tablename__ = "discord_player_panel"
    __table_args__ = (UniqueConstraint("installation_id", "server_number"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    installation_id: Mapped[str] = mapped_column(String(64), index=True)
    server_number: Mapped[int]
    guild_id: Mapped[str] = mapped_column(String(32))
    channel_id: Mapped[str] = mapped_column(String(32))
    message_id: Mapped[str | None] = mapped_column(String(32))


class PrivateReply(Base):
    __tablename__ = "discord_player_private_reply"

    panel_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    discord_user_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    incident_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    interaction_id: Mapped[str] = mapped_column(String(32), default="0")
    notification_sequence: Mapped[int] = mapped_column(BigInteger, default=0)
    applied_sequence: Mapped[int] = mapped_column(BigInteger, default=0)
    encrypted_token: Mapped[str] = mapped_column(Text)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class PlayerDMPreference(Base):
    __tablename__ = "discord_player_dm_preference"

    installation_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    discord_user_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    interaction_id: Mapped[str] = mapped_column(String(32))


class PlayerPanelCallback(Base):
    """An operator-selected origin for one panel, scoped to its original pairing."""

    __tablename__ = "discord_player_panel_callback"

    panel_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    installation_id: Mapped[str] = mapped_column(String(64))
    guild_id: Mapped[str] = mapped_column(String(32))
    server_number: Mapped[int]
    origin: Mapped[str] = mapped_column(String(255))
