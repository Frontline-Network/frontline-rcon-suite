# Discord HTTP transport ownership

The FastAPI lifespan owns one `DiscordHTTPPool`. Request middleware borrows that
app's pool through a context variable, including synchronous routes and their
background tasks. App shutdown closes its transport owner. Other app lifespans
have separate owners; no process-global pool remains after shutdown.

Each Discord operation creates a short-lived HTTPX client and closes it using a
context manager. The borrowed transport adapter leaves the application's pool
open. Headers and cookie jars belong to the operation, so authorization and
response cookies cannot carry across installations. The owner itself never sends
requests and never collects response cookies. Caller-injected clients remain
caller-owned. Standalone operations, including the panel publishing command,
create and close their own normal HTTPX clients.

Each routing transport is limited to 16 concurrent connections and 16 idle
keepalive connections, with 30 seconds idle expiry. If environment proxies create
multiple routing transports, each has its own limit; 16 is not an application-wide
sum across proxies. The existing 10-second timeout and HTTPX's default
zero transport retries remain. HTTPX's
normal environment proxy, NO_PROXY and certificate behavior is preserved by the
owner. `_BorrowedTransport` encapsulates one private HTTPX method,
`Client._transport_for_url`; tests exercise its availability, direct/proxy routing
and closed-owner behavior. Check these tests when upgrading HTTPX.

The keepalive limit matches the connection limit deliberately. HTTPcore 1.0.9's
surplus-idle check counts all pool entries, including busy connections. A lower
keepalive limit can retire each newly idle socket under load before a waiting
request reuses it. Matching the limits avoids that churn while keeping the same
16-connection bound per routing transport and 30-second idle expiry.

This caches connections, not responses. Guild, role and channel checks still make
fresh HTTP calls. Report contents, message IDs, receipt/idempotency handling,
permissions and retries are unchanged. No database migration or configuration
change is needed.

## Measuring the benefit

Replay the same report-create/edit, private-DM and channel/guild-check sequence
against a local fake Discord server in separate baseline/candidate processes.
Compare response/request traces, transport creation/closure counts, descriptors,
sockets and PSS/RSS before load, after warmup and after idle. Exercise HTTP errors
and timeouts too. Count expensive connection/TLS transport pools separately from
the intentionally short-lived client wrappers. Unit tests establish ownership
and isolation; they do not establish RAM savings in production.
