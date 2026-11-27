"""Host sampler attribution, failure and secure atomic-file regressions."""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
from types import SimpleNamespace

import pytest

from scripts import collect_rcon_memory as memory


def component(alias="backend", service="backend_3", category="dedicated"):
    return {"service": alias, "project": "rcon", "compose_service": service, "category": category}


def config(*components):
    return {"server_number": 3, "components": list(components or [component()])}


def container(letter="a", *, pid=101, service="backend_3", project="rcon", running=True):
    return {"id": letter * 64, "pid": pid, "running": running,
            "project": project, "compose_service": service}


class Docker:
    def __init__(self, containers):
        self.containers = containers
        self.commands = []

    def __call__(self, command, timeout):
        self.commands.append((command, timeout))
        if command[1] == "ps":
            value = "\n".join(c["id"] for c in self.containers)
        else:
            assert command[1:3] == ["inspect", "--format"]
            assert command[3] == memory.INSPECT_FORMAT
            value = "\n".join(json.dumps(c) for c in self.containers)
        return SimpleNamespace(returncode=0, stdout=value.encode(), stderr=b"not exposed")


@pytest.fixture
def environment(tmp_path):
    proc = tmp_path / "proc"
    groups = tmp_path / "cgroup"
    groups.mkdir()
    return SimpleNamespace(proc=proc, groups=groups)


def install_group(env, record, *, used=1000, limit="2000", inactive=300, version=2):
    pid = env.proc / str(record["pid"])
    pid.mkdir(parents=True)
    if version == 2:
        relative = "/system.slice/docker-" + record["id"] + ".scope"
        group = env.groups / relative.lstrip("/")
        membership = "0::" + relative + "\n"
        filenames = {"memory.current": str(used), "memory.max": str(limit),
                     "memory.stat": "anon 100\ninactive_file " + str(inactive) + "\n"}
    else:
        relative = "/docker/" + record["id"]
        group = env.groups / "memory" / relative.lstrip("/")
        membership = "8:memory:" + relative + "\n"
        filenames = {"memory.usage_in_bytes": str(used), "memory.limit_in_bytes": str(limit),
                     "memory.stat": "inactive_file 1\ntotal_inactive_file " + str(inactive) + "\n"}
    group.mkdir(parents=True)
    (pid / "cgroup").write_text(membership)
    for name, value in filenames.items():
        (group / name).write_text(value)
    return group


def sampler(env, docker, **kwargs):
    return memory.MemoryCollector(runner=docker, proc_root=env.proc, cgroup_root=env.groups,
        utc_now=lambda: datetime(2026, 11, 27, 18, 0, tzinfo=timezone.utc), **kwargs)


def test_v2_reports_full_current_including_reclaimable_file_cache(environment):
    c = container()
    install_group(environment, c)
    docker = Docker([c])
    result = sampler(environment, docker).collect(config())
    assert result == {"schema_version": 1, "server_number": 3, "complete": True,
        "sampled_at": "2026-11-27T18:00:00Z", "shared_components": [],
        "dedicated_components": [{"service": "backend", "used_bytes": 1000,
                                  "limit_bytes": 2000, "reclaimable_bytes": 300}]}
    assert len(docker.commands) == 2
    assert all(".Config.Env" not in str(command) for command, _ in docker.commands)


def test_explicit_selectors_exclude_other_tenants_and_sum_replicas(environment):
    a = container()
    b = container("b", pid=102)
    redis = container("c", pid=103, service="redis")
    foreign = container("d", pid=999, project="other_tenant")
    install_group(environment, a, used=100, limit="1000", inactive=10)
    install_group(environment, b, used=200, limit="2000", inactive=20)
    install_group(environment, redis, used=400, limit="max", inactive=30)
    # No /proc/999 exists: looking at unrelated cgroups would fail the sample.
    result = sampler(environment, Docker([a, b, redis, foreign])).collect(config(
        component(), component("redis", "redis", "shared")))
    assert result["complete"] is True
    assert result["dedicated_components"][0] == {
        "service": "backend", "used_bytes": 300, "limit_bytes": 3000, "reclaimable_bytes": 30}
    assert result["shared_components"][0]["used_bytes"] == 400
    assert result["shared_components"][0]["limit_bytes"] is None


