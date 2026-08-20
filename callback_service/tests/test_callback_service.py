import os
from unittest.mock import patch

os.environ.setdefault("CALLBACK_SERVICE_DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault(
    "CALLBACK_SERVICE_ADMIN_TOKEN", "admin-test-capability-that-is-long-enough"
)
os.environ.setdefault(
    "CALLBACK_SERVICE_DISCORD_TOKEN", "discord-test-capability-that-is-long-enough"
)
os.environ.setdefault("CALLBACK_SERVICE_ALLOW_PRIVATE_TARGETS", "true")

from callback_service.app.db import Base, SessionLocal, engine
from callback_service.app.main import _PATH_RE, app
from callback_service.app.models import InstallationRoute
from fastapi.testclient import TestClient

INSTALLATION = "11111111-1111-4111-8111-111111111111"


def setup_function():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)


def test_admin_capability_registers_and_controls_route():
    client = TestClient(app)
    path = f"/v1/installations/{INSTALLATION}"
    payload = {
        "target_base_url": "https://customer.example",
        "service_id": "42",
        "game": "hllv",
        "enabled": True,
    }
    assert client.put(path, json=payload).status_code == 404
    response = client.put(
        path,
        headers={"Authorization": "Bearer admin-test-capability-that-is-long-enough"},
        json=payload,
    )
    assert response.status_code == 200
    assert response.json()["registered"] is True
    with SessionLocal() as session:
        route = session.get(InstallationRoute, INSTALLATION)
        assert route.target_base_url == "https://customer.example"
        assert route.game == "hllv"

    disabled = client.patch(
        path,
        headers={"Authorization": "Bearer admin-test-capability-that-is-long-enough"},
        json={"enabled": False},
    )
    assert disabled.status_code == 200
    assert disabled.json()["enabled"] is False


def test_proxy_requires_discord_capability_and_allowlisted_path():
    client = TestClient(app)
    with SessionLocal() as session:
        session.add(
            InstallationRoute(
                installation_id=INSTALLATION,
                target_base_url="https://customer.example",
                service_id="42",
                game="hll",
                enabled=True,
            )
        )
        session.commit()
    allowed = f"/v1/installations/{INSTALLATION}/api/discord/v1/pairings/verify"
    assert client.post(allowed, json={}).status_code == 404
    rejected = client.post(
        f"/v1/installations/{INSTALLATION}/api/admin/users",
        headers={
            "X-Frontline-Broker-Authorization": "Bearer discord-test-capability-that-is-long-enough"
        },
        json={},
    )
    assert rejected.status_code == 404


def test_invalid_uuid_never_reaches_storage():
    response = TestClient(app).put(
        "/v1/installations/not-an-id",
        headers={"Authorization": "Bearer admin-test-capability-that-is-long-enough"},
        json={
            "target_base_url": "https://customer.example",
            "service_id": "42",
            "game": "hll",
        },
    )
    assert response.status_code == 422


def test_diagnostic_callback_path_is_explicitly_allowlisted():
    assert _PATH_RE.fullmatch("/api/discord/v1/diagnostics/ping")
    assert not _PATH_RE.fullmatch("/api/discord/v1/diagnostics/anything-else")
