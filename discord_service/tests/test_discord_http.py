"""No external I/O: exercise the real HTTPX routing and ownership boundary."""

from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Event, Lock, Thread
from time import monotonic, sleep

import httpx
import pytest
from fastapi import BackgroundTasks, FastAPI
from fastapi.testclient import TestClient

from discord_service.app import discord_http as transport
from discord_service.app.config import Settings
from discord_service.app.discord_client import DiscordClient


def settings(token="test-token"):
    return Settings(dry_run=False, discord_bot_token=token)


@pytest.fixture
def wire(monkeypatch):
    for name in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY"):
        monkeypatch.delenv(name, raising=False)
        monkeypatch.delenv(name.lower(), raising=False)
    created, closed, requests = [], [], []
    lock = Lock()
    original_init = httpx.HTTPTransport.__init__
    original_close = httpx.HTTPTransport.close
    original_exit = httpx.HTTPTransport.__exit__
    state = {"status": 200, "guild": "123"}

    def init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        created.append(self)

    def close(self):
        closed.append(self)
        original_close(self)

    def exit(self, *args):
        closed.append(self)
        original_exit(self, *args)

    def handle(self, request):
        with lock:
            requests.append((self, request))
        if state.get("error"):
            raise httpx.ReadTimeout("synthetic failure", request=request)
        if request.url.path.endswith("/roles"):
            body = [{"id": "9", "name": state.get("role", "Admin")}]
        elif request.url.path.endswith("/channels") and request.method == "GET":
            body = [{"id": "456", "name": "Reports", "type": 0}]
        else:
            body = {"id": str(id(self)), "guild_id": state["guild"]}
        return httpx.Response(
            state["status"], json=body,
            headers={"set-cookie": "private_cookie=must-not-cross-operations; Path=/"},
        )

    monkeypatch.setattr(httpx.HTTPTransport, "__init__", init)
    monkeypatch.setattr(httpx.HTTPTransport, "close", close)
    monkeypatch.setattr(httpx.HTTPTransport, "__exit__", exit)
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", handle)
    return created, closed, requests, state


def make_app():
    app = FastAPI(lifespan=transport.discord_http_lifespan)
    app.add_middleware(transport.DiscordHTTPPoolMiddleware)

    @app.get("/send")
    def send(token: str, tasks: BackgroundTasks):
        client = DiscordClient(settings(token))
        result = client.upsert("456", {"content": "unchanged"}, "789")
        tasks.add_task(client.validate_channel, "456", "123")
        return {"transport": result}

    return app


def test_app_reuses_one_bounded_pool_closes_all_leases_and_shutdown(wire, monkeypatch):
    created, closed, requests, _ = wire
    client_closes = []
    original_exit = httpx.Client.__exit__

    def exit(client, *args):
        client_closes.append(client)
        original_exit(client, *args)

    monkeypatch.setattr(httpx.Client, "__exit__", exit)
    app = make_app()
    with TestClient(app) as http:
        owner = app.state.discord_http_pool._owner
        for _ in range(100):
            assert http.get("/send", params={"token": "one"}).status_code == 200
        assert len(created) == 1
        assert not closed
        assert len(requests) == 200  # Includes sync background-task leases.
        assert sum(client is not owner for client in client_closes) == 200
        assert all(client.is_closed for client in client_closes)
        assert not owner.cookies
        assert all("cookie" not in request.headers for _, request in requests)
        assert owner._transport._pool._max_connections == 16
        assert owner._transport._pool._max_keepalive_connections == 16
    assert owner.is_closed
    assert closed == created
    assert app.state.discord_http_pool is None
    assert transport._current_pool.get() is None


def test_concurrent_apps_have_separate_pools_and_request_auth(wire):
    created, closed, requests, _ = wire
    first, second = make_app(), make_app()
    with TestClient(first) as a, TestClient(second) as b:
        def send(index):
            token, http = ("one", a) if index % 2 else ("two", b)
            return token, http.get("/send", params={"token": token}).json()["transport"]

        with ThreadPoolExecutor(max_workers=8) as executor:
            results = list(executor.map(send, range(40)))
        pools = {token: {value for key, value in results if key == token}
                 for token in ("one", "two")}
        assert len(created) == 2
        assert len(pools["one"]) == len(pools["two"]) == 1
        assert pools["one"].isdisjoint(pools["two"])
        for pool, request in requests:
            expected = "one" if str(id(pool)) in pools["one"] else "two"
            assert request.headers["authorization"] == f"Bot {expected}"
            assert "cookie" not in request.headers
    assert set(closed) == set(created)


def test_private_dm_borrows_pool_without_closing_it(wire, monkeypatch):
    from discord_service.app import player_panel

    created, closed, requests, _ = wire
    monkeypatch.setattr(player_panel, "DiscordClient", lambda: DiscordClient(settings()))
    pool = transport.DiscordHTTPPool()
    token = transport._current_pool.set(pool)
    try:
        player_panel.private_dm("42", {"content": "private"}, "nonce")
        assert DiscordClient(settings()).upsert("456", {})
        assert len(created) == 1
        assert not closed
        assert len(requests) == 3
        assert requests[0][1].url.path.endswith("/users/@me/channels")
        assert "cookie" not in requests[-1][1].headers
    finally:
        transport._current_pool.reset(token)
        pool.close()
    assert closed == created