def test_stopped_containers_are_zero_without_reading_a_pid(environment):
    result = sampler(environment, Docker([container(running=False, pid=0)])).collect(config())
    assert result["complete"] is True
    assert result["dedicated_components"][0] == {
        "service": "backend", "used_bytes": 0, "limit_bytes": None, "reclaimable_bytes": 0}


def test_stopped_replica_does_not_remove_a_running_replicas_limit(environment):
    a, stopped = container(), container("b", pid=0, running=False)
    install_group(environment, a)
    result = sampler(environment, Docker([a, stopped])).collect(config())
    assert result["complete"] is True
    assert result["dedicated_components"][0]["limit_bytes"] == 2000


@pytest.mark.parametrize("limit,expected", [("9223372036854771712", None), ("3000", 3000)])
def test_v1_uses_hierarchical_inactive_and_detects_unlimited_memory(environment, limit, expected):
    c = container()
    install_group(environment, c, used=500, limit=limit, inactive=200, version=1)
    result = sampler(environment, Docker([c])).collect(config())
    assert result["complete"] is True
    assert result["dedicated_components"][0] == {
        "service": "backend", "used_bytes": 500, "limit_bytes": expected, "reclaimable_bytes": 200}


def test_hybrid_host_can_use_the_v1_memory_controller(environment):
    c = container()
    install_group(environment, c, version=1)
    membership = environment.proc / str(c["pid"]) / "cgroup"
    membership.write_text("0::/unmounted/docker-" + c["id"] + ".scope\n" + membership.read_text())
    result = sampler(environment, Docker([c])).collect(config())
    assert result["complete"] is True
    assert result["dedicated_components"][0]["used_bytes"] == 1000


@pytest.mark.parametrize("value", ["-1", "1.5", "NaN", str(2**63), str(2**65)])
def test_invalid_memory_counters_are_unknown(environment, value):
    c = container()
    install_group(environment, c, used=value)
    result = sampler(environment, Docker([c])).collect(config())
    assert result["complete"] is False
    assert result["dedicated_components"][0]["used_bytes"] is None


def test_reclaimable_memory_never_exceeds_current(environment):
    c = container()
    install_group(environment, c, inactive=5000)
    result = sampler(environment, Docker([c])).collect(config())
    assert result["dedicated_components"][0]["reclaimable_bytes"] == 1000


def test_replica_totals_cannot_exceed_the_backend_reader_integer_bound(environment):
    a, b = container(), container("b", pid=102)
    for c in (a, b):
        install_group(environment, c, used=2**62, limit="max", inactive=0)
    result = sampler(environment, Docker([a, b])).collect(config())
    assert result["complete"] is False
    assert result["dedicated_components"][0]["used_bytes"] is None


def test_missing_required_selector_is_unknown_and_keeps_all_configured_entries(environment):
    c = container()
    install_group(environment, c)
    result = sampler(environment, Docker([c])).collect(config(component(), component("redis", "redis", "shared")))
    assert result["complete"] is False
    assert result["dedicated_components"][0]["used_bytes"] == 1000
    assert result["shared_components"] == [{"service": "redis", "used_bytes": None,
                                             "limit_bytes": None, "reclaimable_bytes": None}]


def test_missing_counter_file_is_not_zero_or_host_memory(environment):
    c = container()
    group = install_group(environment, c)
    (group / "memory.current").unlink()
    result = sampler(environment, Docker([c])).collect(config())
    assert result["complete"] is False
    assert result["dedicated_components"][0]["used_bytes"] is None


@pytest.mark.parametrize("path", ["/", "/docker/" + "b" * 64,
                                  "/docker/" + "a" * 64 + "/../other"])
def test_wrong_identity_and_traversal_fail_closed(environment, path):
    c = container()
    group = install_group(environment, c)
    (environment.proc / "101" / "cgroup").write_text("0::" + path + "\n")
    result = sampler(environment, Docker([c])).collect(config())
    assert result["complete"] is False
    assert result["dedicated_components"][0]["used_bytes"] is None


