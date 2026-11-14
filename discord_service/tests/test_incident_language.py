from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect, text

from discord_service.app.db import Base, engine, migrate_incident_language, SessionLocal
from discord_service.app.discord_client import DiscordClient, render_message
from discord_service.app.contracts import IncidentEventEnvelope
from discord_service.app.main import app, _action_modal, _template_picker, _crcon_interaction_error
from discord_service.app.models import IncidentMessage, Integration, PreparedActionRelay
from discord_service.app.security import digest, encrypt
from discord_service.tests.test_service import _event, _seed


def test_old_database_is_migrated_without_losing_existing_mappings(tmp_path):
    old = create_engine(f"sqlite:///{tmp_path / 'old.sqlite'}")
    with old.begin() as connection:
        connection.execute(text("CREATE TABLE discord_incident_message (id INTEGER PRIMARY KEY, incident_id VARCHAR(36))"))
        connection.execute(text("INSERT INTO discord_incident_message (id, incident_id) VALUES (1, 'old-case')"))
    migrate_incident_language(old)
    migrate_incident_language(old)
    with old.connect() as connection:
        assert connection.execute(text("SELECT incident_id, discord_language FROM discord_incident_message")).one() == ("old-case", "de")
        assert "discord_language" in {column["name"] for column in inspect(connection).get_columns("discord_incident_message")}


def test_concurrent_migration_is_idempotent(tmp_path):
    old = create_engine(f"sqlite:///{tmp_path / 'concurrent.sqlite'}", connect_args={"timeout": 10})
    with old.begin() as connection:
        connection.execute(text("CREATE TABLE discord_incident_message (id INTEGER PRIMARY KEY)"))
    with ThreadPoolExecutor(max_workers=4) as workers:
        list(workers.map(lambda _: migrate_incident_language(old), range(4)))
    with old.connect() as connection:
        assert sum(column["name"] == "discord_language" for column in inspect(connection).get_columns("discord_incident_message")) == 1


def test_language_survives_missing_and_stale_asynchronous_events():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    capability = _seed()
    client = TestClient(app)
    headers = {"Authorization": f"Bearer {capability}"}
    event = _event()
    event["incident"]["discord_language"] = "fr"
    with patch.object(DiscordClient, "upsert", return_value="123") as upsert:
        assert client.post("/v1/events", headers={**headers, "Idempotency-Key": "language-1"}, json=event).status_code == 202
        event["incident_revision"] = 3
        event["incident"].pop("discord_language")
        assert client.post("/v1/events", headers={**headers, "Idempotency-Key": "language-3"}, json=event).status_code == 202
        assert "Signalement du joueur" in upsert.call_args.args[1]["embeds"][0]["title"]
        event["incident_revision"] = 2
        event["incident"]["discord_language"] = "en"
        stale = client.post("/v1/events", headers={**headers, "Idempotency-Key": "language-2"}, json=event)
        assert stale.json().get("stale") is True
    with SessionLocal() as session:
        mapping = session.query(IncidentMessage).one()
        assert mapping.discord_language == "fr"
        assert mapping.last_revision == 3


def test_french_modal_and_template_picker_keep_customer_text():
    modal = _action_modal("id", "2", "temp_ban", initial_text="Customer's text", language="fr")
    assert modal["data"]["title"] == "Exécuter l’action"
    first = modal["data"]["components"][0]["components"][0]
    assert first["label"] == "Motif" and first["value"] == "Customer's text"
    assert "heures" in modal["data"]["components"][1]["components"][0]["label"]
    picker = _template_picker("id", "2", "kick", [{"id": 1, "title": "Customer title"}], language="fr")
    options = picker["data"]["components"][0]["components"][0]["options"]
    assert options[0]["label"] == "Customer title" and options[-1]["label"] == "Texte libre"
    assert _action_modal("id", "2", "kick")["data"]["title"] == "Aktion ausführen"


def test_french_error_preserves_uncertainty_without_exposing_remote_detail():
    request = httpx.Request("POST", "https://crcon.example")
    response = httpx.Response(502, request=request, json={"error": "HLLCommandError: internal secret"})
    result = _crcon_interaction_error(httpx.HTTPStatusError("failed", request=request, response=response), "fr")
    assert "n’a pas confirmé" in result and "ne la répétez pas immédiatement" in result
    assert "internal secret" not in result


def test_later_discord_interaction_uses_persisted_incident_language():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    capability = _seed()
    event = _event()
    event["incident"]["discord_language"] = "fr"
    with patch.object(DiscordClient, "upsert", return_value="123"):
        response = TestClient(app).post("/v1/events", headers={"Authorization": f"Bearer {capability}", "Idempotency-Key": "fr-dialog"}, json=event)
    assert response.status_code == 202
    claim = httpx.Response(200, request=httpx.Request("POST", "https://crcon.example/transition"), json={"result": {"revision": 2}})
    templates = httpx.Response(200, request=httpx.Request("POST", "https://crcon.example/templates"), json={"result": {"templates": []}})
    interaction = {"id": "1538274085513994250", "type": 3, "guild_id": "123", "channel_id": "456", "member": {"user": {"id": "789", "username": "Moderator"}, "roles": ["42"]}, "data": {"custom_id": "action:22222222-2222-2222-2222-222222222222:1:kick"}}
    with patch("discord_service.app.main._verify_discord_signature"), patch("discord_service.app.main.httpx.post", side_effect=[claim, templates]):
        result = TestClient(app).post("/v1/discord/interactions", json=interaction).json()
    assert result["type"] == 9
    assert result["data"]["title"] == "Exécuter l’action"
    assert result["data"]["components"][0]["components"][0]["label"] == "Motif"


