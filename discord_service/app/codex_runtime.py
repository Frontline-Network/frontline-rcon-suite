"""Isolated Codex app-server bridge for customer ChatGPT subscriptions.

Each CRCON installation gets its own CODEX_HOME.  The app-server owns token
refresh and model discovery; this service never copies OAuth tokens into its
database or API responses.
"""

from __future__ import annotations

import json
import os
import queue
import re
import shutil
import subprocess
import tempfile
import threading
from pathlib import Path
from time import monotonic
from typing import Any

from cryptography.fernet import InvalidToken

from .config import Settings, get_settings
from .security import decrypt, encrypt


class CodexRuntimeError(RuntimeError):
    pass


class CodexRuntimeBusy(CodexRuntimeError):
    """No runtime/account/model call was started: admission may be retried."""


class _PriorityLock:
    """One account runtime at a time; waiting live reports go before batches."""

    def __init__(self):
        self.condition = threading.Condition()
        self.held = False
        self.priority_waiters = 0

    def acquire(self, timeout: float, *, priority: bool = False) -> bool:
        deadline = monotonic() + timeout
        with self.condition:
            if priority:
                self.priority_waiters += 1
                self.condition.notify_all()
            try:
                while self.held or (not priority and self.priority_waiters):
                    remaining = deadline - monotonic()
                    if remaining <= 0:
                        return False
                    self.condition.wait(remaining)
                self.held = True
                return True
            finally:
                if priority:
                    self.priority_waiters -= 1
                    self.condition.notify_all()

    def release(self):
        with self.condition:
            if not self.held:
                raise RuntimeError("release of unlocked runtime admission")
            self.held = False
            self.condition.notify_all()


_INSTALLATION_RE = re.compile(r"^[A-Za-z0-9-]{1,64}$")


def _installation_store(installation_id: str, settings: Settings) -> Path:
    if not _INSTALLATION_RE.fullmatch(installation_id):
        raise CodexRuntimeError("invalid_installation_id")
    root = Path(settings.codex_auth_root).resolve()
    store = (root / installation_id).resolve()
    if store.parent != root:
        raise CodexRuntimeError("invalid_installation_id")
    store.mkdir(parents=True, exist_ok=True, mode=0o700)
    try:
        store.chmod(0o700)
    except OSError:
        pass
    return store


def _runtime_home(store: Path) -> Path:
    home = Path(tempfile.mkdtemp(prefix="frontline-codex-"))
    home.chmod(0o700)
    config = home / "config.toml"
    config.write_text(
        'cli_auth_credentials_store = "file"\n'
        "check_for_update_on_startup = false\n"
        'approval_policy = "never"\n'
        'sandbox_mode = "read-only"\n'
        'web_search = "disabled"\n\n'
        "[features]\n"
        "apply_patch_freeform = false\n"
        "apps = false\n"
        "browser_use = false\n"
        "code_mode = false\n"
        "connectors = false\n"
        "image_generation = false\n"
        "multi_agent = false\n"
        "plugins = false\n"
        "shell_snapshot = false\n"
        "shell_tool = false\n"
        "tool_search = false\n",
        encoding="utf-8",
    )
    try:
        config.chmod(0o600)
    except OSError:
        pass
    encrypted_auth = store / "auth.json.enc"
    if encrypted_auth.exists():
        try:
            (home / "auth.json").write_text(
                decrypt(encrypted_auth.read_text(encoding="ascii")), encoding="utf-8"
            )
            (home / "auth.json").chmod(0o600)
        except (OSError, ValueError, InvalidToken) as exc:
            shutil.rmtree(home, ignore_errors=True)
            raise CodexRuntimeError("codex_credentials_unreadable") from exc
    runtime = home / "runtime"
    runtime.mkdir(exist_ok=True, mode=0o700)
    return home


_home_locks_guard = threading.Lock()
_home_locks: dict[str, _PriorityLock] = {}


def _home_lock(installation_id: str) -> _PriorityLock:
    with _home_locks_guard:
        return _home_locks.setdefault(installation_id, _PriorityLock())