def test_membership_is_rechecked_after_reading_to_detect_pid_reuse(environment):
    c = container()
    install_group(environment, c)
    calls = []
    def read(path, maximum):
        if path.name == "cgroup":
            calls.append(path)
            if len(calls) > 1:
                return "0::/docker/" + "b" * 64 + "\n"
        return memory._bounded_read(path, maximum)
    result = sampler(environment, Docker([c]), read_text=read).collect(config())
    assert len(calls) == 2
    assert result["complete"] is False


def test_duplicate_inspect_records_never_double_count_one_container(environment):
    c = container()
    install_group(environment, c)
    result = sampler(environment, Docker([c, c])).collect(config())
    assert result["complete"] is True
    assert result["dedicated_components"][0]["used_bytes"] == 1000


def test_conflicting_container_identity_cannot_be_counted_under_two_aliases(environment):
    c = container()
    install_group(environment, c)
    duplicate = {**c, "compose_service": "redis"}
    result = sampler(environment, Docker([c, duplicate])).collect(config(
        component(), component("redis", "redis", "shared")))
    assert result["complete"] is False
    assert all(row["used_bytes"] is None for group in ["dedicated_components", "shared_components"] for row in result[group])


def test_docker_timeout_still_emits_the_configured_unknown_components(environment):
    def timed_out(_command, _timeout):
        raise TimeoutError("untrusted Docker detail must not reach output")
    result = sampler(environment, timed_out).collect(config())
    assert result["complete"] is False
    assert "untrusted" not in json.dumps(result)


def test_budget_is_bounded_without_sleeping(environment):
    c = container()
    install_group(environment, c)
    clock = [0.0]
    docker = Docker([c])
    def costly(command, timeout):
        clock[0] += 3
        return docker(command, timeout)
    result = sampler(environment, costly, monotonic=lambda: clock[0], budget_seconds=5).collect(config())
    assert result["complete"] is False
    assert len(docker.commands) == 2


@pytest.mark.parametrize("change", [
    lambda c: c.update(server_number=True),
    lambda c: c["components"].append(component()),
    lambda c: c["components"].append(component("other", "backend_3", "shared")),
    lambda c: c["components"][0].update(project="--all"),
    lambda c: c["components"][0].update(service="../other"),
    lambda c: c["components"][0].update(compose_service="backend;env"),
    lambda c: c["components"][0].update(category="host"),
    lambda c: c.update(components=[]),
])
def test_config_rejects_ambiguous_or_unsafe_selectors(change):
    value = config()
    change(value)
    with pytest.raises(memory.CollectorError):
        memory.parse_config(json.dumps(value))


def test_config_limits_and_duplicate_json_fields():
    with pytest.raises(memory.CollectorError):
        memory.parse_config('{"server_number":3,"server_number":4,"components":[]}')
    with pytest.raises(memory.CollectorError):
        memory.parse_config(b" " * (memory.MAX_JSON_BYTES + 1))
    with pytest.raises(memory.CollectorError):
        memory.parse_config(json.dumps(config(*(component(f"a{i}", f"s{i}") for i in range(65)))))


def test_maximum_configured_components_fit_the_bounded_output(environment):
    value = config(*(component(f"alias{i}", f"service{i}") for i in range(64)))
    result = sampler(environment, Docker([])).collect(value)
    assert result["complete"] is False
    assert len(result["dedicated_components"]) == 64
    assert len(memory.encode_sample(result)) <= memory.MAX_JSON_BYTES


@pytest.mark.skipif(os.name != "posix", reason="Linux symlink attribution")
def test_symlink_cgroup_cannot_escape_the_expected_root(environment, tmp_path):
    c = container()
    pid = environment.proc / str(c["pid"])
    pid.mkdir(parents=True)
    relative = "/docker/" + c["id"]
    (pid / "cgroup").write_text("0::" + relative + "\n")
    (environment.groups / "docker").mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (environment.groups / "docker" / c["id"]).symlink_to(outside, target_is_directory=True)
    result = sampler(environment, Docker([c])).collect(config())
    assert result["complete"] is False


