from sqlalchemy import (
    JSON,
    BigInteger,
    Float,
    Index,
    LargeBinary,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from rcon.models import Base


class TacticalSettings(Base):
    __tablename__ = "tactical_settings"
    server_number: Mapped[int] = mapped_column(primary_key=True)
    value: Mapped[dict] = mapped_column(JSON, nullable=False)


class TacticalBlock(Base):
    __tablename__ = "tactical_block"
    __table_args__ = (Index("ix_tactical_block_server_time", "server_number", "end_at"),
                      Index("ix_tactical_block_server_round_time", "server_number", "round_id", "start_at"))
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    server_number: Mapped[int] = mapped_column(nullable=False)
    round_id: Mapped[str] = mapped_column(String(160), nullable=False)
    start_at: Mapped[float] = mapped_column(Float, nullable=False)
    end_at: Mapped[float] = mapped_column(Float, nullable=False)
    data: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)


class TacticalReview(Base):
    __tablename__ = "tactical_review"
    server_number: Mapped[int] = mapped_column(primary_key=True)
    signal_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    incident_id: Mapped[str] = mapped_column(String(36), nullable=False)
    expires_at: Mapped[float] = mapped_column(Float, nullable=False, index=True)
    evidence: Mapped[bytes | None] = mapped_column(LargeBinary)


class TacticalArchive(Base):
    __tablename__ = "tactical_archive"
    __table_args__ = (
        UniqueConstraint("server_number", "round_id", name="uq_tactical_archive_server_round"),
        Index("ix_tactical_archive_server_expiry", "server_number", "expires_at"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    server_number: Mapped[int] = mapped_column(nullable=False)
    round_id: Mapped[str] = mapped_column(String(160), nullable=False)
    start_at: Mapped[float] = mapped_column(Float, nullable=False)
    end_at: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[float] = mapped_column(Float, nullable=False)
    expires_at: Mapped[float] = mapped_column(Float, nullable=False)
    retention_days: Mapped[int] = mapped_column(nullable=False)
    created_by: Mapped[str] = mapped_column(String(150), nullable=False)
    reason: Mapped[str] = mapped_column(String(1000), nullable=False)
    incident_id: Mapped[str | None] = mapped_column(String(36))
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    estimated_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)


class TacticalDetection(Base):
    __tablename__ = "tactical_detection"
    __table_args__ = (
        Index("ix_tactical_detection_server_time", "server_number", "last_at"),
        Index("ix_tactical_detection_server_round", "server_number", "round_id"),
        Index("ix_tactical_detection_expiry", "expires_at"),
    )
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    server_number: Mapped[int] = mapped_column(primary_key=True)
    round_id: Mapped[str] = mapped_column(String(160), nullable=False)
    player_id: Mapped[str] = mapped_column(String(100), nullable=False)
    player_name: Mapped[str | None] = mapped_column(String(200))
    kind: Mapped[str] = mapped_column(String(40), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    first_at: Mapped[float] = mapped_column(Float, nullable=False)
    last_at: Mapped[float] = mapped_column(Float, nullable=False)
    expires_at: Mapped[float] = mapped_column(Float, nullable=False)
    rule_version: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="open")
    incident_id: Mapped[str | None] = mapped_column(String(36))
    evidence: Mapped[dict] = mapped_column(JSON, nullable=False)
