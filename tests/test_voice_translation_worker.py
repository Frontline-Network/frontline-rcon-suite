"""A failed translation cannot block the notice, persist a partial bundle, or spin on retries."""

import os
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

os.environ.setdefault("HLL_MAINTENANCE_CONTAINER", "1")
os.environ.setdefault("SERVER_NUMBER", "1")
os.environ.setdefault("RCONWEB_TEST_MODE", "1")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "rconweb.rconweb.test_settings")

import django

django.setup()
from api import voice_translation_worker as worker
from rcon import voice_language as language
from rcon.voice_language_text import ENGLISH, VERSION


@pytest.fixture()
def queued(monkeypatch):
    engine = create_engine("sqlite://")
    language.VoiceTranslationCache.__table__.create(engine)
    sessions = sessionmaker(engine)
    monkeypatch.setattr(worker, "enter_session", sessions.begin)
    with sessions.begin() as db:
        language.render(db, "notice_squad", "es")
    integration = SimpleNamespace(service_url="https://example.invalid", installation_id="test-installation",
                                  ai_config={"provider": "codex", "ai_model": "model"}, outbound_capability_ciphertext="encrypted")
    monkeypatch.setattr(worker.DiscordReportIntegration.objects, "filter", lambda **kw: SimpleNamespace(first=lambda:integration))
    monkeypatch.setattr(worker, "decrypt_capability", lambda ciphertext:"testcap")
    return sessions


@pytest.mark.parametrize("outcome", ["ok", "corrupt", "busy"])
def test_warm_outcomes_and_single_attempt(queued, outcome):
    http = Mock()
    http.post.return_value.status_code = 429 if outcome == "busy" else 200
    texts = {**ENGLISH, "received":"Informe recibido."}
    if outcome == "corrupt":
        texts["notice_sent"] = "¡Expulsado!"
    http.post.return_value.json.return_value = {"texts":texts}
    if outcome == "corrupt":
        with pytest.raises(ValueError, match="invalid_voice_translation"):
            worker.process_one(http)
    else:
        assert worker.process_one(http)
    assert not worker.process_one(http)
    assert http.post.call_count == 1
    body = http.post.call_args.kwargs["json"]
    assert body["texts"] == ENGLISH
    assert body["api_key"] is None
    with queued.begin() as db:
        cached = db.get(language.VoiceTranslationCache, ("es", VERSION))
        if outcome == "ok":
            assert cached.next_attempt == -1
            assert language.render(db, "received", "es") == "Informe recibido."
        else:
            assert cached.texts == {}
            assert "Translation currently unavailable" in language.render(db, "received", "es")
