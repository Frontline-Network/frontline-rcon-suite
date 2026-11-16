from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
EXPECTED_WEBHOOK_HEALTHCHECK = [
    "CMD-SHELL",
    "test -e /code/webhook-service-healthy",
]


class ComposeLoader(yaml.SafeLoader):
    pass


ComposeLoader.add_constructor(
    "!reset", lambda loader, node: loader.construct_sequence(node)
)


def _load_compose(filename):
    compose = yaml.load(
        (REPO_ROOT / filename).read_text(encoding="utf-8"),
        Loader=ComposeLoader,
    )
    return compose


def test_webhook_healthcheck_source_template_fails_closed():
    compose = _load_compose("docker-compose-common-components.yaml")

    assert (
        compose["services"]["webhook_service"]["healthcheck"]["test"]
        == EXPECTED_WEBHOOK_HEALTHCHECK
    )


def test_webhook_healthcheck_production_override_fails_closed():
    compose = _load_compose("compose.mobile-admin.yaml")

    assert (
        compose["services"]["webhook_service"]["healthcheck"]["test"]
        == EXPECTED_WEBHOOK_HEALTHCHECK
    )


def test_managed_backend_overrides_replace_legacy_readiness_checks():
    compose = _load_compose("compose.mobile-admin.yaml")
    expected = ["CMD", "python", "/code/scripts/backend_healthcheck.py"]
    for number in range(1, 5):
        backend = compose["services"][f"backend_{number}"]
        supervisor = compose["services"][f"supervisor_{number}"]
        assert backend["healthcheck"]["disable"] is False
        assert backend["healthcheck"]["test"] == expected
        assert "healthcheck" not in supervisor
