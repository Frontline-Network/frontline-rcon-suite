from __future__ import annotations

from sqlalchemy import create_engine, inspect
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


def migrate_incident_language(target_engine):
    """Add a non-sensitive UI language to older incident mappings, idempotently.

    SQLite serializes the inspection and ALTER across concurrent startups.
    PostgreSQL handles concurrent startups with IF NOT EXISTS. No incident
    content is rewritten; pre-existing mappings keep the historical German
    interaction language until an authenticated event supplies a newer value.
    """
    dialect = target_engine.dialect.name
    if dialect not in {"sqlite", "postgresql"}:
        raise RuntimeError(f"Unsupported database for incident language migration: {dialect}")
    with target_engine.begin() as connection:
        if dialect == "sqlite":
            connection.exec_driver_sql("BEGIN IMMEDIATE")
        inspector = inspect(connection)
        if not inspector.has_table("discord_incident_message"):
            return
        if "discord_language" in {column["name"] for column in inspector.get_columns("discord_incident_message")}:
            return
        clause = " IF NOT EXISTS" if dialect == "postgresql" else ""
        connection.exec_driver_sql(
            f"ALTER TABLE discord_incident_message ADD COLUMN{clause} discord_language VARCHAR(2) NOT NULL DEFAULT 'de'"
        )