def _persist_credentials(store: Path, home: Path, snapshot: str | None = None) -> None:
    auth = home / "auth.json"
    plaintext = auth.read_text(encoding="utf-8") if auth.exists() else snapshot
    if not plaintext:
        return
    encrypted = encrypt(plaintext)
    destination = store / "auth.json.enc"
    temporary = store / "auth.json.enc.tmp"
    temporary.write_text(encrypted, encoding="ascii")
    try:
        temporary.chmod(0o600)
    except OSError:
        pass
    temporary.replace(destination)
    try:
        destination.chmod(0o600)
    except OSError:
        pass


class CodexAppServer:
    def __init__(
        self, installation_id: str, settings: Settings | None = None, *, priority=False
    ):
        self.settings = settings or get_settings()
        if not self.settings.codex_enabled:
            raise CodexRuntimeError("codex_runtime_disabled")
        self.installation_id = installation_id
        self._lock = _home_lock(installation_id)
        if not self._lock.acquire(timeout=15 if priority else 5, priority=priority):
            raise CodexRuntimeBusy("codex_runtime_busy")
        self._closed = False
        self._auth_snapshot: str | None = None
        self.home: Path | None = None
        try:
            self.store = _installation_store(installation_id, self.settings)
            self.home = _runtime_home(self.store)
            env = os.environ.copy()
            env["CODEX_HOME"] = str(self.home)
            env["NO_COLOR"] = "1"
            self.process = subprocess.Popen(
                [self.settings.codex_binary, "app-server"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                bufsize=1,
                env=env,
                cwd=str(self.home / "runtime"),
            )
        except (FileNotFoundError, OSError) as exc:
            if self.home is not None:
                shutil.rmtree(self.home, ignore_errors=True)
            self._lock.release()
            raise CodexRuntimeError("codex_runtime_unavailable") from exc
        except Exception:
            if self.home is not None:
                shutil.rmtree(self.home, ignore_errors=True)
            self._lock.release()
            raise
        self._messages: queue.Queue[dict[str, Any] | None] = queue.Queue()
        self._notifications: list[dict[str, Any]] = []
        self._request_id = 0
        threading.Thread(target=self._read_stdout, daemon=True).start()
        threading.Thread(target=self._drain_stderr, daemon=True).start()
        try:
            self.request(
                "initialize",
                {
                    "clientInfo": {
                        "name": "frontline_crcon",
                        "title": "Frontline CRCON",
                        "version": "0.1.0",
                    },
                    "capabilities": {
                        "optOutNotificationMethods": [
                            "item/agentMessage/delta",
                            "item/reasoning/summaryTextDelta",
                            "item/reasoning/textDelta",
                        ]
                    },
                },
                timeout=15,
            )
            self.notify("initialized")
        except Exception:
            self.close()
            raise

    def _read_stdout(self) -> None:
        assert self.process.stdout is not None
        try:
            for line in self.process.stdout:
                try:
                    message = json.loads(line)
                except (TypeError, ValueError):
                    continue
                if isinstance(message, dict):
                    self._messages.put(message)
        finally:
            self._messages.put(None)

    def _drain_stderr(self) -> None:
        assert self.process.stderr is not None
        for _ in self.process.stderr:
            # Runtime diagnostics may contain customer metadata. Do not log it.
            pass

    def _send(self, payload: dict[str, Any]) -> None:
        if self.process.poll() is not None or self.process.stdin is None:
            raise CodexRuntimeError("codex_runtime_stopped")
        self.process.stdin.write(json.dumps(payload, separators=(",", ":")) + "\n")
        self.process.stdin.flush()

    def notify(self, method: str, params: dict[str, Any] | None = None) -> None:
        payload: dict[str, Any] = {"method": method}
        if params is not None:
            payload["params"] = params
        self._send(payload)

    def request(
        self,
        method: str,
        params: dict[str, Any] | None = None,
        *,
        timeout: int | None = None,
    ) -> dict[str, Any]:
        self._request_id += 1
        request_id = self._request_id
        payload: dict[str, Any] = {"id": request_id, "method": method}
        if params is not None:
            payload["params"] = params
        self._send(payload)
        deadline = monotonic() + (
            timeout or self.settings.codex_request_timeout_seconds
        )
        while True:
            remaining = deadline - monotonic()
            if remaining <= 0:
                raise CodexRuntimeError(f"codex_timeout:{method}")
            try:
                message = self._messages.get(timeout=remaining)
            except queue.Empty as exc:
                raise CodexRuntimeError(f"codex_timeout:{method}") from exc
            if message is None:
                raise CodexRuntimeError("codex_runtime_stopped")
            if message.get("id") == request_id:
                if message.get("error"):
                    error = message["error"]
                    code = error.get("code") if isinstance(error, dict) else "unknown"
                    raise CodexRuntimeError(f"codex_request_failed:{method}:{code}")
                result = message.get("result")
                return result if isinstance(result, dict) else {}
            if "method" in message:
                self._notifications.append(message)

    def wait_notification(
        self, method: str, *, timeout: int | None = None
    ) -> dict[str, Any]:
        deadline = monotonic() + (
            timeout or self.settings.codex_request_timeout_seconds
        )
        while True:
            for index, message in enumerate(self._notifications):
                if message.get("method") == method:
                    return self._notifications.pop(index)
            remaining = deadline - monotonic()
            if remaining <= 0:
                raise CodexRuntimeError(f"codex_timeout:{method}")
            try:
                message = self._messages.get(timeout=remaining)
            except queue.Empty as exc:
                raise CodexRuntimeError(f"codex_timeout:{method}") from exc
            if message is None:
                raise CodexRuntimeError("codex_runtime_stopped")
            if message.get("method") == method:
                return message
            if "method" in message:
                self._notifications.append(message)

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.process.kill()
        try:
            if self.home is not None:
                _persist_credentials(self.store, self.home, self._auth_snapshot)
        finally:
            if self.home is not None:
                shutil.rmtree(self.home, ignore_errors=True)
            self._lock.release()

    def detach_credentials(self) -> None:
        """Remove plaintext credentials before any untrusted model turn starts."""

        if self.home is None:
            return
        auth = self.home / "auth.json"
        if not auth.exists():
            return
        self._auth_snapshot = auth.read_text(encoding="utf-8")
        auth.unlink()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()


_login_lock = threading.Lock()
_pending_logins: dict[str, tuple[CodexAppServer, str]] = {}
_login_results: dict[str, dict[str, Any]] = {}


def start_device_login(installation_id: str) -> dict[str, Any]:
    with _login_lock:
        previous = _pending_logins.pop(installation_id, None)
        if previous:
            previous[0].close()
        client = CodexAppServer(installation_id)
        try:
            result = client.request(
                "account/login/start", {"type": "chatgptDeviceCode"}, timeout=30
            )
        except Exception:
            client.close()
            raise
        login_id = str(result.get("loginId") or "")
        verification_url = str(result.get("verificationUrl") or "")
        user_code = str(result.get("userCode") or "")
        if not login_id or not verification_url or not user_code:
            client.close()
            raise CodexRuntimeError("codex_login_response_invalid")
        _pending_logins[installation_id] = (client, login_id)
        _login_results[installation_id] = {
            "state": "pending",
            "login_id": login_id,
            "verification_url": verification_url,
            "user_code": user_code,
        }

    def wait_for_login() -> None:
        try:
            notification = client.wait_notification(
                "account/login/completed", timeout=600
            )
            params = notification.get("params") or {}
            result = {
                "state": "connected" if params.get("success") else "failed",
                "login_id": login_id,
                "error": None if params.get("success") else "codex_login_failed",
            }
        except CodexRuntimeError as exc:
            result = {"state": "failed", "login_id": login_id, "error": str(exc)}
        finally:
            client.close()
            with _login_lock:
                current = _pending_logins.get(installation_id)
                if current and current[1] == login_id:
                    _pending_logins.pop(installation_id, None)
                    _login_results[installation_id] = result

    threading.Thread(target=wait_for_login, daemon=True).start()
    return {
        "state": "pending",
        "login_id": login_id,
        "verification_url": verification_url,
        "user_code": user_code,
    }


def _model_options(client: CodexAppServer) -> list[dict[str, Any]]:
    result = client.request("model/list", {"includeHidden": False}, timeout=30)
    rows = result.get("data") or result.get("models") or []
    options = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        model_id = str(row.get("id") or row.get("model") or "")
        if not model_id:
            continue
        options.append(
            {
                "id": model_id,
                "name": str(row.get("displayName") or row.get("name") or model_id)[
                    :160
                ],
                "description": str(row.get("description") or "")[:500],
                "default": bool(row.get("isDefault") or row.get("default")),
            }
        )
    return options


def account_status(installation_id: str) -> dict[str, Any]:
    settings = get_settings()
    if not settings.codex_enabled:
        return {
            "available": False,
            "connected": False,
            "state": "disabled",
            "models": [],
        }
    with _login_lock:
        pending = _login_results.get(installation_id, {})
        if pending.get("state") == "pending":
            return {"available": True, "connected": False, "models": [], **pending}
    try:
        with CodexAppServer(installation_id, settings) as client:
            account_result = client.request(
                "account/read", {"refreshToken": False}, timeout=30
            )
            account = account_result.get("account")
            if not isinstance(account, dict) or account.get("type") != "chatgpt":
                with _login_lock:
                    pending = _login_results.get(installation_id, {})
                return {
                    "available": True,
                    "connected": False,
                    "state": pending.get("state", "disconnected"),
                    "error": pending.get("error"),
                    "models": [],
                }
            models = _model_options(client)
            return {
                "available": True,
                "connected": True,
                "state": "connected",
                "email": account.get("email"),
                "plan_type": account.get("planType"),
                "models": models,
            }
    except CodexRuntimeError as exc:
        return {
            "available": False,
            "connected": False,
            "state": "unavailable",
            "error": str(exc),
            "models": [],
        }


def logout(installation_id: str) -> None:
    with _login_lock:
        pending = _pending_logins.pop(installation_id, None)
        _login_results.pop(installation_id, None)
    if pending:
        pending[0].close()
    with CodexAppServer(installation_id) as client:
        client.request("account/logout", timeout=30)
    encrypted_auth = (
        _installation_store(installation_id, get_settings()) / "auth.json.enc"
    )
    try:
        encrypted_auth.unlink()
    except FileNotFoundError:
        pass


def run_structured(
    installation_id: str,
    *,
    model: str,
    prompt: str,
    output_schema: dict[str, Any],
    priority: bool = False,
) -> dict[str, Any]:
    with CodexAppServer(
        installation_id, **({"priority": True} if priority else {})
    ) as client:
        account = client.request("account/read", {"refreshToken": True}, timeout=30)
        if not isinstance(account.get("account"), dict):
            raise CodexRuntimeError("codex_not_authenticated")
        available = {item["id"] for item in _model_options(client)}
        if model not in available:
            raise CodexRuntimeError("codex_model_unavailable")
        client.detach_credentials()
        thread = client.request(
            "thread/start",
            {
                "model": model,
                "cwd": str(client.home / "runtime"),
                "approvalPolicy": "never",
                "sandbox": "read-only",
                "personality": "none",
                "serviceName": "frontline_crcon_moderation",
                "ephemeral": True,
            },
        )
        thread_id = str((thread.get("thread") or {}).get("id") or "")
        if not thread_id:
            raise CodexRuntimeError("codex_thread_start_failed")
        client.request(
            "turn/start",
            {
                "threadId": thread_id,
                "input": [{"type": "text", "text": prompt}],
                "model": model,
                "effort": "low",
                "outputSchema": output_schema,
            },
        )
        final_text = ""
        deadline = monotonic() + client.settings.codex_request_timeout_seconds
        while monotonic() < deadline:
            notification = client.wait_notification(
                "turn/completed", timeout=max(1, int(deadline - monotonic()))
            )
            turn = (notification.get("params") or {}).get("turn") or {}
            if turn.get("status") != "completed":
                raise CodexRuntimeError("codex_turn_failed")
            for item in turn.get("items") or []:
                if item.get("type") == "agentMessage":
                    final_text = str(item.get("text") or "")
            break
        if not final_text:
            # item/completed is canonical and may arrive before turn/completed.
            for notification in reversed(client._notifications):
                if notification.get("method") != "item/completed":
                    continue
                item = (notification.get("params") or {}).get("item") or {}
                if item.get("type") == "agentMessage":
                    final_text = str(item.get("text") or "")
                    break
        try:
            return json.loads(final_text)
        except (TypeError, ValueError) as exc:
            raise CodexRuntimeError("codex_structured_output_invalid") from exc