def test_permission_check_requires_owned_nonwritable_regular_files():
    for mode, owner in [(stat.S_IFLNK | 0o600, 0), (stat.S_IFREG | 0o622, 0), (stat.S_IFREG | 0o600, 1000)]:
        with pytest.raises(memory.CollectorError):
            memory._owned(SimpleNamespace(st_mode=mode, st_uid=owner))


@pytest.mark.skipif(os.name != "posix", reason="Linux secure dirfd file operations")
def test_secure_load_and_atomic_replace_preserve_a_readable_bounded_snapshot(tmp_path):
    directory = tmp_path / "protected"
    directory.mkdir(mode=0o700)
    cfg = directory / "config.json"
    cfg.write_text(json.dumps(config()))
    cfg.chmod(0o600)
    owner = os.geteuid()
    assert memory.load_config(cfg, owner_uid=owner) == config()
    output = directory / "memory.json"
    old = {"sampled_at": "old"}
    memory.write_sample(output, old, owner_uid=owner)
    inode = output.stat().st_ino
    new = {"sampled_at": "new"}
    memory.write_sample(output, new, owner_uid=owner)
    assert json.loads(output.read_text()) == new
    assert output.stat().st_ino != inode
    assert stat.S_IMODE(output.stat().st_mode) == 0o644
    assert not list(directory.glob("*.tmp"))
    cfg.chmod(0o622)
    with pytest.raises(memory.CollectorError):
        memory.load_config(cfg, owner_uid=owner)


@pytest.mark.skipif(os.name != "posix", reason="Linux secure symlink rejection")
def test_output_symlink_does_not_overwrite_another_file(tmp_path):
    directory = tmp_path / "protected"
    directory.mkdir(mode=0o700)
    target = directory / "target"
    target.write_text("keep")
    output = directory / "memory.json"
    output.symlink_to(target)
    with pytest.raises(memory.CollectorError):
        memory.write_sample(output, {}, owner_uid=os.geteuid())
    assert target.read_text() == "keep"


@pytest.mark.skipif(os.name != "posix", reason="Linux nonblocking FIFO config rejection")
def test_fifo_config_is_rejected_without_waiting_for_a_writer(tmp_path):
    directory = tmp_path / "protected"
    directory.mkdir(mode=0o700)
    cfg = directory / "config.json"
    os.mkfifo(cfg, mode=0o600)
    with pytest.raises(memory.CollectorError):
        memory.load_config(cfg, owner_uid=os.geteuid())


@pytest.mark.parametrize("complete,expected", [(True, 0), (False, 1)])
def test_cli_publishes_incomplete_snapshot_but_reports_failure(monkeypatch, capsys, complete, expected):
    sample = {"complete": complete}
    writes = []
    monkeypatch.setattr(memory, "os", SimpleNamespace(name="posix", geteuid=lambda: 0))
    monkeypatch.setattr(memory, "load_config", lambda _: config())
    monkeypatch.setattr(memory, "MemoryCollector", lambda: SimpleNamespace(collect=lambda _: sample))
    monkeypatch.setattr(memory, "write_sample", lambda path, value: writes.append((path, value)))
    assert memory.main(["--config", "config.json", "--output", "memory.json"]) == expected
    assert writes == [("memory.json", sample)]
    assert capsys.readouterr().err == ("RCON memory sample incomplete\n" if not complete else "")


@pytest.mark.skipif(os.name != "posix", reason="Linux bounded subprocess pipe")
def test_docker_runner_bounds_output_and_discards_stderr():
    result = memory._docker_run([sys.executable, "-c",
        "import sys; sys.stdout.write('metadata'); sys.stderr.write('private detail')"], 2)
    assert result.stdout == b"metadata"
    assert result.stderr is None
    with pytest.raises(memory.CollectorError, match="docker_metadata_too_large"):
        memory._docker_run([sys.executable, "-c",
            f"import sys; sys.stdout.buffer.write(b'x' * {memory.MAX_DOCKER_BYTES + 1})"], 2)


@pytest.mark.skipif(os.name != "posix", reason="Linux bounded subprocess pipe")
def test_docker_runner_times_out_and_reaps_an_unresponsive_process():
    with pytest.raises(subprocess.TimeoutExpired):
        memory._docker_run([sys.executable, "-c", "while True: pass"], 0.05)
