"""Lightweight readiness probe for the CRCON HTTP and WebSocket servers."""

from __future__ import annotations

import socket
import sys
import urllib.request


HTTP_HEALTH_URL = "http://127.0.0.1:8000/healthz"
WEBSOCKET_ADDRESS = ("127.0.0.1", 8001)
TIMEOUT_SECONDS = 3


def check_http() -> None:
    request = urllib.request.Request(HTTP_HEALTH_URL, method="GET")
    with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
        if response.status != 204:
            raise RuntimeError(f"unexpected HTTP health status: {response.status}")


def check_websocket_listener() -> None:
    with socket.create_connection(WEBSOCKET_ADDRESS, timeout=TIMEOUT_SECONDS):
        pass


def main() -> int:
    try:
        check_http()
        check_websocket_listener()
    except (OSError, RuntimeError) as exc:
        print(f"backend not ready: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
