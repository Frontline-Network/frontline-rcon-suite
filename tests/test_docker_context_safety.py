from pathlib import Path


def test_docker_context_excludes_runtime_secrets_and_backups():
    patterns = {
        line.strip()
        for line in Path(".dockerignore").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }

    assert {
        ".deploy-backups/",
        ".deploy-state/",
        ".env",
        "certs/",
        "static/",
        "supervisor_data/",
    } <= patterns


def test_maintenance_receives_the_django_application_secret():
    compose = Path("docker-compose-common-components.yaml").read_text(
        encoding="utf-8"
    )
    maintenance = compose.split("  maintenance:", 1)[1].split(
        "  # This is used to handle webhooks", 1
    )[0]

    assert "RCONWEB_API_SECRET: ${RCONWEB_API_SECRET}" in maintenance
