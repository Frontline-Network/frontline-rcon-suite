"""Aggregate occupancy only; no player identities are stored."""

from sqlalchemy import BigInteger, CheckConstraint, Float, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from rcon.models import Base


class PopulationSample(Base):
    __tablename__ = "population_samples"
    __table_args__ = (
        CheckConstraint("interval_seconds IN (15, 30, 60)"),
        CheckConstraint(
            "(status = 'ok' AND player_count IS NOT NULL AND max_players IS NOT NULL "
            "AND player_count >= 0 AND max_players >= player_count) "
            "OR (status = 'rcon_error' AND player_count IS NULL AND max_players IS NULL)"
        ),
    )
    server_number: Mapped[int] = mapped_column(primary_key=True)
    scheduled_at: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    captured_at: Mapped[float] = mapped_column(Float, nullable=False)
    interval_seconds: Mapped[int] = mapped_column(nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    player_count: Mapped[int | None]
    max_players: Mapped[int | None]
    map_name: Mapped[str | None] = mapped_column(String(160))


class SeedingSession(Base):
    __tablename__ = "population_seeding_sessions"
    __table_args__ = (
        Index("ix_population_seeding_server_start", "server_number", "started_at"),
        CheckConstraint("ended_at IS NULL OR ended_at >= started_at"),
        CheckConstraint("seeder_count IS NULL OR seeder_count >= 0"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    server_number: Mapped[int] = mapped_column(nullable=False)
    # A unique nullable slot permits only one open manual attempt per server.
    active_server: Mapped[int | None] = mapped_column(unique=True)
    started_at: Mapped[float] = mapped_column(Float, nullable=False)
    ended_at: Mapped[float | None] = mapped_column(Float)
    seeder_count: Mapped[int | None]
    created_by: Mapped[str] = mapped_column(String(150), nullable=False)
    ended_by: Mapped[str | None] = mapped_column(String(150))
