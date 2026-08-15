from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.pool import StaticPool

from .config import get_settings


class Base(DeclarativeBase):
    pass


settings = get_settings()
engine = create_engine(
    settings.database_url,
    connect_args=(
        {"check_same_thread": False}
        if settings.database_url.startswith("sqlite")
        else {}
    ),
    poolclass=StaticPool if settings.database_url == "sqlite:///:memory:" else None,
)
SessionLocal = sessionmaker(engine, expire_on_commit=False)


def session_dependency():
    with SessionLocal() as session:
        yield session
