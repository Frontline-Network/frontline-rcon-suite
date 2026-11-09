"""In-container probes for rehearse_upgrade.py; never run against a live DB."""

import hashlib
import json
import os
import sys
from http.cookies import SimpleCookie
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen


def require_fixture_environment():
    if os.getenv("CRCON_UPGRADE_REHEARSAL") != "isolated":
        raise RuntimeError("This probe is only for the isolated upgrade rehearsal")
    if os.getenv("HLL_DB_HOST") != "127.0.0.1":
        raise RuntimeError(
            "Rehearsal database must be in the isolated network namespace"
        )


def setup_django():
    sys.path.insert(0, "/code/rconweb")
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "rconweb.settings")
    import django

    django.setup()


def seed():
    setup_django()
    from api.models import (
        DjangoAPIKey,
        UserAppearancePreference,
        UserLiveViewPreference,
    )
    from django.contrib.auth.models import Group, Permission, User

    user = User.objects.create_user(
        username=os.environ["REHEARSAL_USERNAME"],
        password=os.environ["REHEARSAL_PASSWORD"],
        email="rehearsal@example.invalid",
        is_staff=True,
        is_superuser=False,
    )
    group = Group.objects.create(name=os.environ["REHEARSAL_USERNAME"])
    permission = Permission.objects.get(codename="can_view_recent_logs")
    group.permissions.add(permission)
    user.groups.add(group)
    DjangoAPIKey.objects.create(
        user=user,
        api_key=os.environ["REHEARSAL_API_KEY"],
        notes="Isolated upgrade fixture",
    )
    UserAppearancePreference.objects.create(
        user=user,
        preferences={"preset": "wardogs", "mode": "dark", "customAccent": "#123456"},
    )
    UserLiveViewPreference.objects.create(user=user)
    print(json.dumps({"seeded": True, "superuser": False}))


def snapshot():
    import psycopg2
    from psycopg2 import sql

    connection = psycopg2.connect(os.environ["HLL_DB_URL"])
    connection.set_session(readonly=True)
    full_tables = {
        "auth_user",
        "auth_group",
        "auth_permission",
        "auth_group_permissions",
        "auth_user_groups",
        "auth_user_user_permissions",
        "api_djangoapikey",
        "api_steamplayer",
        "api_userappearancepreference",
        "api_userliveviewpreference",
        "api_userreleasehighlightstate",
        "api_discordreportintegration",
        "user_config",
        "player_vip",
        "player_flags",
        "player_watchlist",
        "blacklist",
        "blacklist_record",
        "message_template",
        "alembic_version",
        "django_migrations",
    }
    count_tables = {
        "log_lines",
        "player_stats",
        "map_history",
        "player_sessions",
        "player_account",
        "player_soldier",
        "player_vip",
        "players_actions",
        "player_comments",
        "admin_incident",
        "admin_incident_event",
        "audit_log",
    }
    result = {"hashes": {}, "counts": {}}

    class Sink:
        def __init__(self):
            self.digest = hashlib.sha256()

        def write(self, data):
            self.digest.update(data.encode() if isinstance(data, str) else data)

    with connection.cursor() as cursor:
        cursor.execute("SET LOCAL statement_timeout='180s'")
        cursor.execute("SELECT tablename FROM pg_tables WHERE schemaname='public'")
        tables = {row[0] for row in cursor.fetchall()}
        for table in sorted(full_tables & tables):
            sink = Sink()
            # Login changes last_login only for our synthetic account. Customer
            # users, including their password hashes and timestamps, stay exact.
            where = sql.SQL("")
            if table == "auth_user":
                where = sql.SQL(" WHERE username <> {} ").format(
                    sql.Literal(os.environ["REHEARSAL_USERNAME"])
                )
            query = sql.SQL(
                "COPY (SELECT row_to_json(t)::text FROM {} t {} "
                "ORDER BY row_to_json(t)::text) TO STDOUT"
            ).format(sql.Identifier(table), where)
            cursor.copy_expert(query.as_string(connection), sink)
            result["hashes"][table] = sink.digest.hexdigest()
        for table in sorted(count_tables & tables):
            query = sql.SQL("SELECT count(*) FROM {}").format(sql.Identifier(table))
            if table == "audit_log":
                # Denied permission probes are audited too. Keep those records,
                # but compare only the pre-existing/customer audit population.
                query += sql.SQL(" WHERE username <> {}").format(
                    sql.Literal(os.environ["REHEARSAL_USERNAME"])
                )
            cursor.execute(query)
            result["counts"][table] = cursor.fetchone()[0]
    connection.close()
    print(json.dumps(result, sort_keys=True))


