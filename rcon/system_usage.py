from __future__ import annotations

import copy
import threading
import time
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import psutil

SAMPLE_INTERVAL_SECONDS = 15
HISTORY_WINDOW_SECONDS = 60 * 60
MAX_HISTORY_SAMPLES = HISTORY_WINDOW_SECONDS // SAMPLE_INTERVAL_SECONDS + 1
WARNING_THRESHOLD_PERCENT = 80.0
CRITICAL_THRESHOLD_PERCENT = 90.0

CGROUP_V2_CPU_MAX = (Path("/sys/fs/cgroup/cpu.max"),)
CGROUP_V2_CPU_STAT = (Path("/sys/fs/cgroup/cpu.stat"),)
CGROUP_V2_CPUSET = (
    Path("/sys/fs/cgroup/cpuset.cpus.effective"),
    Path("/sys/fs/cgroup/cpuset.cpus"),
)
CGROUP_V2_MEMORY_CURRENT = (Path("/sys/fs/cgroup/memory.current"),)
CGROUP_V2_MEMORY_MAX = (Path("/sys/fs/cgroup/memory.max"),)

CGROUP_V1_CPU_QUOTA = (Path("/sys/fs/cgroup/cpu/cpu.cfs_quota_us"),)
CGROUP_V1_CPU_PERIOD = (Path("/sys/fs/cgroup/cpu/cpu.cfs_period_us"),)
CGROUP_V1_CPU_USAGE = (Path("/sys/fs/cgroup/cpuacct/cpuacct.usage"),)
CGROUP_V1_CPUSET = (Path("/sys/fs/cgroup/cpuset/cpuset.cpus"),)
CGROUP_V1_MEMORY_CURRENT = (Path("/sys/fs/cgroup/memory/memory.usage_in_bytes"),)
CGROUP_V1_MEMORY_MAX = (Path("/sys/fs/cgroup/memory/memory.limit_in_bytes"),)


def _read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8").strip()
    except (OSError, UnicodeError):
        return None


def _read_first(
    paths: tuple[Path, ...], read_text: Callable[[Path], str | None]
) -> str | None:
    for path in paths:
        value = read_text(path)
        if value is not None:
            return value
    return None


def _as_int(value: str | None) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def parse_cpuset(value: str | None) -> int | None:
    """Return the number of unique CPUs in a Linux cpuset expression."""

    if not value:
        return None
    cpus: set[int] = set()
    try:
        for segment in value.split(","):
            bounds = segment.strip().split("-", 1)
            start = int(bounds[0])
            end = int(bounds[-1])
            if end < start:
                return None
            cpus.update(range(start, end + 1))
    except (TypeError, ValueError):
        return None
    return len(cpus) or None


def _finite_memory_limit(value: str | None, host_total: int) -> int | None:
    if not value or value == "max":
        return None
    limit = _as_int(value)
    if not limit or limit <= 0 or limit >= 2**60:
        return None
    return min(limit, host_total) if host_total > 0 else limit


def _severity(percent: float | None) -> str:
    if percent is None:
        return "unknown"
    if percent >= CRITICAL_THRESHOLD_PERCENT:
        return "critical"
    if percent >= WARNING_THRESHOLD_PERCENT:
        return "warning"
    return "ok"


def _percent(used: float | int | None, total: float | int | None) -> float | None:
    if used is None or total is None or total <= 0:
        return None
    return round(max(0.0, min(100.0, float(used) / float(total) * 100.0)), 2)


def _metric(
    *,
    percent: float | None,
    source: str,
    used: float | None = None,
    total: float | None = None,
    unit: str | None = None,
    **extra: Any,
) -> dict[str, Any]:
    return {
        "available": percent is not None,
        "percent": percent,
        "used": used,
        "total": total,
        "unit": unit,
        "source": source,
        "severity": _severity(percent),
        **extra,
    }


def _cpu_capacity(
    host_cores: int,
    read_text: Callable[[Path], str | None],
) -> tuple[float | None, str, float | None]:
    limits: list[float] = []
    quota_cores: float | None = None
    source = "host"

    cpu_max = _read_first(CGROUP_V2_CPU_MAX, read_text)
    if cpu_max:
        parts = cpu_max.split()
        if len(parts) == 2 and parts[0] != "max":
            quota = _as_int(parts[0])
            period = _as_int(parts[1])
            if quota and period and quota > 0 and period > 0:
                quota_cores = quota / period
                limits.append(quota_cores)
                source = "cgroup_v2"
    else:
        quota = _as_int(_read_first(CGROUP_V1_CPU_QUOTA, read_text))
        period = _as_int(_read_first(CGROUP_V1_CPU_PERIOD, read_text))
        if quota and period and quota > 0 and period > 0:
            quota_cores = quota / period
            limits.append(quota_cores)
            source = "cgroup_v1"

    cpuset_value = _read_first(CGROUP_V2_CPUSET, read_text)
    cpuset_source = "cgroup_v2"
    if cpuset_value is None:
        cpuset_value = _read_first(CGROUP_V1_CPUSET, read_text)
        cpuset_source = "cgroup_v1"
    cpuset_cores = parse_cpuset(cpuset_value)
    if cpuset_cores:
        limits.append(float(cpuset_cores))
        source = cpuset_source

    if host_cores > 0:
        limits.append(float(host_cores))
    return (min(limits) if limits else None, source, quota_cores)


