"""Destructive only to the explicitly dedicated disposable PostgreSQL test DB."""
import os
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import inspect, text

from discord_service.app.db import Base, engine, migrate_incident_language, SessionLocal
from discord_service.app.discord_client import DiscordClient
from discord_service.app.main import app
from discord_service.app.models import IncidentMessage
from discord_service.tests.test_service import _event, _seed

pytestmark = pytest.mark.skipif(
    os.getenv("DISCORD_LANGUAGE_DEDICATED_TEST_DB") != "yes" or engine.dialect.name != "postgresql",
    reason="requires an explicitly designated disposable PostgreSQL test database",
)


def test_postgres_old_mapping_migration_and_concurrent_startup():
    Base.metadata.drop_all(engine)
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE discord_incident_message (id INTEGER PRIMARY KEY, incident_id VARCHAR(36))"))
        connection.execute(text("INSERT INTO discord_incident_message VALUES (1, 'old-case')"))
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(lambda _: migrate_incident_language(engine), range(4)))
    with engine.connect() as connection:
        assert connection.execute(text("SELECT incident_id, discord_language FROM discord_incident_message")).one() == ("old-case", "de")
        assert sum(c["name"] == "discord_language" for c in inspect(connection).get_columns("discord_incident_message")) == 1
    with engine.begin() as connection:
        connection.execute(text("DROP TABLE discord_incident_message"))
    Base.metadata.create_all(engine)


def test_concurrent_revisions_do_not_overwrite_newer_incident_language():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    capability = _seed()
    headers = {"Authorization": f"Bearer {capability}"}
    initial = _event()
    initial["incident"]["discord_language"] = "de"
    with patch.object(DiscordClient, "upsert", return_value="123"):
        assert TestClient(app).post("/v1/events", headers={**headers, "Idempotency-Key": "parallel-1"}, json=initial).status_code == 202
        def send(revision, language):
            event = _event()
            event["incident_revision"] = revision
            event["incident"]["discord_language"] = language
            return TestClient(app).post("/v1/events", headers={**headers, "Idempotency-Key": f"parallel-{revision}"}, json=event)
        with ThreadPoolExecutor(max_workers=2) as pool:
            responses = list(pool.map(lambda item: send(*item), [(2, "en"), (3, "fr")]))
        assert all(response.status_code == 202 for response in responses)
    with SessionLocal() as session:
        mapping = session.query(IncidentMessage).one()
        assert (mapping.last_revision, mapping.discord_language) == (3, "fr")
