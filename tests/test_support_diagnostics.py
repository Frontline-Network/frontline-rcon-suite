from datetime import datetime, timezone

from rcon.support_diagnostics import build_support_diagnostics, preview_support_diagnostics


def test_support_diagnostics_allowlists_aggregate_fields_and_omits_sensitive_data():
    package = build_support_diagnostics(
        version="v0.3.10",
        game="hll",
        server_number=2,
        system_usage={
            "status": "warning",
            "sampled_at": "2026-08-21T12:00:00+00:00",
            "data_age_seconds": 3,
            "range": {"from": "a", "to": "b", "seconds": 900, "sample_interval_seconds": 15},
            "warnings": [{"metric": "ram", "severity": "warning", "code": "ram_warning", "threshold_percent": 80, "text": "secret"}],
            "cpu_usage": {"percent": 12, "source": "host", "process_count": 9000},
            "ram_usage": {"percent": 81, "source": "host", "path": "/private"},
            "rcon_ram_usage": {
                "available": True, "used_bytes": 1234,
                "dedicated_used_bytes": 1000, "shared_used_bytes": 234,
                "reclaimable_bytes": 100, "working_set_bytes": 1134,
                "source": "rcon_services", "percent": None,
                "components": [{"service": "private-hostname", "token": "private-token"}],
                "path": "/private-resource-metrics",
            },
            "disk_usage": {"percent": 32, "source": "filesystem"},
            "history": [{"sampled_at": "x", "cpu_percent": 1, "player_name": "Alice"}],
        },
        services=[
            {"name": "automod", "statename": "FATAL", "start": 10, "now": 20, "spawnerr": "token=abc"},
            {"name": "unknown_secret", "statename": "RUNNING", "start": 10, "now": 20},
        ],
        known_service_names={"automod"},
        generated_at=datetime(2026, 8, 21, tzinfo=timezone.utc),
    )

    rendered = str(package)
    assert package["services"] == [{"name": "automod", "state": "FATAL", "uptime_seconds": 10}]
    assert package["error_signatures"] == ["system.ram_warning", "service.automod.fatal"]
    assert "Alice" not in rendered
    assert "abc" not in rendered
    assert "unknown_secret" not in rendered
    assert "process_count" not in rendered
    assert "path" not in rendered
    assert "private-hostname" not in rendered
    assert "private-token" not in rendered
    metric = package["system_usage"]["metrics"]["rcon_ram"]
    assert metric["used_bytes"] == 1234
    assert metric["shared_used_bytes"] == 234
    assert metric["reclaimable_bytes"] == 100
    assert metric["percent"] is None


def test_support_diagnostics_preview_matches_exact_export_scope():
    package = build_support_diagnostics(
        version="v0.3.10",
        game="hllv",
        server_number=4,
        system_usage={},
        services=[],
        known_service_names=set(),
    )

    preview = preview_support_diagnostics(package)

    assert preview["format"] == "JSON"
    assert preview["estimated_bytes"] > 0
    assert preview["service_count"] == 0
    assert "raw logs and error text" in preview["omitted"]
