from sqlalchemy import JSON, Float, Index, LargeBinary, String
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
