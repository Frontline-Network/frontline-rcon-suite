"""Exercise the actual rotation script in an isolated directory on Linux."""

import gzip
import os
import shutil
import subprocess
from pathlib import Path

import pytest

fcntl = pytest.importorskip("fcntl")
pytestmark = pytest.mark.skipif(
    not Path("/usr/sbin/logrotate").exists() or not shutil.which("flock"),
    reason="Requires the Linux runtime image's logrotate and flock",
)
SCRIPT = Path(__file__).resolve().parents[1] / "config" / "do_logrotate.sh"


@pytest.fixture
def rotation(tmp_path):
    log = tmp_path / "worker.log"
    original = b"synthetic log entry\n" * 200
    log.write_bytes(original)
    config = tmp_path / "logrotate.conf"
    config.write_text(
        f'"{log}" {{\n size 1k\n rotate 2\n copytruncate\n compress\n}}\n'
    )
    config.chmod(0o600)

    def run(server=3):
        return subprocess.run(
            ["bash", str(SCRIPT)],
            env={
                **os.environ,
                "SERVER_NUMBER": str(server),
                "LOGROTATE_LOG_DIR": str(tmp_path),
                "LOGROTATE_CONFIG": str(config),
            },
            capture_output=True,
            text=True,
            timeout=10,
        )

    return tmp_path, log, config, original, run


def test_active_server_rotates_with_shared_persistent_state(rotation):
    root, log, config, original, run = rotation
    before = config.stat()
    result = run(3)
    assert result.returncode == 0, result.stderr
    assert log.read_bytes() == b""
    assert gzip.decompress((root / "worker.log.1.gz").read_bytes()) == original
    assert str(log) in (root / ".logrotate.status").read_text()
    log.write_text("small new entry\n")
    assert run(4).returncode == 0
    assert not (root / "worker.log.2.gz").exists()
    assert log.read_text() == "small new entry\n"
    after = config.stat()
    assert (after.st_mode, after.st_uid, after.st_gid) == (
        before.st_mode,
        before.st_uid,
        before.st_gid,
    )


def test_shared_lock_prevents_concurrent_rotation(rotation):
    root, log, _, original, run = rotation
    with (root / ".logrotate.lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        result = run(4)
        assert result.returncode == 0, result.stderr
        assert log.read_bytes() == original
        assert not (root / ".logrotate.status").exists()
    assert run(4).returncode == 0
    assert log.stat().st_size == 0


def test_configuration_failure_is_not_hidden(rotation):
    _, _, config, _, run = rotation
    config.unlink()
    assert run().returncode != 0
