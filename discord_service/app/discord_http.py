"""Application-owned Discord connection pools, without shared request state.

Clients are short-lived and have their own headers/cookies. Only the transport
is borrowed, and only inside an application's request/background-task lifetime.
Standalone callers own and close their normal HTTPX client deterministically.
"""

from contextlib import asynccontextmanager, contextmanager
from contextvars import ContextVar

import httpx


def _limits():
    return httpx.Limits(
        max_connections=16, max_keepalive_connections=16, keepalive_expiry=30
    )


class _BorrowedTransport(httpx.BaseTransport):
    def __init__(self, owner):
        self.owner = owner

    def handle_request(self, request):
        # Keep HTTPX's environment proxy/NO_PROXY routing, including proxy pools.
        # The owning client never sends requests or retains response cookies.
        # This is the sole HTTPX-private compatibility seam; exercise it in tests.
        if self.owner.is_closed:
            raise RuntimeError("Discord HTTP pool is closed")
        transport = self.owner._transport_for_url(request.url)
        return transport.handle_request(request)

    def close(self):
        # A request must never close the application-owned connection pool.
        pass


class DiscordHTTPPool:
    def __init__(self):
        self._owner = httpx.Client(timeout=10, limits=_limits())
        if not callable(getattr(self._owner, "_transport_for_url", None)):
            self._owner.close()
            raise RuntimeError("HTTPX transport routing is unavailable")

    @contextmanager
    def client(self):
        with httpx.Client(
            timeout=10,
            transport=_BorrowedTransport(self._owner),
            trust_env=False,  # Routing and TLS environment belong to the owner.
        ) as client:
            yield client

    def close(self):
        self._owner.close()


_current_pool: ContextVar[DiscordHTTPPool | None] = ContextVar(
    "discord_http_pool", default=None
)


@contextmanager
def discord_http_client(injected=None):
    if injected is not None:
        # Test/explicit callers retain ownership of injected clients.
        yield injected
    elif (pool := _current_pool.get()) is not None:
        with pool.client() as client:
            yield client
    else:
        with httpx.Client(timeout=10, limits=_limits()) as client:
            yield client


@asynccontextmanager
async def discord_http_lifespan(app):
    pool = DiscordHTTPPool()
    app.state.discord_http_pool = pool
    try:
        yield
    finally:
        app.state.discord_http_pool = None
        pool.close()


class DiscordHTTPPoolMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        # Lifespan context variables do not propagate into independent ASGI
        # requests. Bind from this request's app, including sync thread workers.
        pool = getattr(scope["app"].state, "discord_http_pool", None)
        token = _current_pool.set(pool)
        try:
            await self.app(scope, receive, send)
        finally:
            _current_pool.reset(token)
