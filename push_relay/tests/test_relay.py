import importlib

from fastapi.testclient import TestClient


def _client(
    monkeypatch,
    tmp_path,
    *,
    rate_limit=30,
    registration_rate_limit=120,
    max_registered_devices=10000,
):
    monkeypatch.setenv("RELAY_SECRET", "test-secret-that-is-at-least-32-characters")
    monkeypatch.setenv("RELAY_DATABASE_URL", f"sqlite:///{tmp_path / 'relay.sqlite'}")
    monkeypatch.setenv("RELAY_DRY_RUN", "true")
    monkeypatch.setenv("RELAY_RATE_LIMIT_PER_MINUTE", str(rate_limit))
    monkeypatch.setenv(
        "RELAY_REGISTRATION_RATE_LIMIT_PER_MINUTE", str(registration_rate_limit)
    )
    monkeypatch.setenv("RELAY_MAX_REGISTERED_DEVICES", str(max_registered_devices))
    import app.main

    module = importlib.reload(app.main)
    return TestClient(module.app)


def test_registration_and_opaque_notification(monkeypatch, tmp_path):
    client = _client(monkeypatch, tmp_path)
    registration = client.post(
        "/v1/devices",
        json={"platform": "android", "push_token": "x" * 64},
    )
    assert registration.status_code == 200
    identity = registration.json()

    response = client.post(
        f"/v1/notify/{identity['handle']}",
        headers={"Authorization": f"Bearer {identity['notify_capability']}"},
        json={
            "connection_key": "8feb2bad-6dca-42f8-9346-25b01f191b8f",
            "incident_id": "bf3378ef-ea20-4921-b225-2443967fd74a",
            "event_type": "created",
            "timestamp": "2026-08-04T12:00:00Z",
        },
    )
    assert response.status_code == 202


def test_registration_accepts_a_web_pwa_token(monkeypatch, tmp_path):
    client = _client(monkeypatch, tmp_path)
    response = client.post(
        "/v1/devices",
        json={"platform": "web", "push_token": "w" * 64},
    )
    assert response.status_code == 200
    assert response.json()["handle"]


def test_registration_is_idempotent_for_the_same_push_token(monkeypatch, tmp_path):
    client = _client(monkeypatch, tmp_path)
    payload = {"platform": "android", "push_token": "i" * 64}
    first = client.post("/v1/devices", json=payload)
    second = client.post("/v1/devices", json=payload)
    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json() == first.json()


def test_rate_limits_public_device_registration(monkeypatch, tmp_path):
    client = _client(monkeypatch, tmp_path, registration_rate_limit=1)
    assert (
        client.post(
            "/v1/devices",
            json={"platform": "android", "push_token": "a" * 64},
        ).status_code
        == 200
    )
    assert (
        client.post(
            "/v1/devices",
            json={"platform": "android", "push_token": "b" * 64},
        ).status_code
        == 429
    )


def test_caps_registered_devices(monkeypatch, tmp_path):
    client = _client(monkeypatch, tmp_path, max_registered_devices=1)
    assert (
        client.post(
            "/v1/devices",
            json={"platform": "android", "push_token": "c" * 64},
        ).status_code
        == 200
    )
    assert (
        client.post(
            "/v1/devices",
            json={"platform": "android", "push_token": "d" * 64},
        ).status_code
        == 503
    )


def test_rejects_sensitive_payload_fields(monkeypatch, tmp_path):
    client = _client(monkeypatch, tmp_path)
    registration = client.post(
        "/v1/devices", json={"platform": "ios", "push_token": "y" * 64}
    ).json()
    response = client.post(
        f"/v1/notify/{registration['handle']}",
        headers={"Authorization": f"Bearer {registration['notify_capability']}"},
        json={
            "connection_key": "8feb2bad-6dca-42f8-9346-25b01f191b8f",
            "incident_id": "bf3378ef-ea20-4921-b225-2443967fd74a",
            "event_type": "created",
            "timestamp": "2026-08-04T12:00:00Z",
            "player_name": "must not leave CRCON",
        },
    )
    assert response.status_code == 422


def test_rejects_wrong_notify_capability(monkeypatch, tmp_path):
    client = _client(monkeypatch, tmp_path)
    registration = client.post(
        "/v1/devices", json={"platform": "ios", "push_token": "z" * 64}
    ).json()
    response = client.post(
        f"/v1/notify/{registration['handle']}",
        headers={"Authorization": "Bearer wrong"},
        json={
            "connection_key": "8feb2bad-6dca-42f8-9346-25b01f191b8f",
            "incident_id": "bf3378ef-ea20-4921-b225-2443967fd74a",
            "event_type": "created",
            "timestamp": "2026-08-04T12:00:00Z",
        },
    )
    assert response.status_code == 404


def test_rate_limits_each_device_handle(monkeypatch, tmp_path):
    client = _client(monkeypatch, tmp_path, rate_limit=1)
    registration = client.post(
        "/v1/devices", json={"platform": "android", "push_token": "r" * 64}
    ).json()
    request = {
        "connection_key": "8feb2bad-6dca-42f8-9346-25b01f191b8f",
        "incident_id": "bf3378ef-ea20-4921-b225-2443967fd74a",
        "event_type": "created",
        "timestamp": "2026-08-04T12:00:00Z",
    }
    headers = {"Authorization": f"Bearer {registration['notify_capability']}"}
    assert (
        client.post(
            f"/v1/notify/{registration['handle']}", headers=headers, json=request
        ).status_code
        == 202
    )
    assert (
        client.post(
            f"/v1/notify/{registration['handle']}", headers=headers, json=request
        ).status_code
        == 429
    )
