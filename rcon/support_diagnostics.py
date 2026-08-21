"""Create a privacy-preserving support diagnostics package.

The package is deliberately assembled from allowlisted, aggregate fields. It
never reads game logs, configuration values, player records, URLs or process
command lines, which keeps it useful for support without becoming a data leak.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Iterable

PACKAGE_SCHEMA_VERSION = 1
SAFE_SERVICE_STATES = frozenset({"RUNNING", "STOPPED", "FATAL", "EXITED"})


def _safe_metric(metric: dict[str, Any] | None) -> dict[str, Any]:
    """Keep aggregate capacity values, excluding paths and process details."""

    metric = metric or {}
    return {
        key: metric.get(key)
        for key in ("available", "percent", "used", "total", "unit", "source", "severity")
    }


def _safe_system_usage(snapshot: dict[str, Any] | None) -> dict[str, Any]:
    snapshot = snapshot or {}
    history = snapshot.get("history") or []
    return {
        "status": snapshot.get("status", "unavailable"),
        "sampled_at": snapshot.get("sampled_at"),
        "data_age_seconds": snapshot.get("data_age_seconds"),
        "range": {
            key: (snapshot.get("range") or {}).get(key)
            for key in ("from", "to", "seconds", "sample_interval_seconds")
        },
        "warnings": [
            {
                key: warning.get(key)
                for key in ("metric", "severity", "code", "threshold_percent")
            }
            for warning in snapshot.get("warnings") or []
            if isinstance(warning, dict)
        ],
        "metrics": {
            "cpu": _safe_metric(snapshot.get("cpu_usage")),
            "ram": _safe_metric(snapshot.get("ram_usage")),
            "disk": _safe_metric(snapshot.get("disk_usage")),
        },
        "history": [
            {
                key: entry.get(key)
                for key in ("sampled_at", "cpu_percent", "ram_percent", "disk_percent", "status")
            }
            for entry in history
            if isinstance(entry, dict)
        ],
    }


def _safe_services(
    services: Iterable[dict[str, Any]], *, known_service_names: set[str]
) -> tuple[list[dict[str, Any]], list[str]]:
    """Reduce supervisor data to names, states and bounded uptime only."""

    result: list[dict[str, Any]] = []
    signatures: list[str] = []
    for service in services:
        name = service.get("name")
        state = service.get("statename")
        if name not in known_service_names or state not in SAFE_SERVICE_STATES:
            continue

        start = service.get("start")
        now = service.get("now")
        uptime_seconds = (
            max(0, int(now) - int(start))
            if isinstance(now, (int, float)) and isinstance(start, (int, float))
            else None
        )
        result.append({"name": name, "state": state, "uptime_seconds": uptime_seconds})
        if state in {"FATAL", "EXITED"}:
            signatures.append(f"service.{name}.{state.lower()}")
    return sorted(result, key=lambda item: item["name"]), sorted(signatures)


def build_support_diagnostics(
    *,
    version: str,
    game: str | None,
    server_number: int | None,
    system_usage: dict[str, Any] | None,
    services: Iterable[dict[str, Any]],
    known_service_names: set[str],
    generated_at: datetime | None = None,
) -> dict[str, Any]:
    """Return a compact, JSON-serializable support package without raw data."""

    generated_at = generated_at or datetime.now(timezone.utc)
    safe_usage = _safe_system_usage(system_usage)
    safe_services, service_signatures = _safe_services(
        services, known_service_names=known_service_names
    )
    warning_signatures = sorted(
        f"system.{warning['code']}"
        for warning in safe_usage["warnings"]
        if warning.get("code")
    )

    return {
        "schema_version": PACKAGE_SCHEMA_VERSION,
        "generated_at": generated_at.isoformat(),
        "runtime": {
            "version": version,
            "game": game,
            "server_number": server_number,
        },
        "health": {
            "system": safe_usage["status"],
            "services": {
                "running": sum(item["state"] == "RUNNING" for item in safe_services),
                "stopped": sum(item["state"] == "STOPPED" for item in safe_services),
                "failed": sum(item["state"] in {"FATAL", "EXITED"} for item in safe_services),
            },
        },
        "system_usage": safe_usage,
        "services": safe_services,
        "error_signatures": warning_signatures + service_signatures,
        "privacy": {
            "included": [
                "version and game profile",
                "aggregate CPU, memory and disk metrics",
                "bounded service states and uptime",
                "generic health warning codes",
            ],
            "omitted": [
                "raw logs and error text",
                "player names, Steam IDs and chat content",
                "hostnames, URLs and IP addresses",
                "passwords, tokens, webhook values and configuration",
                "process IDs and command lines",
            ],
        },
    }


def preview_support_diagnostics(package: dict[str, Any]) -> dict[str, Any]:
    """Describe the exact export scope and its deterministic JSON size."""

    encoded = json.dumps(package, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    privacy = package["privacy"]
    return {
        "format": "JSON",
        "estimated_bytes": len(encoded),
        "included": privacy["included"],
        "omitted": privacy["omitted"],
        "error_signature_count": len(package["error_signatures"]),
        "service_count": len(package["services"]),
        "history_samples": len(package["system_usage"]["history"]),
    }
