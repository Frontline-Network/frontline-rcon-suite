"""Wire-level regressions for isolated structured report analysis."""

from pathlib import Path
from types import SimpleNamespace

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
