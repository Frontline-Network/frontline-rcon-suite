from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_single_worker_gunicorn_preload_is_not_unconditional():
    entrypoint = (REPO_ROOT / "entrypoint.sh").read_text(encoding="utf-8")

    assert "GUNICORN_PRELOAD_MODE=\"${HLL_GUNICORN_PRELOAD:-auto}\"" in entrypoint
    assert '"$NB_API_WORKERS" -gt 1' in entrypoint
    assert 'gunicorn "${GUNICORN_PRELOAD_ARGS[@]}"' in entrypoint
    assert "gunicorn --preload" not in entrypoint


def test_unified_api_mode_is_explicit_opt_in_and_uses_both_existing_ports():
    entrypoint = (REPO_ROOT / "entrypoint.sh").read_text(encoding="utf-8")

    assert 'API_SERVER_MODE="${HLL_API_SERVER_MODE:-split}"' in entrypoint
    assert '[[ "$API_SERVER_MODE" == "unified" ]]' in entrypoint
    assert "-e tcp:port=8000:interface=0.0.0.0" in entrypoint
    assert "-e tcp:port=8001:interface=0.0.0.0" in entrypoint
    assert "rconweb.asgi:application" in entrypoint
