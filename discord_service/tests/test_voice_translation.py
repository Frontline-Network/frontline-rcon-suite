from hashlib import sha256
import json
from unittest.mock import Mock

import pytest

from fastapi import FastAPI
from fastapi.testclient import TestClient

from discord_service.app import voice_translation as vt


def test_model_review_rejects_changed_meaning(monkeypatch):
    job = vt.TranslationJob(
        installation_id="i",
        language="es",
        texts={"done": "Kick unconfirmed"},
        ai_provider="codex",
        ai_model="test",
    )
    fake = Mock(
        side_effect=[
            (vt.Translation(entries=[vt.Entry(key="done", text="Expulsado")]), 2, 3),
            (vt.Review(all_entries_correct=False), 2, 1),
        ]
    )
    monkeypatch.setattr(vt, "_structured", fake)

    with pytest.raises(ValueError, match="review_failed"):
        vt.translate(job)


@pytest.mark.parametrize("pin", ["CATALOG_HASH", "PREVIOUS_CATALOG_HASH"])
def test_route_authenticates_and_only_sends_pinned_templates(monkeypatch, pin):
    session = Mock()
    checked = Mock()
    app = FastAPI()
    app.include_router(vt.build_translation_router(checked, Mock(), lambda: session))
    client = TestClient(app)
    texts = {"done": "Sent"}
    payload = {
        "installation_id": "i",
        "language": "es",
        "texts": texts,
        "ai_provider": "codex",
        "ai_model": "test",
    }
    worker = Mock(return_value=({"done": "Enviado"}, 1, 2))
    monkeypatch.setattr(vt, "translate", worker)
    assert client.post("/v1/voice-translations", json=payload).status_code == 422
    checked.assert_called_once_with(session, "i", None)
    worker.assert_not_called()
    monkeypatch.setattr(
        vt,
        pin,
        sha256(json.dumps(texts, sort_keys=True).encode()).hexdigest(),
    )
    response = client.post("/v1/voice-translations", json=payload)
    assert response.status_code == 200
    assert response.json() == {"texts": {"done": "Enviado"}}
    assert session.add.call_args.args[0].success is True
