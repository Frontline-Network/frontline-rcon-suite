from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from rcon.system_usage import (
    SystemUsageSampler,
    collect_system_usage,
    parse_cpuset,
)

GIB = 1024**3
NOW = datetime(2026, 11, 27, 12, tzinfo=timezone.utc)


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


def installation_snapshot():
    return {
        "schema_version": 1,
        "sampled_at": NOW.isoformat(),
        "server_number": 3,
        "complete": True,
        "dedicated_components": [
            {"service": "backend_3", "used_bytes": GIB, "limit_bytes": 2 * GIB, "reclaimable_bytes": GIB // 4},
            {"service": "supervisor_3", "used_bytes": 2 * GIB, "limit_bytes": None, "reclaimable_bytes": GIB // 4},
        ],
        "shared_components": [
            {"service": "redis", "used_bytes": GIB, "limit_bytes": None, "reclaimable_bytes": 0},
            {"service": "postgres", "used_bytes": 2 * GIB, "limit_bytes": None, "reclaimable_bytes": GIB // 2},
        ],
    }


def snapshot_file(monkeypatch, tmp_path, document):
    path = tmp_path / "installation-memory.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    monkeypatch.setenv("HLL_RESOURCE_USAGE_FILE", str(path))
    monkeypatch.setenv("SERVER_NUMBER", "3")
    return path


def collect_snapshot(*, now=NOW):
    return collect_system_usage(
        sampled_at=now, monotonic_now=10,
        psutil_module=FakePsutil(memory_used=4 * GIB, memory_total=32 * GIB),
        read_text=reader({
            "/sys/fs/cgroup/memory.current": str(GIB // 2),
            "/sys/fs/cgroup/memory.max": str(GIB),
        }),
    )[0]


def test_rcon_sum_is_absolute_and_includes_shared_services_exactly_once(monkeypatch, tmp_path):
    snapshot_file(monkeypatch, tmp_path, installation_snapshot())
    sample = collect_snapshot()
    rcon = sample["rcon_ram_usage"]
    assert rcon["available"] is True
    assert rcon["source"] == "rcon_services"
    assert rcon["accounting"] == "cgroup_memory_current"
    assert rcon["used_bytes"] == 6 * GIB and rcon["used"] == 6.0
    assert rcon["dedicated_used_bytes"] == rcon["shared_used_bytes"] == 3 * GIB
    assert rcon["total_bytes"] is None and rcon["total"] is None and rcon["percent"] is None
    assert rcon["reclaimable_bytes"] == GIB
    assert rcon["working_set_bytes"] == 5 * GIB
    assert [c["scope"] for c in rcon["components"]] == ["dedicated", "dedicated", "shared", "shared"]
    assert rcon["sampled_at"] == NOW.isoformat() and rcon["data_age_seconds"] == 0
    # The existing field remains backend/container memory, not the installation sum.
    assert sample["ram_usage"]["source"] == "cgroup_v2"
    assert sample["ram_usage"]["used_bytes"] == GIB // 2
    assert sample["ram_usage"]["total_bytes"] == GIB
    assert sample["ram_usage"]["percent"] == 50.0


def test_missing_installation_source_never_inherits_backend_or_host_memory(monkeypatch):
    monkeypatch.delenv("HLL_RESOURCE_USAGE_FILE", raising=False)
    sample = collect_snapshot()
    assert sample["ram_usage"]["available"] is True
    assert sample["rcon_ram_usage"]["available"] is False
    assert sample["rcon_ram_usage"]["reason"] == "not_configured"
    assert sample["rcon_ram_usage"]["used_bytes"] is None
    assert sample["rcon_ram_usage"]["components"] == []


def test_installation_snapshot_is_independent_of_unavailable_local_metrics(monkeypatch, tmp_path):
    snapshot_file(monkeypatch, tmp_path, installation_snapshot())
    sample, _ = collect_system_usage(sampled_at=NOW, monotonic_now=10,
        read_text=lambda path: None, psutil_module=UnavailablePsutil())
    assert sample["ram_usage"]["available"] is False
    assert sample["rcon_ram_usage"]["available"] is True
    assert sample["rcon_ram_usage"]["used_bytes"] == 6 * GIB


def test_known_stopped_components_are_valid_zero_not_unknown(monkeypatch, tmp_path):
    document = installation_snapshot()
    for item in document["dedicated_components"] + document["shared_components"]:
        item.update(used_bytes=0, reclaimable_bytes=0, limit_bytes=None)
    snapshot_file(monkeypatch, tmp_path, document)
    result = collect_snapshot()["rcon_ram_usage"]
    assert result["available"] is True and result["used_bytes"] == 0
    assert result["used"] == 0.0 and result["percent"] is None


@pytest.mark.parametrize("age,valid,reason", [
    (60, True, None), (60.001, False, "stale"),
    (-5, True, None), (-5.001, False, "future_timestamp"),
])
def test_installation_snapshot_enforces_age_bounds(monkeypatch, tmp_path, age, valid, reason):
    document = installation_snapshot()
    document["sampled_at"] = (NOW - timedelta(seconds=age)).isoformat()
    snapshot_file(monkeypatch, tmp_path, document)
    result = collect_snapshot()["rcon_ram_usage"]
    assert result["available"] is valid
    assert result["reason"] == reason


@pytest.mark.parametrize("change,reason", [
    (lambda d: d.update(schema_version=True), "invalid_schema"),
    (lambda d: d.update(server_number=4), "wrong_server"),
    (lambda d: d.update(server_number=True), "wrong_server"),
    (lambda d: d.update(complete=False, dedicated_components=None), "incomplete"),
    (lambda d: d.pop("complete"), "incomplete"),
    (lambda d: d.update(dedicated_components=[]), "incomplete"),
    (lambda d: d.pop("shared_components"), "incomplete"),
    (lambda d: d.update(sampled_at="2026-11-27T12:00:00"), "invalid_timestamp"),
    (lambda d: d.update(sampled_at="2026-11-27T13:00:00+01:00"), "invalid_timestamp"),
    (lambda d: d["shared_components"].append(dict(d["dedicated_components"][0])), "duplicate_service"),
    (lambda d: d["dedicated_components"][0].update(used_bytes=-1), "invalid_component"),
    (lambda d: d["dedicated_components"][0].update(used_bytes=True), "invalid_component"),
    (lambda d: d["dedicated_components"][0].update(used_bytes=1.0), "invalid_component"),
    (lambda d: d["dedicated_components"][0].pop("limit_bytes"), "invalid_component"),
    (lambda d: d["dedicated_components"][0].update(limit_bytes=False), "invalid_component"),
    (lambda d: d["dedicated_components"][0].update(reclaimable_bytes=2 * GIB), "invalid_component"),
])
def test_invalid_or_partial_installation_data_is_explicitly_unavailable(monkeypatch, tmp_path, change, reason):
    document = installation_snapshot()
    change(document)
    snapshot_file(monkeypatch, tmp_path, document)
    sample = collect_snapshot()
    assert sample["rcon_ram_usage"]["available"] is False
    assert sample["rcon_ram_usage"]["reason"] == reason
    assert sample["rcon_ram_usage"]["used_bytes"] is None
    assert sample["ram_usage"]["used_bytes"] == GIB // 2


def test_optional_reclaimable_breakdown_does_not_change_charged_sum(monkeypatch, tmp_path):
    document = installation_snapshot()
    document["shared_components"][0].pop("reclaimable_bytes")
    snapshot_file(monkeypatch, tmp_path, document)
    result = collect_snapshot()["rcon_ram_usage"]
    assert result["available"] is True and result["used_bytes"] == 6 * GIB
    assert result["reclaimable_bytes"] is None and result["working_set_bytes"] is None


def test_component_count_and_file_size_are_bounded(monkeypatch, tmp_path):
    document = installation_snapshot()
    document["dedicated_components"] = [{"service": "backend_3", "used_bytes": 0, "limit_bytes": None}]
    document["shared_components"] = [{"service": f"shared_{n}", "used_bytes": 1, "limit_bytes": None} for n in range(63)]
    path = snapshot_file(monkeypatch, tmp_path, document)
    assert collect_snapshot()["rcon_ram_usage"]["used_bytes"] == 63
    document["shared_components"].append({"service": "overflow", "used_bytes": 1, "limit_bytes": None})
    path.write_text(json.dumps(document))
    assert collect_snapshot()["rcon_ram_usage"]["reason"] == "too_many_components"
    raw = json.dumps(installation_snapshot()).encode()
    path.write_bytes(raw + b" " * (32768 - len(raw)))
    assert collect_snapshot()["rcon_ram_usage"]["available"] is True
    with path.open("ab") as stream:
        stream.write(b" ")
    assert collect_snapshot()["rcon_ram_usage"]["reason"] == "too_large"


def test_unreadable_and_malformed_files_are_not_zero_usage(monkeypatch, tmp_path):
    path = snapshot_file(monkeypatch, tmp_path, installation_snapshot())
    path.write_bytes(b"not-json")
    assert collect_snapshot()["rcon_ram_usage"]["reason"] == "invalid_json"
    path.unlink()
    assert collect_snapshot()["rcon_ram_usage"]["reason"] == "unreadable"
    monkeypatch.setenv("HLL_RESOURCE_USAGE_FILE", str(tmp_path))
    assert collect_snapshot()["rcon_ram_usage"]["available"] is False


@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="POSIX named pipe")
def test_a_configured_fifo_is_rejected_without_waiting_for_a_writer(monkeypatch, tmp_path):
    path = tmp_path / "snapshot.fifo"
    os.mkfifo(path)
    monkeypatch.setenv("HLL_RESOURCE_USAGE_FILE", str(path))
    assert collect_snapshot()["rcon_ram_usage"]["reason"] == "not_regular_file"


def test_snapshot_server_defaults_to_one(monkeypatch, tmp_path):
    document = installation_snapshot()
    document["server_number"] = 1
    snapshot_file(monkeypatch, tmp_path, document)
    monkeypatch.delenv("SERVER_NUMBER")
    assert collect_snapshot()["rcon_ram_usage"]["available"] is True


def test_cached_response_expires_installation_data_without_extra_collection(monkeypatch, tmp_path):
    document = installation_snapshot()
    document["sampled_at"] = (NOW - timedelta(seconds=59)).isoformat()
    snapshot_file(monkeypatch, tmp_path, document)
    monotonic_values = iter([0, 1, 2])
    now_values = iter([NOW, NOW + timedelta(seconds=1), NOW + timedelta(seconds=2)])
    calls = []

    def collector(previous, *, sampled_at, monotonic_now):
        calls.append(1)
        return collect_snapshot(now=sampled_at), {}

    sampler = SystemUsageSampler(collector=collector, monotonic=lambda: next(monotonic_values), now=lambda: next(now_values))
    first = sampler.get_snapshot()
    first["rcon_ram_usage"]["components"][0]["used_bytes"] = -1
    first["history"][0]["rcon_ram_used_bytes"] = -1
    second = sampler.get_snapshot()
    assert second["rcon_ram_usage"]["available"] is True
    assert second["rcon_ram_usage"]["components"][0]["used_bytes"] == GIB
    assert second["history"][0]["rcon_ram_used_bytes"] == 6 * GIB
    third = sampler.get_snapshot()
    assert third["cache_hit"] is True and len(calls) == 1
    assert third["rcon_ram_usage"]["available"] is False
    assert third["rcon_ram_usage"]["reason"] == "stale"
    assert third["ram_usage"]["used_bytes"] == GIB // 2


def test_installation_history_remains_bounded_and_records_missing_samples(monkeypatch, tmp_path):
    path = snapshot_file(monkeypatch, tmp_path, installation_snapshot())
    monotonic_values = iter([0, 15, 30])
    now_values = iter([NOW, NOW + timedelta(seconds=15), NOW + timedelta(seconds=30)])

    def collector(previous, *, sampled_at, monotonic_now):
        return collect_snapshot(now=sampled_at), {}

    sampler = SystemUsageSampler(max_history_samples=2, collector=collector,
        monotonic=lambda: next(monotonic_values), now=lambda: next(now_values))
    sampler.get_snapshot()
    path.unlink()
    missing = sampler.get_snapshot()
    assert [h["rcon_ram_used_bytes"] for h in missing["history"]] == [6 * GIB, None]
    snapshot_file(monkeypatch, tmp_path, installation_snapshot())
    last = sampler.get_snapshot()
    assert len(last["history"]) == 2
    assert [h["rcon_ram_used_bytes"] for h in last["history"]] == [None, 6 * GIB]


def snapshot_with_file_cache():
    document = installation_snapshot()
    for component, file_cache in zip(
        document["dedicated_components"] + document["shared_components"],
        [GIB // 4, GIB // 2, 0, 3 * GIB // 2],
    ):
        component["file_cache_bytes"] = file_cache
    return document


def assert_service_memory_unknown(metric):
    assert metric["service_ram_available"] is False
    for field in (
        "service_used_bytes", "dedicated_service_used_bytes", "shared_service_used_bytes",
        "file_cache_bytes", "dedicated_file_cache_bytes", "shared_file_cache_bytes",
    ):
        assert metric[field] is None


def test_disk_cache_separates_dedicated_shared_service_ram_without_changing_raw(monkeypatch, tmp_path):
    snapshot_file(monkeypatch, tmp_path, snapshot_with_file_cache())
    sample = collect_snapshot()
    result = sample["rcon_ram_usage"]
    assert result["available"] is True and result["service_ram_available"] is True
    assert result["used_bytes"] == 6 * GIB
    assert result["service_used_bytes"] == 15 * GIB // 4
    assert result["dedicated_service_used_bytes"] == 9 * GIB // 4
    assert result["shared_service_used_bytes"] == 3 * GIB // 2
    assert result["file_cache_bytes"] == 9 * GIB // 4
    assert result["dedicated_file_cache_bytes"] == 3 * GIB // 4
    assert result["shared_file_cache_bytes"] == 3 * GIB // 2
    assert result["reclaimable_bytes"] == GIB
    assert result["working_set_bytes"] == 5 * GIB
    assert result["components"][0]["file_cache_bytes"] == GIB // 4
    assert result["components"][0]["service_used_bytes"] == 3 * GIB // 4
    assert sample["ram_usage"]["used_bytes"] == GIB // 2


def test_active_disk_cache_is_excluded_but_shmem_remains_service_ram(monkeypatch, tmp_path):
    # Example collector input: file=9 GiB (active+inactive), shmem=1 GiB.
    # Only its disk-backed 8 GiB is subtracted, not shmem or merely inactive_file.
    document = installation_snapshot()
    document["dedicated_components"] = [{
        "service": "backend_3", "used_bytes": 10 * GIB,
        "limit_bytes": None, "reclaimable_bytes": GIB,
        "file_cache_bytes": 8 * GIB,
    }]
    document["shared_components"] = []
    snapshot_file(monkeypatch, tmp_path, document)
    result = collect_snapshot()["rcon_ram_usage"]
    assert result["service_used_bytes"] == 2 * GIB
    assert result["file_cache_bytes"] == 8 * GIB
    assert result["working_set_bytes"] == 9 * GIB
    assert result["shared_service_used_bytes"] == result["shared_file_cache_bytes"] == 0


@pytest.mark.parametrize("scope,index,explicit_null", [
    ("dedicated_components", 0, False),
    ("dedicated_components", 1, True),
    ("shared_components", 0, False),
    ("shared_components", 1, True),
])
def test_one_missing_cache_value_keeps_raw_valid_and_service_ram_unknown(monkeypatch, tmp_path, scope, index, explicit_null):
    document = snapshot_with_file_cache()
    if explicit_null:
        document[scope][index]["file_cache_bytes"] = None
    else:
        document[scope][index].pop("file_cache_bytes")
    snapshot_file(monkeypatch, tmp_path, document)
    result = collect_snapshot()["rcon_ram_usage"]
    assert result["available"] is True and result["used_bytes"] == 6 * GIB
    assert_service_memory_unknown(result)
    missing = next(item for item in result["components"] if item["service"] == document[scope][index]["service"])
    assert missing["service_used_bytes"] is None


@pytest.mark.parametrize("cache", [-1, True, False, 1.0, "0", 2 * GIB, 2**63])
def test_invalid_disk_cache_counter_rejects_snapshot(monkeypatch, tmp_path, cache):
    document = snapshot_with_file_cache()
    document["dedicated_components"][0]["file_cache_bytes"] = cache
    snapshot_file(monkeypatch, tmp_path, document)
    result = collect_snapshot()["rcon_ram_usage"]
    assert result["available"] is False and result["reason"] == "invalid_component"
    assert_service_memory_unknown(result)


def test_old_snapshot_with_only_inactive_cache_cannot_claim_service_ram(monkeypatch, tmp_path):
    snapshot_file(monkeypatch, tmp_path, installation_snapshot())
    result = collect_snapshot()["rcon_ram_usage"]
    assert result["available"] is True and result["working_set_bytes"] == 5 * GIB
    assert_service_memory_unknown(result)


def test_known_zero_disk_cache_preserves_all_ram_and_known_stopped_zero(monkeypatch, tmp_path):
    document = snapshot_with_file_cache()
    for item in document["dedicated_components"] + document["shared_components"]:
        item.update(file_cache_bytes=0)
    document["dedicated_components"][0].update(used_bytes=0, reclaimable_bytes=0)
    snapshot_file(monkeypatch, tmp_path, document)
    result = collect_snapshot()["rcon_ram_usage"]
    assert result["service_ram_available"] is True
    assert result["service_used_bytes"] == result["used_bytes"] == 5 * GIB
    assert result["file_cache_bytes"] == 0
    assert result["components"][0]["service_used_bytes"] == 0


def test_disk_cache_can_equal_charge_without_becoming_unavailable(monkeypatch, tmp_path):
    document = snapshot_with_file_cache()
    for item in document["dedicated_components"] + document["shared_components"]:
        item["file_cache_bytes"] = item["used_bytes"]
    snapshot_file(monkeypatch, tmp_path, document)
    result = collect_snapshot()["rcon_ram_usage"]
    assert result["service_ram_available"] is True
    assert result["service_used_bytes"] == 0 and result["file_cache_bytes"] == 6 * GIB


def test_disk_cache_breakdown_does_not_require_inactive_file_counter(monkeypatch, tmp_path):
    document = snapshot_with_file_cache()
    for item in document["dedicated_components"] + document["shared_components"]:
        item.pop("reclaimable_bytes")
    snapshot_file(monkeypatch, tmp_path, document)
    result = collect_snapshot()["rcon_ram_usage"]
    assert result["service_ram_available"] is True
    assert result["service_used_bytes"] == 15 * GIB // 4
    assert result["reclaimable_bytes"] is None and result["working_set_bytes"] is None


def test_cached_snapshot_expiry_invalidates_all_derived_service_values(monkeypatch, tmp_path):
    document = snapshot_with_file_cache()
    document["sampled_at"] = (NOW - timedelta(seconds=59)).isoformat()
    snapshot_file(monkeypatch, tmp_path, document)
    monotonic_values = iter([0, 2])
    now_values = iter([NOW, NOW + timedelta(seconds=2)])
    sampler = SystemUsageSampler(
        collector=lambda previous, *, sampled_at, monotonic_now: (collect_snapshot(now=sampled_at), {}),
        monotonic=lambda: next(monotonic_values), now=lambda: next(now_values),
    )
    first = sampler.get_snapshot()
    assert first["rcon_ram_usage"]["service_ram_available"] is True
    stale = sampler.get_snapshot()
    assert stale["cache_hit"] is True and stale["rcon_ram_usage"]["reason"] == "stale"
    assert_service_memory_unknown(stale["rcon_ram_usage"])
    assert stale["rcon_ram_usage"]["components"] == []


def test_service_history_tracks_dedicated_shared_and_cache_with_unknown_gaps(monkeypatch, tmp_path):
    snapshot_file(monkeypatch, tmp_path, snapshot_with_file_cache())
    monotonic_values = iter([0, 15, 30])
    now_values = iter([NOW, NOW + timedelta(seconds=15), NOW + timedelta(seconds=30)])
    sampler = SystemUsageSampler(
        max_history_samples=2,
        collector=lambda previous, *, sampled_at, monotonic_now: (collect_snapshot(now=sampled_at), {}),
        monotonic=lambda: next(monotonic_values), now=lambda: next(now_values),
    )
    first = sampler.get_snapshot()["history"][0]
    assert first["rcon_service_ram_used_bytes"] == 15 * GIB // 4
    assert first["rcon_dedicated_ram_used_bytes"] == 9 * GIB // 4
    assert first["rcon_shared_ram_used_bytes"] == 3 * GIB // 2
    assert first["rcon_file_cache_bytes"] == 9 * GIB // 4
    snapshot_file(monkeypatch, tmp_path, installation_snapshot())
    old = sampler.get_snapshot()["history"][-1]
    assert old["rcon_ram_used_bytes"] == 6 * GIB
    for field in ("rcon_service_ram_used_bytes", "rcon_dedicated_ram_used_bytes",
                  "rcon_shared_ram_used_bytes", "rcon_file_cache_bytes"):
        assert old[field] is None
    snapshot_file(monkeypatch, tmp_path, snapshot_with_file_cache())
    assert len(sampler.get_snapshot()["history"]) == 2
