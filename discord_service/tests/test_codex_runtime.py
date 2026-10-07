"""Wire-level regressions for isolated structured report analysis."""

from pathlib import Path
from types import SimpleNamespace
import threading
from unittest.mock import Mock

import pytest

from discord_service.app import codex_runtime as runtime


def test_structured_turn_uses_thread_start_sandbox_enum(monkeypatch):
    calls = []

    class Client:
        home = Path("/isolated-test")
        settings = SimpleNamespace(codex_request_timeout_seconds=10)

        def __init__(self, installation_id):
            self.detached = False

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def detach_credentials(self):
            self.detached = True

        def request(self, method, params=None, **kwargs):
            calls.append((method, params))
            if method == "account/read":
                return {"account": {"type": "chatgpt"}}
            if method == "model/list":
                return {"data": [{"id": "configured-model"}]}
            if method == "thread/start":
                # SandboxMode (thread/start) differs from the tagged
                # SandboxPolicy object used by other RPCs.
                assert params["sandbox"] == "read-only"
                assert params["approvalPolicy"] == "never"
                assert params["ephemeral"] is True
                assert self.detached
                return {"thread": {"id": "synthetic-thread"}}
            return {}

        def wait_notification(self, method, **kwargs):
            return {
                "params": {
                    "turn": {
                        "status": "completed",
                        "items": [{"type": "agentMessage", "text": '{"ok":true}'}],
                    }
                }
            }

    monkeypatch.setattr(runtime, "CodexAppServer", Client)
    schema = {"type": "object", "properties": {"ok": {"type": "boolean"}}}
    assert runtime.run_structured(
        "test-installation",
        model="configured-model",
        prompt="test",
        output_schema=schema,
    ) == {"ok": True}
    assert dict(calls)["turn/start"]["outputSchema"] == schema


def test_waiting_report_has_priority_without_overlapping_runtimes():
    lock = runtime._PriorityLock()
    assert lock.acquire(timeout=0)
    order = []

    def acquire(label, priority):
        assert lock.acquire(timeout=2, priority=priority)
        order.append(label)
        lock.release()

    report = threading.Thread(target=acquire, args=("report", True))
    batch = threading.Thread(target=acquire, args=("batch", False))
    report.start()
    with lock.condition:
        assert lock.condition.wait_for(lambda: lock.priority_waiters == 1, timeout=1)
    batch.start()
    lock.release()
    report.join(timeout=3)
    batch.join(timeout=3)
    assert not report.is_alive() and not batch.is_alive()
    assert order == ["report", "batch"]


def test_timed_out_priority_wait_does_not_block_later_work():
    lock = runtime._PriorityLock()
    assert lock.acquire(timeout=0)
    assert not lock.acquire(timeout=0.01, priority=True)
    assert lock.priority_waiters == 0
    lock.release()
    assert lock.acquire(timeout=0)
    lock.release()


def test_typed_busy_error_is_before_credentials_or_runtime_start(monkeypatch):
    lock = Mock()
    lock.acquire.return_value = False
    prepare = Mock()
    spawn = Mock()
    monkeypatch.setattr(runtime, "_home_lock", lambda _: lock)
    monkeypatch.setattr(runtime, "_runtime_home", prepare)
    monkeypatch.setattr(runtime.subprocess, "Popen", spawn)
    with pytest.raises(runtime.CodexRuntimeBusy):
        runtime.CodexAppServer(
            "test", SimpleNamespace(codex_enabled=True), priority=True
        )
    lock.acquire.assert_called_once_with(timeout=15, priority=True)
    prepare.assert_not_called()
    spawn.assert_not_called()
