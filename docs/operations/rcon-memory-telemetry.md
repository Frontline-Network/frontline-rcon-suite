# RCON container memory telemetry

The system sidebar shows RAM of the instance's dedicated RCON services. Shared
services are displayed separately, and the details also show their combined
service RAM. Shared services are counted once in full, not assigned an estimated
per-instance fraction. Totals for different RCON instances must therefore not be
added together when they include the same shared services.

Service RAM excludes all disk-backed file cache, including active cache. On
cgroup v2 it is `memory.current - clamp(file - shmem, 0, memory.current)`; shared
memory remains included. On cgroup v1 matching hierarchical cache/shmem counters
are used, or matching local counters. Missing cache counters mean service RAM is
unknown, never a fallback to the full charge. File cache and raw charges are not
shown in the sidebar, tooltips, details, or history. The original full-charge API
fields remain compatible. There is no total percentage or synthetic sum of
container limits, which can overlap or exceed host capacity.

## Host collector

Run `scripts/collect_rcon_memory.py` on the Docker host. Only the host collector
needs Docker access. Never mount the Docker socket, host `/proc`, or host cgroups
in the application backend. The backend receives a read-only directory containing
only its small resource snapshot. The collector reads cgroup counters, not player
data, logs, environment variables, database records, or credentials.

Configuration explicitly selects each component by Compose project and service.
Do not select other tenants, test installations, statistics websites, or general
host services. Additional shared Discord, callback, or push services belong in the
list only when they serve this installation. Each logical component alias must be
unique. Replicas of one selected service are aggregated; the same container cannot
be counted under multiple aliases. Known stopped components contribute zero; a
missing component or failed counter read makes the snapshot incomplete.

Example for a single-instance Compose project:

```json
{
  "server_number": 1,
  "components": [
    {"service": "backend", "project": "my-rcon", "compose_service": "backend_1", "category": "dedicated"},
    {"service": "supervisor", "project": "my-rcon", "compose_service": "supervisor_1", "category": "dedicated"},
    {"service": "frontend", "project": "my-rcon", "compose_service": "frontend_1", "category": "dedicated"},
    {"service": "redis", "project": "my-rcon", "compose_service": "redis", "category": "shared"},
    {"service": "postgres", "project": "my-rcon", "compose_service": "postgres", "category": "shared"},
    {"service": "webhook", "project": "my-rcon", "compose_service": "webhook_service", "category": "shared"},
    {"service": "background_worker", "project": "my-rcon", "compose_service": "frontline_background_worker", "category": "shared"},
    {"service": "maintenance", "project": "my-rcon", "compose_service": "maintenance", "category": "shared"}
  ]
}
```

Adapt this configuration to the actual active deployment; the project name and
server number are installation-specific. Keep the configuration root-owned and
not writable by the application or other users.

Install the collector and template units on the host, then run one collection
before enabling the timer:

```sh
sudo install -d -m 755 /usr/local/lib/frontline-rcon /etc/frontline-rcon
sudo install -d -m 755 /var/lib/frontline-rcon/memory/1
sudo install -m 755 scripts/collect_rcon_memory.py /usr/local/lib/frontline-rcon/
sudo install -m 644 scripts/frontline-rcon-memory@.service scripts/frontline-rcon-memory@.timer /etc/systemd/system/
# Install the reviewed instance-specific JSON at /etc/frontline-rcon/memory-1.json.
sudo chmod 600 /etc/frontline-rcon/memory-1.json
sudo chown root:root /etc/frontline-rcon/memory-1.json
sudo systemctl daemon-reload
sudo systemctl start frontline-rcon-memory@1.service
sudo systemctl enable --now frontline-rcon-memory@1.timer
```

Bind `/var/lib/frontline-rcon/memory/1` read-only into backend 1 at
`/run/frontline-resource-usage`, and set
`HLL_RESOURCE_USAGE_FILE=/run/frontline-resource-usage/usage.json` in that backend's
environment. Mount the directory, not the file: the collector replaces the JSON
atomically, and a single-file bind would keep exposing the old inode.

```yaml
services:
  backend_1:
    environment:
      HLL_RESOURCE_USAGE_FILE: /run/frontline-resource-usage/usage.json
    volumes:
      - type: bind
        source: /var/lib/frontline-rcon/memory/1
        target: /run/frontline-resource-usage
        read_only: true
        bind:
          create_host_path: false
```

The timer runs every 15 seconds with a short-lived process, a 128 MiB memory cap,
and a 25%-of-one-core CPU cap. The API keeps its existing bounded sampling
interval and one-hour history. Missing, incomplete, malformed, oversized, stale
(more than 60 seconds old), or wrong-instance snapshots are unavailable, never a
zero or the backend value labelled as the complete RCON sum. The existing
`ram_usage` API field remains backwards-compatible; the additive
`rcon_ram_usage` field contains the complete configured container set. Its
`service_ram_available`, `service_used_bytes`, `dedicated_service_used_bytes`,
and `shared_service_used_bytes` fields drive the display. New derived history
fields are used instead of the legacy raw-charge history. The collector retains
`file_cache_bytes` internally for this calculation; it is not displayed.

## Update and recovery

Preserve the backend's read-only bind, environment variable, reviewed collector
configuration, and enabled timer during future image updates. The snapshot schema
is versioned. Install a matching collector script if a later release changes its
protocol. Neither the timer nor the application restarts containers to reduce RAM.

Validate the API against an independent host cgroup reading, including all
configured component aliases and the shared subtotal. Check the sidebar and its
RAM-details dialog in German, English, and French. Test missing and stale
snapshots, a stopped component, and an interrupted collector before relying on
the display. Use `systemctl status frontline-rcon-memory@1.timer` and
`journalctl -u frontline-rcon-memory@1.service` for collector failures; do not print
private deployment configuration when sharing diagnostics.

To disable collection, stop and disable only this instance's timer. Preserve its
configuration for recovery. The application will explicitly mark the sum
unavailable once the final snapshot expires. Restoring the previous image does
not require a database change or deletion of any queued message.