def test_standalone_and_error_paths_close_owned_resources(wire):
    created, closed, _, state = wire
    client = DiscordClient(settings())
    client.validate_channel("456", "123")
    state["guild"] = "different"
    with pytest.raises(ValueError, match="does not belong"):
        client.validate_channel("456", "123")
    state["status"] = 403
    with pytest.raises(httpx.HTTPStatusError):
        client.upsert("456", {})
    state["error"] = True
    with pytest.raises(httpx.ReadTimeout):
        client.upsert("456", {})
    assert len(created) == 4
    assert created == closed


def test_permissions_are_fetched_again_and_shared_pool_survives_failure(wire):
    created, closed, requests, state = wire
    pool = transport.DiscordHTTPPool()
    token = transport._current_pool.set(pool)
    try:
        client = DiscordClient(settings())
        assert client.guild_options("123")["roles"][0]["name"] == "Admin"
        state["role"] = "Removed permission"
        assert client.guild_options("123")["roles"][0]["name"] == "Removed permission"
        state["status"] = 403
        with pytest.raises(httpx.HTTPStatusError):
            client.upsert("456", {})
        state["status"] = 200
        assert client.upsert("456", {})
        state["error"] = True
        with pytest.raises(httpx.ReadTimeout):
            client.upsert("456", {})
        state["error"] = False
        assert client.upsert("456", {})
        assert len(created) == 1
        assert not closed
        assert len(requests) == 10
    finally:
        transport._current_pool.reset(token)
        pool.close()


def test_injected_client_remains_borrowed_and_dry_run_allocates_nothing(wire):
    api = httpx.Client(transport=httpx.MockTransport(
        lambda request: httpx.Response(200, json={"id": "789"})
    ))
    try:
        assert DiscordClient(settings(), client=api).upsert("456", {}) == "789"
        assert not api.is_closed
        assert DiscordClient(Settings(dry_run=True)).upsert("456", {}, "789") == "789"
        assert not wire[0]
    finally:
        api.close()


def test_proxy_and_no_proxy_use_owners_httpx_routing(wire, monkeypatch):
    monkeypatch.setenv("HTTPS_PROXY", "http://proxy.invalid:8080")
    monkeypatch.setenv("NO_PROXY", "direct.invalid")
    created, closed, requests, _ = wire
    pool = transport.DiscordHTTPPool()
    try:
        with pool.client() as http:
            http.get("https://discord.com/api/v10/channels/456")
            http.get("https://direct.invalid/test")
        assert len(created) == 2
        assert requests[0][0] is not pool._owner._transport
        assert requests[1][0] is pool._owner._transport
        assert not closed
    finally:
        pool.close()
    assert set(created) == set(closed)


def test_closed_pool_rejects_new_requests(wire):
    pool = transport.DiscordHTTPPool()
    pool.close()
    with pool.client() as http:
        with pytest.raises(RuntimeError, match="pool is closed"):
            http.get("https://discord.com/api/v10/channels/456")


def test_httpx_routing_compatibility_failure_closes_owner(wire, monkeypatch):
    monkeypatch.setattr(httpx.Client, "_transport_for_url", None)
    with pytest.raises(RuntimeError, match="routing is unavailable"):
        transport.DiscordHTTPPool()
    assert wire[0] == wire[1]


def test_busy_loopback_pool_reuses_connections_for_waiting_requests(monkeypatch):
    """Real HTTP/1.1: eight queued requests reuse the first sixteen sockets."""
    for name in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY"):
        monkeypatch.delenv(name, raising=False)
        monkeypatch.delenv(name.lower(), raising=False)
    release = Event()
    sixteen_active = Event()
    lock = Lock()
    accepted = 0
    entered = 0

    class Server(ThreadingHTTPServer):
        # server_close joins request threads after pool.close releases their
        # keepalive reads, including when an assertion fails midway through.
        daemon_threads = False
        block_on_close = True

        def get_request(self):
            nonlocal accepted
            result = super().get_request()
            with lock:
                accepted += 1
            return result

    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def do_GET(self):
            nonlocal entered
            with lock:
                entered += 1
                if entered == 16:
                    sixteen_active.set()
            if not release.wait(10):
                self.send_error(504)
                return
            self.send_response(200)
            self.send_header("Content-Length", "2")
            self.end_headers()
            self.wfile.write(b"ok")

        def log_message(self, *_args):
            pass

    server = Server(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    pool = transport.DiscordHTTPPool()
    executor = ThreadPoolExecutor(max_workers=24)
    url = f"http://127.0.0.1:{server.server_port}/probe"

    def request():
        with pool.client() as client:
            response = client.get(url)
            response.raise_for_status()
            return response.text

    try:
        futures = [executor.submit(request) for _ in range(24)]
        assert sixteen_active.wait(5), "16 requests never reached the local server"
        core_pool = pool._owner._transport._pool
        deadline = monotonic() + 5
        queued = False
        while monotonic() < deadline:
            with core_pool._optional_thread_lock:
                queued = len(core_pool._requests) == 24
            if queued:
                break
            sleep(0.005)
        assert queued, "eight requests never queued behind the busy pool"
        release.set()
        assert [future.result(timeout=10) for future in futures] == ["ok"] * 24
        assert accepted <= 16, "idle sockets were retired instead of reused"
    finally:
        release.set()
        executor.shutdown(wait=True, cancel_futures=True)
        pool.close()
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
        assert not thread.is_alive()
