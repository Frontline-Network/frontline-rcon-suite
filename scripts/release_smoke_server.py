"""Isolated release-image test server. Never use as a production entrypoint.

Uses real Django authentication, migrations, appearance and release endpoints.
No RCON endpoints, production DB, Redis or external credentials are loaded.
All accounts/state live in a temporary SQLite database removed on exit.
The optional notes file is for prepublication CI only; final image tests read
the image's unmodified bundled snapshot and immutable version file instead.
"""
import argparse
import importlib
import io
from contextlib import ExitStack, redirect_stdout
import json
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "rconweb"))


def main():
    if os.environ.get("RELEASE_SMOKE_TEST") != "1":
        raise SystemExit("Set RELEASE_SMOKE_TEST=1 only in an isolated test environment")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8049)
    parser.add_argument("--bind", default="127.0.0.1")
    parser.add_argument("--frontend", type=Path)
    parser.add_argument("--notes-file", type=Path)
    args = parser.parse_args()
    expected_version = os.environ.get("RELEASE_VERSION", "v0.9.0")
    # Never inherit access to a production database or a private release token.
    for name in ("HLL_DB_URL", "HLL_REDIS_URL", "CRCON_RELEASES_GITHUB_TOKEN", "CRCON_RELEASES_GITHUB_TOKEN_FILE", "GITHUB_TOKEN", "GH_TOKEN"):
        os.environ.pop(name, None)
    os.environ.update(HLL_MAINTENANCE_CONTAINER="1", RCONWEB_TEST_MODE="1", SERVER_NUMBER="1")

    from django.apps import AppConfig
    from django.conf import settings
    from django.db.backends.sqlite3.base import DatabaseWrapper
    from rcon.version import resolve_version

    class IsolatedApi(AppConfig):
        name = "api"

    with TemporaryDirectory(prefix="release-smoke-") as directory, ExitStack() as cleanup:
        settings.configure(
            SECRET_KEY="isolated-release-smoke-only-never-for-production",
            TAG_VERSION=resolve_version(), DEBUG=False,
            ALLOWED_HOSTS=["localhost", "127.0.0.1", "backend"],
            # The shipped nginx forwards Host=backend:8000. As in a real
            # installation, trust only the explicitly configured public origin.
            CSRF_TRUSTED_ORIGINS=["http://127.0.0.1:8049"],
            ROOT_URLCONF=__name__, USE_TZ=True, TIME_ZONE="UTC",
            INSTALLED_APPS=["django.contrib.auth", "django.contrib.contenttypes", "django.contrib.sessions", IsolatedApi("api", importlib.import_module("api"))],
            DATABASES={"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": str(Path(directory) / "state.sqlite3")}},
            DEFAULT_AUTO_FIELD="django.db.models.AutoField",
            CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}},
            MIDDLEWARE=["django.contrib.sessions.middleware.SessionMiddleware",
                        "rconweb.middleware.SessionCsrfProtectionMiddleware",
                        "django.contrib.auth.middleware.AuthenticationMiddleware"],
            CSRF_FAILURE_VIEW="rconweb.csrf.csrf_failure",
            PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
            SILENCED_SYSTEM_CHECKS=["fields.E120", "models.W042"],
            LOGGING={"version": 1, "disable_existing_loggers": True},
        )
        # Historical migrations use unbounded CharFields (valid on PostgreSQL).
        DatabaseWrapper.data_types["CharField"] = "varchar"
        import django
        django.setup()
        from django.db import connections
        cleanup.callback(connections.close_all)
        # auth.py's legacy constants import must use these isolated settings.
        sys.modules["rconweb.settings"] = settings
        from django.core.management import call_command
        from django.contrib.auth.models import User
        from django.core.handlers.wsgi import WSGIHandler
        from django.core.servers.basehttp import WSGIServer, WSGIRequestHandler
        from django.http import HttpResponse, JsonResponse
        from django.urls import path, re_path
        from django.views.static import serve
        from api import auth, appearance, release_updates
        from api.models import UserAppearancePreference
        from rcon import release_channel

        # Explicitly stub ONLY the game's audit side effects, not auth/state/API.
        auth.set_registered_mods = lambda *_args, **_kwargs: None
        auth.heartbeat = lambda *_args, **_kwargs: None
        with redirect_stdout(io.StringIO()):
            call_command("migrate", verbosity=0, interactive=False)
        call_command("makemigrations", check=True, dry_run=True, verbosity=0)
        for username in ("vanguard", "aurora", "busy", "dialog", "separate", "csrf"):
            user = User.objects.create_user(username=username, password="isolated-test-only")
            UserAppearancePreference.objects.create(user=user, preferences={
                "preset": "wardogs" if username == "aurora" else "frontline-gold", "mode": "dark"
            })
        if args.notes_file:
            snapshot = Path(directory) / "prepublication-notes.json"
            snapshot.write_text(json.dumps({"checked_at": "2020-01-01T00:00:00Z", "releases": [{
                "tag_name": expected_version, "name": f"Frontline RCON Suite {expected_version}",
                "draft": False, "prerelease": False, "published_at": "2020-01-01T00:00:00Z",
                "body": args.notes_file.read_text(encoding="utf-8")
            }]}), encoding="utf-8")
            release_channel.SNAPSHOT_PATH = snapshot
        assert settings.TAG_VERSION == expected_version, settings.TAG_VERSION
        channel = release_channel.get_channel(settings.TAG_VERSION, expected_version, None)
        assert channel["status"] == "ready", channel
        current = next(entry for entry in channel["releases"] if entry["current"])
        assert current["tag_name"] == expected_version
        if expected_version == "v0.9.0":
            assert current["highlights"], "Missing real published highlights"

        def unavailable(request, endpoint):
            # No accidental access to a game server is possible through this URLconf.
            return JsonResponse({"failed": True, "result": None, "error": "Game endpoints disabled in isolated release verification"}, status=503)

        def frontend(request, route):
            if route == "tag_version":
                return HttpResponse(settings.TAG_VERSION, content_type="text/plain")
            if not args.frontend:
                return HttpResponse(status=404)
            asset = args.frontend / route
            return serve(request, route if asset.is_file() else "index.html", document_root=args.frontend)

        globals()["urlpatterns"] = [
            # Browser security tests load the production transport unchanged.
            # These routes exist ONLY in this isolated, opt-in test server.
            path("__test__/blank", lambda request: HttpResponse("<!doctype html><title>CSRF test</title>")),
            path("__test__/csrf-transport.mjs", lambda request: HttpResponse(
                (ROOT / "rcongui/src/utils/csrfTransport.mjs").read_text(encoding="utf-8"),
                content_type="application/javascript",
            )),
            path("api/login", auth.do_login),
            path("api/logout", auth.do_logout),
            path("api/is_logged_in", auth.is_logged_in),
            path("api/get_own_user_permissions", auth.get_own_user_permissions),
            path("api/get_own_user_appearance", appearance.get_own_user_appearance),
            path("api/set_own_user_appearance", appearance.set_own_user_appearance),
            path("api/get_update_channel", release_updates.get_update_channel),
            path("api/set_own_release_highlight_state", release_updates.set_own_release_highlight_state),
            re_path(r"^api/(?P<endpoint>.*)$", unavailable),
            re_path(r"^(?P<route>.*)$", frontend),
        ]
        server = WSGIServer((args.bind, args.port), WSGIRequestHandler)
        server.set_app(WSGIHandler())
        print(f"Isolated release verification ready on {args.bind}:{args.port}", flush=True)
        server.serve_forever()


if __name__ == "__main__":
    main()