def _cgroup_cpu_usage_seconds(
    read_text: Callable[[Path], str | None],
) -> tuple[float | None, str | None]:
    cpu_stat = _read_first(CGROUP_V2_CPU_STAT, read_text)
    if cpu_stat:
        for line in cpu_stat.splitlines():
            key, _, value = line.partition(" ")
            if key == "usage_usec":
                usage_usec = _as_int(value.strip())
                if usage_usec is not None:
                    return usage_usec / 1_000_000.0, "cgroup_v2"

    usage_ns = _as_int(_read_first(CGROUP_V1_CPU_USAGE, read_text))
    if usage_ns is not None:
        return usage_ns / 1_000_000_000.0, "cgroup_v1"
    return None, None


def _memory_values(
    psutil_module: Any,
    read_text: Callable[[Path], str | None],
) -> tuple[int | None, int | None, str]:
    try:
        host_memory = psutil_module.virtual_memory()
        host_total = int(host_memory.total)
        host_used = int(host_memory.used)
    except Exception:
        host_total = 0
        host_used = 0

    current = _as_int(_read_first(CGROUP_V2_MEMORY_CURRENT, read_text))
    limit = _finite_memory_limit(
        _read_first(CGROUP_V2_MEMORY_MAX, read_text), host_total
    )
    source = "cgroup_v2"
    if current is None or limit is None:
        current = _as_int(_read_first(CGROUP_V1_MEMORY_CURRENT, read_text))
        limit = _finite_memory_limit(
            _read_first(CGROUP_V1_MEMORY_MAX, read_text), host_total
        )
        source = "cgroup_v1"

    if current is not None and limit is not None:
        return min(current, limit), limit, source
    if host_total > 0:
        return min(host_used, host_total), host_total, "host"
    return None, None, "unavailable"


def collect_system_usage(
    previous_raw: dict[str, Any] | None = None,
    *,
    sampled_at: datetime | None = None,
    monotonic_now: float | None = None,
    read_text: Callable[[Path], str | None] = _read_text,
    psutil_module: Any = psutil,
) -> tuple[dict[str, Any], dict[str, Any]]:
    sampled_at = sampled_at or datetime.now(timezone.utc)
    monotonic_now = time.monotonic() if monotonic_now is None else monotonic_now
    previous_raw = previous_raw or {}

    try:
        host_cores = int(psutil_module.cpu_count() or 0)
    except Exception:
        host_cores = 0
    total_cores, capacity_source, quota_cores = _cpu_capacity(host_cores, read_text)
    cpu_usage_seconds, usage_source = _cgroup_cpu_usage_seconds(read_text)
    cpu_percent: float | None = None
    cpu_source = usage_source or capacity_source
    previous_cpu_usage = previous_raw.get("cpu_usage_seconds")
    previous_monotonic = previous_raw.get("monotonic")
    if (
        cpu_usage_seconds is not None
        and previous_cpu_usage is not None
        and previous_monotonic is not None
        and monotonic_now > previous_monotonic
        and total_cores
        and total_cores > 0
    ):
        usage_delta = max(0.0, cpu_usage_seconds - previous_cpu_usage)
        elapsed = monotonic_now - previous_monotonic
        cpu_percent = round(
            max(0.0, min(100.0, usage_delta / elapsed / total_cores * 100.0)),
            2,
        )
    elif cpu_usage_seconds is None:
        try:
            cpu_percent = round(float(psutil_module.cpu_percent(interval=None)), 2)
            cpu_source = "host"
        except Exception:
            cpu_percent = None
            cpu_source = "unavailable"

    used_cores = (
        round(total_cores * cpu_percent / 100.0, 3)
        if total_cores is not None and cpu_percent is not None
        else None
    )
    try:
        process_count = len(psutil_module.pids())
    except Exception:
        process_count = None
    cpu = _metric(
        percent=cpu_percent,
        source=cpu_source,
        used=used_cores,
        total=round(total_cores, 3) if total_cores is not None else None,
        unit="cores",
        cores=round(total_cores, 3) if total_cores is not None else None,
        host_cores=host_cores or None,
        quota_cores=round(quota_cores, 3) if quota_cores is not None else None,
        process_count=process_count,
    )

    memory_used, memory_total, memory_source = _memory_values(psutil_module, read_text)
    memory_percent = _percent(memory_used, memory_total)
    gibibyte = 1024**3
    ram = _metric(
        percent=memory_percent,
        source=memory_source,
        used=round(memory_used / gibibyte, 3) if memory_used is not None else None,
        total=round(memory_total / gibibyte, 3) if memory_total is not None else None,
        unit="GiB",
        used_bytes=memory_used,
        total_bytes=memory_total,
    )

    try:
        disk_values = psutil_module.disk_usage("/")
        disk_used = int(disk_values.used)
        disk_total = int(disk_values.total)
        disk_percent = _percent(disk_used, disk_total)
        disk_source = "filesystem"
    except Exception:
        disk_used = None
        disk_total = None
        disk_percent = None
        disk_source = "unavailable"
    disk = _metric(
        percent=disk_percent,
        source=disk_source,
        used=round(disk_used / gibibyte, 3) if disk_used is not None else None,
        total=round(disk_total / gibibyte, 3) if disk_total is not None else None,
        unit="GiB",
        used_bytes=disk_used,
        total_bytes=disk_total,
    )

    metrics = {"cpu_usage": cpu, "ram_usage": ram, "disk_usage": disk}
    warnings = [
        {
            "metric": name.removesuffix("_usage"),
            "severity": metric["severity"],
            "code": f"{name.removesuffix('_usage')}_{metric['severity']}",
            "threshold_percent": (
                CRITICAL_THRESHOLD_PERCENT
                if metric["severity"] == "critical"
                else WARNING_THRESHOLD_PERCENT
            ),
        }
        for name, metric in metrics.items()
        if metric["severity"] in {"warning", "critical"}
    ]
    severities = {metric["severity"] for metric in metrics.values()}
    if severities == {"unknown"}:
        status = "unavailable"
    elif "critical" in severities:
        status = "critical"
    elif "warning" in severities:
        status = "warning"
    elif "unknown" in severities:
        status = "partial"
    else:
        status = "ok"

    sample = {
        "sampled_at": sampled_at.isoformat(),
        "status": status,
        "warnings": warnings,
        **metrics,
    }
    raw = {
        "cpu_usage_seconds": cpu_usage_seconds,
        "monotonic": monotonic_now,
    }
    return sample, raw