def http_checks():
    base = "http://127.0.0.1:8000"
    cookies = {}
    timings = []

    def request(
        path,
        *,
        data=None,
        token=None,
        csrf=None,
        expected=200,
        session=True,
        method=None,
    ):
        import time

        headers = {"Content-Type": "application/json", "X-Forwarded-Proto": "https"}
        if session and cookies:
            headers["Cookie"] = "; ".join(f"{k}={v}" for k, v in cookies.items())
        if token:
            headers["Authorization"] = "Bearer " + token
        if csrf:
            headers["X-CSRFToken"] = csrf
        req = Request(
            base + path,
            data=json.dumps(data).encode() if data is not None else None,
            headers=headers,
            method=method,
        )
        start = time.monotonic()
        try:
            response = urlopen(req, timeout=20)
        except HTTPError as error:
            response = error
        body = response.read()
        assert response.status == expected, (path, response.status, expected)
        for header in response.headers.get_all("Set-Cookie", []):
            parsed = SimpleCookie(header)
            cookies.update({k: value.value for k, value in parsed.items()})
        timings.append(
            {
                "path": path,
                "status": response.status,
                "bytes": len(body),
                "milliseconds": round((time.monotonic() - start) * 1000, 2),
            }
        )
        result = (
            json.loads(body)
            if body
            and response.headers.get("Content-Type", "").startswith("application/json")
            else None
        )
        if expected == 200 and path.startswith("/api/"):
            assert result is not None and result.get("failed") is False, path
        return result

    request("/healthz", expected=204)
    anonymous = request("/api/is_logged_in")
    assert anonymous["result"]["authenticated"] is False
    login = request(
        "/api/login",
        data={
            "username": os.environ["REHEARSAL_USERNAME"],
            "password": os.environ["REHEARSAL_PASSWORD"],
        },
    )
    assert login["result"] is True
    assert request("/api/is_logged_in")["result"]["authenticated"] is True
    request("/admin/")
    preferences = request("/api/get_own_user_appearance")["result"]
    assert (
        preferences["preset"] == "wardogs" and preferences["customAccent"] == "#123456"
    )
    request("/api/get_own_user_live_view")
    # No valid CSRF token: this must fail before any preference can be written.
    request(
        "/api/set_own_user_appearance", data=preferences, method="PUT", expected=403
    )
    api_preferences = request(
        "/api/get_own_user_appearance",
        token=os.environ["REHEARSAL_API_KEY"],
        session=False,
    )
    assert api_preferences["result"] == preferences
    request(
        "/api/get_own_user_appearance",
        token="invalid-upgrade-fixture",
        session=False,
        expected=401,
    )
    # The fixture has only the log-reading permission, never sanction rights.
    request(
        "/api/kick",
        token=os.environ["REHEARSAL_API_KEY"],
        session=False,
        data={"player_id": "not-a-real-player", "reason": "isolated denied action"},
        expected=403,
    )
    request(
        "/api/get_recent_logs", token=os.environ["REHEARSAL_API_KEY"], session=False
    )
    import socket

    with socket.create_connection(("127.0.0.1", 8001), timeout=3) as sock:
        sock.sendall(
            b"GET /ws/barricade HTTP/1.1\r\nHost: 127.0.0.1\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==\r\nSec-WebSocket-Version: 13\r\n\r\n"
        )
        assert b"403" in sock.recv(4096).split(b"\r\n", 1)[0]
    print(
        json.dumps(
            {
                "http": timings,
                "websocket_unauthorized": 403,
                "login": True,
                "api_key": True,
                "csrf": True,
                "permission_denial": True,
            }
        )
    )


if __name__ == "__main__":
    require_fixture_environment()
    {"seed": seed, "snapshot": snapshot, "http": http_checks}[sys.argv[1]]()
