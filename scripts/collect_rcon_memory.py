#!/usr/bin/env python3
"""One-shot, host-only memory sampler for explicitly selected RCON services.

Run as root from a systemd timer. Only the resulting JSON file is mounted into
the backend; this program never exposes a Docker socket to an application.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path, PurePosixPath
import re
import selectors
import stat
import subprocess
import sys
import time
from uuid import uuid4

MAX_JSON_BYTES = 32768
MAX_COMPONENTS = 64
MAX_CONTAINERS = 1024
MAX_DOCKER_BYTES = 1024 * 1024
MAX_COUNTER = 2**63 - 1
INSPECT_FORMAT = ('{"id":{{json .Id}},"running":{{json .State.Running}},'
                  '"pid":{{json .State.Pid}},'
                  '"project":{{json (index .Config.Labels "com.docker.compose.project")}},'
                  '"compose_service":{{json (index .Config.Labels "com.docker.compose.service")}}}')
_ALIAS = re.compile(r"[A-Za-z][A-Za-z0-9_.-]{0,63}\Z")
_PROJECT = re.compile(r"[a-z0-9][a-z0-9_-]{0,127}\Z")
_SERVICE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}\Z")
_ID = re.compile(r"[0-9a-f]{64}\Z")


class CollectorError(Exception):
    """Deliberately contains no command output, environment or config values."""


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise CollectorError("duplicate_json_field")
        result[key] = value
    return result


def parse_config(raw):
    if not isinstance(raw, (str, bytes, bytearray)):
        raise CollectorError("invalid_config")
    if len(raw.encode("utf-8") if isinstance(raw, str) else raw) > MAX_JSON_BYTES:
        raise CollectorError("config_too_large")
    try:
        config = json.loads(raw, object_pairs_hook=_unique_object)
    except (ValueError, UnicodeError, TypeError):
        raise CollectorError("invalid_config") from None
    if not isinstance(config, dict) or set(config) != {"server_number", "components"}:
        raise CollectorError("invalid_config")
    number = config["server_number"]
    components = config["components"]
    if isinstance(number, bool) or not isinstance(number, int) or not 1 <= number <= 2**31 - 1:
        raise CollectorError("invalid_server_number")
    if not isinstance(components, list) or not 1 <= len(components) <= MAX_COMPONENTS:
        raise CollectorError("invalid_components")
    aliases, selectors = set(), set()
    for item in components:
        if not isinstance(item, dict) or set(item) != {"service", "project", "compose_service", "category"}:
            raise CollectorError("invalid_component")
        for field, pattern in (("service", _ALIAS), ("project", _PROJECT), ("compose_service", _SERVICE)):
            if not isinstance(item[field], str) or not pattern.fullmatch(item[field]):
                raise CollectorError("invalid_selector")
        if item["category"] not in ("dedicated", "shared"):
            raise CollectorError("invalid_category")
        alias = item["service"].casefold()
        selector = item["project"], item["compose_service"]
        if alias in aliases or selector in selectors:
            raise CollectorError("duplicate_component")
        aliases.add(alias)
        selectors.add(selector)
    return config


def _bounded_read(path, maximum):
    with Path(path).open("r", encoding="ascii") as stream:
        value = stream.read(maximum + 1)
    if len(value) > maximum:
        raise CollectorError("metadata_too_large")
    return value


def _docker_run(command, timeout):
    # The template retrieves only IDs, PID/running state and the two selector
    # labels. In particular no complete inspect, Config.Env or secrets escape.
    # Read the pipe with a hard cap; rejecting a captured value afterwards
    # would still allow an unexpectedly large response to fill host memory.
    deadline = time.monotonic() + timeout
    with subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL) as process:
        try:
            output = bytearray()
            with selectors.DefaultSelector() as selector:
                selector.register(process.stdout, selectors.EVENT_READ)
                while True:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0 or not selector.select(remaining):
                        raise subprocess.TimeoutExpired(command, timeout)
                    block = os.read(process.stdout.fileno(), min(65536, MAX_DOCKER_BYTES + 1 - len(output)))
                    if not block:
                        break
                    output.extend(block)
                    if len(output) > MAX_DOCKER_BYTES:
                        raise CollectorError("docker_metadata_too_large")
            code = process.wait(timeout=max(0.001, deadline - time.monotonic()))
            return subprocess.CompletedProcess(command, code, stdout=bytes(output))
        finally:
            if process.poll() is None:
                process.kill()
                process.wait()


class MemoryCollector:
    def __init__(self, *, runner=_docker_run, read_text=_bounded_read,
                 proc_root=Path("/proc"), cgroup_root=Path("/sys/fs/cgroup"),
                 monotonic=time.monotonic, utc_now=lambda: datetime.now(timezone.utc),
                 budget_seconds=10):
        self.runner, self.read_text = runner, read_text
        self.proc_root, self.cgroup_root = Path(proc_root), Path(cgroup_root)
        self.monotonic, self.utc_now, self.budget_seconds = monotonic, utc_now, budget_seconds

    def _command(self, arguments, deadline):
        remaining = deadline - self.monotonic()
        if remaining <= 0:
            raise CollectorError("sample_deadline")
        result = self.runner(["docker", *arguments], min(4.0, remaining))
        raw = result.stdout
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        if not isinstance(raw, str) or len(raw.encode("utf-8")) > MAX_DOCKER_BYTES:
            raise CollectorError("docker_metadata_too_large")
        return result.returncode, raw

    def _containers(self, deadline):
        code, raw = self._command(["ps", "-aq", "--no-trunc"], deadline)
        ids = sorted(set(raw.splitlines()))
        if code or len(ids) > MAX_CONTAINERS or any(not _ID.fullmatch(value) for value in ids):
            raise CollectorError("docker_discovery_failed")
        if not ids:
            return []
        _code, raw = self._command(["inspect", "--format", INSPECT_FORMAT, *ids], deadline)
        # A disappearing unrelated container may make inspect exit nonzero.
        # Keep valid records and let missing required selectors fail closed.
        result = {}
        for line in raw.splitlines():
            data = json.loads(line, object_pairs_hook=_unique_object)
            if not isinstance(data, dict) or set(data) != {"id", "pid", "running", "project", "compose_service"}:
                raise CollectorError("invalid_docker_metadata")
            if data["id"] not in ids or not isinstance(data["running"], bool):
                raise CollectorError("invalid_docker_metadata")
            if data["id"] in result and result[data["id"]] != data:
                raise CollectorError("inconsistent_container_identity")
            result[data["id"]] = data
        return list(result.values())

    @staticmethod
    def _has_identity(path, container_id):
        names = {container_id, "docker-" + container_id,
                 "docker-" + container_id + ".scope", "cri-containerd-" + container_id + ".scope"}
        return any(part in names for part in PurePosixPath(path).parts)

    def _cgroup_directory(self, membership, container_id):
        entries = []
        for line in membership.splitlines():
            fields = line.split(":", 2)
            if len(fields) != 3:
                raise CollectorError("invalid_cgroup_membership")
            hierarchy, controllers, raw_path = fields
            path = PurePosixPath(raw_path)
            if not path.is_absolute() or ".." in path.parts or not self._has_identity(raw_path, container_id):
                continue
            if hierarchy == "0" and controllers == "":
                entries.insert(0, (2, self.cgroup_root.joinpath(*path.parts[1:])))
            elif "memory" in controllers.split(","):
                entries.append((1, (self.cgroup_root / "memory").joinpath(*path.parts[1:])))
        root = self.cgroup_root.resolve(strict=True)
        for version, candidate in entries:
            try:
                resolved = candidate.resolve(strict=True)
            except FileNotFoundError:
                # Hybrid hosts can report a unified hierarchy whose memory
                # controller is still served by the v1 memory mount.
                continue
            if not resolved.is_relative_to(root) or not self._has_identity(resolved.relative_to(root).as_posix(), container_id):
                raise CollectorError("unsafe_cgroup_path")
            current = resolved / ("memory.current" if version == 2 else "memory.usage_in_bytes")
            if current.exists():
                return version, resolved
        raise CollectorError("container_cgroup_unavailable")

    def _file(self, directory, filename, maximum=65536):
        path = (directory / filename).resolve(strict=True)
        if path.parent != directory:
            raise CollectorError("unsafe_cgroup_file")
        return self.read_text(path, maximum)

    @staticmethod
    def _number(value):
        value = value.strip()
        if not re.fullmatch(r"[0-9]{1,20}", value):
            raise CollectorError("invalid_memory_counter")
        number = int(value)
        if number > MAX_COUNTER:
            raise CollectorError("invalid_memory_counter")
        return number

    def _memory(self, container, deadline):
        if not container["running"]:
            return 0, None, 0
        pid = container["pid"]
        if isinstance(pid, bool) or not isinstance(pid, int) or not 1 <= pid <= 2**31 - 1:
            raise CollectorError("invalid_container_pid")
        if self.monotonic() > deadline:
            raise CollectorError("sample_deadline")
        membership_path = self.proc_root / str(pid) / "cgroup"
        membership = self.read_text(membership_path, 16384)
        version, directory = self._cgroup_directory(membership, container["id"])
        used = self._number(self._file(directory, "memory.current" if version == 2 else "memory.usage_in_bytes", 128))
        raw_limit = self._file(directory, "memory.max" if version == 2 else "memory.limit_in_bytes", 128).strip()
        limit = None if version == 2 and raw_limit == "max" else self._number(raw_limit)
        if version == 1 and limit is not None and limit >= 2**60:
            limit = None
        values = {}
        for line in self._file(directory, "memory.stat").splitlines():
            fields = line.split()
            if len(fields) == 2 and fields[0] in ("inactive_file", "total_inactive_file"):
                if fields[0] in values:
                    raise CollectorError("duplicate_memory_stat")
                values[fields[0]] = self._number(fields[1])
        key = "total_inactive_file" if version == 1 and "total_inactive_file" in values else "inactive_file"
        if key not in values:
            raise CollectorError("inactive_file_unavailable")
        # Recheck after reading counters: a PID reused by a different container
        # or a moved cgroup cannot inherit the first container's attribution.
        if self.read_text(membership_path, 16384) != membership:
            raise CollectorError("container_identity_changed")
        return used, limit, min(values[key], used)

    def collect(self, config):
        config = parse_config(json.dumps(config))
        deadline = self.monotonic() + self.budget_seconds
        result = {"schema_version": 1, "server_number": config["server_number"], "complete": True,
                  "dedicated_components": [], "shared_components": []}
        try:
            containers = self._containers(deadline)
        except (CollectorError, OSError, ValueError, UnicodeError, subprocess.SubprocessError):
            containers = []
        seen = set()
        for component in config["components"]:
            record = {"service": component["service"], "used_bytes": None,
                      "limit_bytes": None, "reclaimable_bytes": None}
            selected = [c for c in containers if c["project"] == component["project"]
                        and c["compose_service"] == component["compose_service"]]
            try:
                if not selected:
                    raise CollectorError("required_selector_missing")
                readings, running_limits = [], []
                for container in selected:
                    if container["id"] in seen:
                        raise CollectorError("duplicate_container")
                    seen.add(container["id"])
                    reading = self._memory(container, deadline)
                    readings.append(reading)
                    if container["running"]:
                        running_limits.append(reading[1])
                used = sum(value[0] for value in readings)
                reclaimable = sum(value[2] for value in readings)
                limit = sum(running_limits) if running_limits and None not in running_limits else None
                if any(value is not None and value > MAX_COUNTER for value in (used, reclaimable, limit)):
                    raise CollectorError("aggregate_memory_counter_too_large")
                record.update(used_bytes=used, reclaimable_bytes=reclaimable, limit_bytes=limit)
            except (CollectorError, OSError, ValueError, UnicodeError):
                result["complete"] = False
            result[component["category"] + "_components"].append(record)
        now = self.utc_now()
        if not isinstance(now, datetime) or now.tzinfo is None:
            raise CollectorError("invalid_sample_clock")
        result["sampled_at"] = now.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
        encode_sample(result)
        return result


def encode_sample(sample):
    raw = (json.dumps(sample, separators=(",", ":"), ensure_ascii=True) + "\n").encode("utf-8")
    if len(raw) > MAX_JSON_BYTES:
        raise CollectorError("sample_too_large")
    return raw


def _owned(metadata, *, owner_uid=0, directory=False):
    valid_type = stat.S_ISDIR(metadata.st_mode) if directory else stat.S_ISREG(metadata.st_mode)
    if not valid_type or metadata.st_uid != owner_uid or metadata.st_mode & 0o022:
        raise CollectorError("unsafe_file_permissions")


def _secure_directory(path, owner_uid=0):
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        _owned(os.fstat(descriptor), owner_uid=owner_uid, directory=True)
    except BaseException:
        os.close(descriptor)
        raise
    return descriptor


def load_config(path, *, owner_uid=0):
    path = Path(path)
    parent = _secure_directory(path.parent, owner_uid)
    try:
        descriptor = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        try:
            _owned(os.fstat(descriptor), owner_uid=owner_uid)
            raw = os.read(descriptor, MAX_JSON_BYTES + 1)
        finally:
            os.close(descriptor)
    finally:
        os.close(parent)
    return parse_config(raw)


def write_sample(path, sample, *, owner_uid=0):
    path = Path(path)
    raw = encode_sample(sample)
    parent = _secure_directory(path.parent, owner_uid)
    temporary = ".rcon-memory-" + uuid4().hex + ".tmp"
    created = False
    try:
        try:
            existing = os.stat(path.name, dir_fd=parent, follow_symlinks=False)
        except FileNotFoundError:
            pass
        else:
            _owned(existing, owner_uid=owner_uid)
        descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o644, dir_fd=parent)
        created = True
        try:
            # The file contains resource totals only; a non-root backend must
            # be able to read its read-only bind mount even under umask 0077.
            with os.fdopen(descriptor, "wb") as stream:
                os.fchmod(stream.fileno(), 0o644)
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, path.name, src_dir_fd=parent, dst_dir_fd=parent)
            created = False
            os.fsync(parent)
        finally:
            if created:
                os.unlink(temporary, dir_fd=parent)
    finally:
        os.close(parent)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    try:
        if os.name != "posix" or os.geteuid() != 0:
            raise CollectorError("host_root_required")
        config = load_config(args.config)
        sample = MemoryCollector().collect(config)
        write_sample(args.output, sample)
        if not sample["complete"]:
            print("RCON memory sample incomplete", file=sys.stderr)
            return 1
        return 0
    except (CollectorError, OSError, ValueError, UnicodeError):
        # No Docker stderr, inspect bodies, selectors or environment in logs.
        print("RCON memory sample could not be written safely", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
