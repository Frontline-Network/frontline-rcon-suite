from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

from rcon.system_usage import (
    SystemUsageSampler,
    collect_system_usage,
    parse_cpuset,
)

GIB = 1024**3


class FakePsutil:
    def __init__(
        self,
        *,
        host_cores=8,
        host_cpu_percent=44.0,
        memory_used=4 * GIB,
        memory_total=8 * GIB,
        disk_used=50 * GIB,
        disk_total=100 * GIB,
    ):
        self.host_cores = host_cores
        self.host_cpu_percent = host_cpu_percent
        self.memory_used = memory_used
        self.memory_total = memory_total
        self.disk_used = disk_used
        self.disk_total = disk_total

    def cpu_count(self):
        return self.host_cores

    def cpu_percent(self, interval=None):
        assert interval is None
        return self.host_cpu_percent

    def virtual_memory(self):
        return SimpleNamespace(total=self.memory_total, used=self.memory_used)

    def disk_usage(self, path):
        assert path == "/"
        return SimpleNamespace(total=self.disk_total, used=self.disk_used)

    def pids(self):
        return [1, 2, 3]


class UnavailablePsutil:
    def _fail(self, *args, **kwargs):
        raise OSError("metric unavailable")

    cpu_count = _fail
    cpu_percent = _fail
    virtual_memory = _fail
    disk_usage = _fail
    pids = _fail


def reader(values):
    return lambda path: values.get(path.as_posix())


def test_parse_cpuset_counts_ranges_and_rejects_invalid_values():
    assert parse_cpuset("0-3,6,8-9") == 7
    assert parse_cpuset("2") == 1
    assert parse_cpuset("3-1") is None
    assert parse_cpuset("invalid") is None
    assert parse_cpuset(None) is None


def test_collect_system_usage_uses_container_limits_and_cpu_delta():
    values = {
        "/sys/fs/cgroup/cpu.max": "200000 100000",
        "/sys/fs/cgroup/cpu.stat": "usage_usec 1000000\nuser_usec 600000",
        "/sys/fs/cgroup/cpuset.cpus.effective": "0-3",
        "/sys/fs/cgroup/memory.current": str(1 * GIB),
        "/sys/fs/cgroup/memory.max": str(2 * GIB),
    }

    sample, raw = collect_system_usage(
        {"cpu_usage_seconds": 0.5, "monotonic": 5.0},
        sampled_at=datetime(2026, 8, 20, 12, tzinfo=timezone.utc),
        monotonic_now=10.0,
        read_text=reader(values),
        psutil_module=FakePsutil(),
    )

    assert sample["cpu_usage"] == {
        "available": True,
        "percent": 5.0,
        "used": 0.1,
        "total": 2.0,
        "unit": "cores",
        "source": "cgroup_v2",
        "severity": "ok",
        "cores": 2.0,
        "host_cores": 8,
        "quota_cores": 2.0,
        "process_count": 3,
    }
    assert sample["ram_usage"]["source"] == "cgroup_v2"
    assert sample["ram_usage"]["used"] == 1.0
    assert sample["ram_usage"]["total"] == 2.0
    assert sample["ram_usage"]["percent"] == 50.0
    assert sample["disk_usage"]["percent"] == 50.0
    assert sample["status"] == "ok"
    assert sample["warnings"] == []
    assert raw == {"cpu_usage_seconds": 1.0, "monotonic": 10.0}


def test_first_container_cpu_sample_is_unknown_instead_of_invented_zero():
    sample, raw = collect_system_usage(
        sampled_at=datetime(2026, 8, 20, 12, tzinfo=timezone.utc),
        monotonic_now=10.0,
        read_text=reader(
            {
                "/sys/fs/cgroup/cpu.max": "200000 100000",
                "/sys/fs/cgroup/cpu.stat": "usage_usec 1000000",
            }
        ),
        psutil_module=FakePsutil(),
    )

    assert sample["cpu_usage"]["available"] is False
    assert sample["cpu_usage"]["percent"] is None
    assert sample["cpu_usage"]["source"] == "cgroup_v2"
    assert sample["status"] == "partial"
    assert raw == {"cpu_usage_seconds": 1.0, "monotonic": 10.0}


def test_unlimited_cgroup_memory_falls_back_to_truthful_host_values():
    sample, _ = collect_system_usage(
        sampled_at=datetime(2026, 8, 20, 12, tzinfo=timezone.utc),
        monotonic_now=10.0,
        read_text=reader(
            {
                "/sys/fs/cgroup/memory.current": str(1 * GIB),
                "/sys/fs/cgroup/memory.max": "max",
            }
        ),
        psutil_module=FakePsutil(),
    )

    assert sample["ram_usage"]["source"] == "host"
    assert sample["ram_usage"]["used"] == 4.0
    assert sample["ram_usage"]["total"] == 8.0
    assert sample["ram_usage"]["percent"] == 50.0


def test_unavailable_metrics_never_become_invented_zero_values():
    sample, _ = collect_system_usage(
        sampled_at=datetime(2026, 8, 20, 12, tzinfo=timezone.utc),
        monotonic_now=10.0,
        read_text=lambda path: None,
        psutil_module=UnavailablePsutil(),
    )

    assert sample["status"] == "unavailable"
    for name in ("cpu_usage", "ram_usage", "disk_usage"):
        assert sample[name]["available"] is False
        assert sample[name]["percent"] is None
        assert sample[name]["used"] is None
        assert sample[name]["total"] is None


def test_warning_contract_is_explainable_and_threshold_backed():
    sample, _ = collect_system_usage(
        sampled_at=datetime(2026, 8, 20, 12, tzinfo=timezone.utc),
        monotonic_now=10.0,
        read_text=lambda path: None,
        psutil_module=FakePsutil(memory_used=95 * GIB, memory_total=100 * GIB),
    )

    assert sample["status"] == "critical"
    assert {
        "metric": "ram",
        "severity": "critical",
        "code": "ram_critical",
        "threshold_percent": 90.0,
    } in sample["warnings"]


def test_sampler_bounds_collection_rate_and_returns_history_and_data_age():
    monotonic_values = iter([0.0, 5.0, 15.0])
    start = datetime(2026, 8, 20, 12, tzinfo=timezone.utc)
    now_values = iter(
        [start, start + timedelta(seconds=5), start + timedelta(seconds=15)]
    )
    collector_calls = []

    def collector(previous_raw, *, sampled_at, monotonic_now):
        collector_calls.append((previous_raw, sampled_at, monotonic_now))
        percent = 10.0 * len(collector_calls)
        sample = {
            "sampled_at": sampled_at.isoformat(),
            "status": "ok",
            "warnings": [],
            "cpu_usage": {"percent": percent},
            "ram_usage": {"percent": 20.0},
            "disk_usage": {"percent": 30.0},
        }
        return sample, {"sequence": len(collector_calls)}

    sampler = SystemUsageSampler(
        interval_seconds=15,
        max_history_samples=3,
        collector=collector,
        monotonic=lambda: next(monotonic_values),
        now=lambda: next(now_values),
    )

    first = sampler.get_snapshot()
    cached = sampler.get_snapshot()
    second = sampler.get_snapshot()

    assert len(collector_calls) == 2
    assert first["cache_hit"] is False
    assert cached["cache_hit"] is True
    assert cached["data_age_seconds"] == 5.0
    assert second["cache_hit"] is False
    assert second["poll_after_seconds"] == 15
    assert second["range"]["seconds"] == 15.0
    assert second["range"]["max_samples"] == 3
    assert [item["cpu_percent"] for item in second["history"]] == [10.0, 20.0]
