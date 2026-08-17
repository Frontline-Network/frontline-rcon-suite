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


def test_split_api_workers_recycle_after_bounded_request_count():
    entrypoint = (REPO_ROOT / "entrypoint.sh").read_text(encoding="utf-8")

    assert 'GUNICORN_MAX_REQUESTS="${HLL_GUNICORN_MAX_REQUESTS:-1000}"' in entrypoint
    assert (
        'GUNICORN_MAX_REQUESTS_JITTER="${HLL_GUNICORN_MAX_REQUESTS_JITTER:-100}"'
        in entrypoint
    )
    assert '--max-requests "$GUNICORN_MAX_REQUESTS"' in entrypoint
    assert '--max-requests-jitter "$GUNICORN_MAX_REQUESTS_JITTER"' in entrypoint


def test_backend_start_removes_stale_pid_and_unified_mode_records_real_pid():
    entrypoint = (REPO_ROOT / "entrypoint.sh").read_text(encoding="utf-8")

    assert "rm -f /code/rconweb/gunicorn.pid" in entrypoint
    assert "echo $$ > gunicorn.pid" in entrypoint


def test_backend_healthchecks_validate_http_and_websocket_readiness():
    for template_name in ("one-server.yaml", "ten-servers.yaml"):
        template = (REPO_ROOT / "docker-templates" / template_name).read_text(
            encoding="utf-8"
        )

        assert '["CMD", "python", "/code/scripts/backend_healthcheck.py"]' in template


def test_backend_health_endpoint_does_not_probe_external_dependencies():
    urls = (REPO_ROOT / "rconweb" / "rconweb" / "urls.py").read_text(
        encoding="utf-8"
    )
    healthcheck = (REPO_ROOT / "scripts" / "backend_healthcheck.py").read_text(
        encoding="utf-8"
    )

    assert 'path("healthz", healthz, name="healthz")' in urls
    assert "HttpResponse(status=204)" in urls
    assert "http://127.0.0.1:8000/healthz" in healthcheck
    assert '("127.0.0.1", 8001)' in healthcheck


def test_frontend_uses_one_event_driven_nginx_worker_per_instance():
    dockerfile = (REPO_ROOT / "Dockerfile-frontend").read_text(encoding="utf-8")

    assert "worker_processes 1" in dockerfile


def test_combined_supervisor_runtime_is_explicit_opt_in():
    entrypoint = (REPO_ROOT / "entrypoint.sh").read_text(encoding="utf-8")

    assert '[[ -n "${HLL_SUPERVISOR_CONFIG:-}" ]]' in entrypoint
    assert 'supervisord -c "$HLL_SUPERVISOR_CONFIG"' in entrypoint
    assert "supervisord -c /config/supervisord.conf" in entrypoint


def test_public_recent_logs_default_is_bounded_without_changing_internal_scan():
    api_commands = (REPO_ROOT / "rcon" / "api_commands.py").read_text(
        encoding="utf-8"
    )
    game_logs = (REPO_ROOT / "rcon" / "game_logs.py").read_text(encoding="utf-8")

    assert "        end: int = 500," in api_commands
    assert "    end: int = 100000," in game_logs