def test_language_is_isolated_per_installation_even_for_identical_incident_ids():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    first = _seed()
    other_id = "33333333-3333-3333-3333-333333333333"
    with SessionLocal() as session:
        session.add(Integration(installation_id=other_id, crcon_base_url="https://other.example", guild_id="321", channel_id="654", event_capability_digest=digest("other-test", "events"), action_capability_ciphertext=encrypt("other-actions")))
        session.commit()
    one, two = _event(), _event()
    one["incident"]["discord_language"] = "fr"
    two["installation_id"] = other_id
    two["incident"]["discord_language"] = "en"
    with patch.object(DiscordClient, "upsert", return_value="123"):
        client = TestClient(app)
        assert client.post("/v1/events", headers={"Authorization": f"Bearer {first}", "Idempotency-Key": "scope-1"}, json=one).status_code == 202
        assert client.post("/v1/events", headers={"Authorization": "Bearer other-test", "Idempotency-Key": "scope-2"}, json=two).status_code == 202
    with SessionLocal() as session:
        entries = {row.installation_id: row.discord_language for row in session.query(IncidentMessage).all()}
        assert entries == {one["installation_id"]: "fr", other_id: "en"}


def test_unknown_interaction_and_invalid_confirmation_use_signed_locale_fallback():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    client = TestClient(app)
    with patch("discord_service.app.main._verify_discord_signature"):
        unknown = client.post("/v1/discord/interactions", json={"type": 3, "locale": "fr-FR", "data": {"custom_id": "unknown"}}).json()
        legacy = client.post("/v1/discord/interactions", json={"type": 3, "locale": "en-US", "data": {"custom_id": "unknown"}}).json()
        confirm = client.post("/v1/discord/interactions", json={"type": 3, "locale": "fr", "data": {"custom_id": "confirm:missing"}}).json()
    assert unknown["data"]["content"] == "Interaction inconnue"
    assert legacy["data"]["content"] == "Unbekannte Interaktion"
    assert "invalide ou expirée" in confirm["data"]["content"]


def test_later_confirmation_uses_mapping_language_and_is_single_use():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    capability = _seed()
    event = _event()
    event["incident"]["discord_language"] = "fr"
    with patch.object(DiscordClient, "upsert", return_value="123"):
        assert TestClient(app).post("/v1/events", headers={"Authorization": f"Bearer {capability}", "Idempotency-Key": "confirm-fr"}, json=event).status_code == 202
    with SessionLocal() as session:
        session.add(PreparedActionRelay(handle="relay-fr", installation_id=event["installation_id"], incident_id=event["incident_id"], preparation_id="prep", confirmation_ciphertext=encrypt("confirm-secret"), actor_id="789", guild_id="123", channel_id="456", actual_action="kick", expires_at=datetime.now(timezone.utc) + timedelta(minutes=5)))
        session.commit()
    payload = {"id": "1538274085513994259", "type": 3, "locale": "en-US", "guild_id": "123", "channel_id": "456", "member": {"user": {"id": "789", "username": "Moderator"}, "roles": ["42"]}, "data": {"custom_id": "confirm:relay-fr"}}
    with patch("discord_service.app.main._verify_discord_signature"), patch("discord_service.app.main._execute_prepared_action", return_value={}) as execute, patch("discord_service.app.main._send_feedback"):
        response = TestClient(app).post("/v1/discord/interactions", json=payload).json()
        second = TestClient(app).post("/v1/discord/interactions", json=payload).json()
    assert response["data"]["content"] == "L’action a été exécutée et journalisée dans CRCON."
    assert second["data"]["content"] == "Bestätigung ist ungültig oder abgelaufen."
    assert execute.call_count == 1


@pytest.mark.parametrize("language, title", [("de", "CRCON-Verbindung erfolgreich"), ("en", "CRCON connection successful"), ("fr", "Connexion CRCON réussie"), ("xx", "CRCON-Verbindung erfolgreich")])
def test_authenticated_test_message_uses_supported_language(language, title):
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    capability = _seed()
    with patch.object(DiscordClient, "upsert", return_value="123") as upsert:
        response = TestClient(app).post("/v1/test-messages", headers={"Authorization": f"Bearer {capability}"}, json={"installation_id": "11111111-1111-1111-1111-111111111111", "language": language})
    assert response.status_code == 202
    assert upsert.call_args.args[1]["embeds"][0]["title"] == title


def test_french_policy_is_accepted_and_unknown_language_is_rejected():
    from pydantic import ValidationError
    from discord_service.app.contracts import ModerationPolicy
    assert ModerationPolicy(language="fr").language == "fr"
    with pytest.raises(ValidationError):
        ModerationPolicy(language="xx")


@pytest.mark.parametrize("language", ["de", "en", "fr", "xx", None, [], {}])
def test_report_renderer_never_fails_for_missing_or_invalid_language(language):
    event = _event()
    event["incident"]["discord_language"] = language
    event["incident"]["reporter_context"] = {"name": "Nom privé"}
    rendered = render_message(IncidentEventEnvelope.model_validate(event), None)
    assert rendered["embeds"] and "Nom privé" in str(rendered["embeds"])