class SystemUsageSampler:
    """Bound expensive host/container inspection independently of UI clients."""

    def __init__(
        self,
        *,
        interval_seconds: int = SAMPLE_INTERVAL_SECONDS,
        max_history_samples: int = MAX_HISTORY_SAMPLES,
        collector: Callable[
            ..., tuple[dict[str, Any], dict[str, Any]]
        ] = collect_system_usage,
        monotonic: Callable[[], float] = time.monotonic,
        now: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    ):
        self.interval_seconds = interval_seconds
        self._collector = collector
        self._monotonic = monotonic
        self._now = now
        self._history: deque[dict[str, Any]] = deque(maxlen=max_history_samples)
        self._last_sample: dict[str, Any] | None = None
        self._last_raw: dict[str, Any] | None = None
        self._last_monotonic: float | None = None
        self._lock = threading.Lock()

    def _response(
        self,
        *,
        cache_hit: bool,
        generated_at: datetime,
        window_seconds: int | None = None,
    ) -> dict[str, Any]:
        if self._last_sample is None:
            raise RuntimeError("No system-usage sample is available")
        response = copy.deepcopy(self._last_sample)
        sampled_at = datetime.fromisoformat(response["sampled_at"])
        history = copy.deepcopy(list(self._history))
        if window_seconds is not None:
            cutoff = generated_at.timestamp() - window_seconds
            history = [
                entry
                for entry in history
                if datetime.fromisoformat(entry["sampled_at"]).timestamp() >= cutoff
            ]
        history_from = history[0]["sampled_at"] if history else response["sampled_at"]
        response.update(
            {
                "schema_version": 2,
                "generated_at": generated_at.isoformat(),
                "data_age_seconds": round(
                    max(0.0, (generated_at - sampled_at).total_seconds()), 3
                ),
                "cache_hit": cache_hit,
                "poll_after_seconds": self.interval_seconds,
                "history": history,
                "range": {
                    "from": history_from,
                    "to": response["sampled_at"],
                    "seconds": max(
                        0.0,
                        (
                            datetime.fromisoformat(response["sampled_at"])
                            - datetime.fromisoformat(history_from)
                        ).total_seconds(),
                    ),
                    "sample_interval_seconds": self.interval_seconds,
                    "max_samples": self._history.maxlen,
                },
            }
        )
        return response

    def get_snapshot(self, *, window_seconds: int | None = None) -> dict[str, Any]:
        with self._lock:
            monotonic_now = self._monotonic()
            generated_at = self._now()
            if (
                self._last_sample is not None
                and self._last_monotonic is not None
                and monotonic_now - self._last_monotonic < self.interval_seconds
            ):
                return self._response(
                    cache_hit=True,
                    generated_at=generated_at,
                    window_seconds=window_seconds,
                )

            sample, raw = self._collector(
                self._last_raw,
                sampled_at=generated_at,
                monotonic_now=monotonic_now,
            )
            self._last_sample = sample
            self._last_raw = raw
            self._last_monotonic = monotonic_now
            self._history.append(
                {
                    "sampled_at": sample["sampled_at"],
                    "cpu_percent": sample["cpu_usage"]["percent"],
                    "ram_percent": sample["ram_usage"]["percent"],
                    "disk_percent": sample["disk_usage"]["percent"],
                    "status": sample["status"],
                }
            )
            return self._response(
                cache_hit=False,
                generated_at=generated_at,
                window_seconds=window_seconds,
            )


system_usage_sampler = SystemUsageSampler()
