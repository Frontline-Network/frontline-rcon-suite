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
