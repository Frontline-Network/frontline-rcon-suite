"""Private Discord voice-report intake, link challenges and durable receipts."""

import datetime as dt

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from rcon.models import Base


class VoiceDraft(Base):
    __tablename__ = "voice_player_draft"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    server: Mapped[int] = mapped_column(Integer)
    discord_id: Mapped[str] = mapped_column(String(24))
    message: Mapped[str] = mapped_column(String(2000))
    language: Mapped[str] = mapped_column(String(40))
    expires: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), index=True)


class VoiceLinkChallenge(Base):
    __tablename__ = "voice_link_challenge"
    server: Mapped[int] = mapped_column(Integer, primary_key=True)
    discord_id: Mapped[str] = mapped_column(String(24), primary_key=True)
    game_id: Mapped[str] = mapped_column(String(100))
    created: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True))
    digest: Mapped[str] = mapped_column(String(64))
    attempts: Mapped[int] = mapped_column(Integer)
    delivered: Mapped[bool] = mapped_column(Boolean)
    __table_args__ = (
        Index("ix_voice_challenge_target", "server", "game_id", "created"),
    )


class VoicePlayerDelivery(Base):
    __tablename__ = "voice_player_delivery"
    id: Mapped[int] = mapped_column(primary_key=True)
    incident_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("admin_incident.id", ondelete="CASCADE")
    )
    discord_id: Mapped[str] = mapped_column(String(24))
    kind: Mapped[str] = mapped_column(String(24))
    payload: Mapped[dict] = mapped_column(JSON)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    done: Mapped[bool] = mapped_column(Boolean, default=False)
    due: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True))
    __table_args__ = (
        Index(
            "uq_voice_delivery_recipient",
            "incident_id",
            "discord_id",
            "kind",
            unique=True,
        ),
        Index("ix_voice_delivery_due", "done", "due"),
    )
