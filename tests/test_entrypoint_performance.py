from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_single_worker_gunicorn_preload_is_not_unconditional():
    entrypoint = (REPO_ROOT / "entrypoint.sh").read_text(encoding="utf-8")

    assert "GUNICORN_PRELOAD_MODE=\"${HLL_GUNICORN_PRELOAD:-auto}\"" in entrypoint
    assert '"$NB_API_WORKERS" -gt 1' in entrypoint
    assert 'gunicorn "${GUNICORN_PRELOAD_ARGS[@]}"' in entrypoint
    assert "gunicorn --preload" not in entrypoint
