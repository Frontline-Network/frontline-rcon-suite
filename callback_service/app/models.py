from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


class InstallationRoute(Base):
    __tablename__ = "callback_installation_route"

    installation_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    target_base_url: Mapped[str] = mapped_column(String(500), nullable=False)
    service_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    game: Mapped[str] = mapped_column(String(32), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
