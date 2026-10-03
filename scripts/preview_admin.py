"""Run the real Django admin against isolated local demo data (Django only).

Usage: python scripts/preview_admin.py [--port 8042] [--test]
No production settings, RCON connections, credentials or databases are loaded.
"""

import argparse
import json
import secrets
import sys
from pathlib import Path

from django.apps import AppConfig
from django.conf import settings

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "rconweb"
DATA = ROOT.parent / "output" / "wardogs-admin-preview"
sys.path.insert(0, str(WEB))


class PreviewApiConfig(AppConfig):
    """Use the real models, without production startup callbacks to RCON."""

    name = "api"


def configure():
    DATA.mkdir(parents=True, exist_ok=True)
    secret_file = DATA / "secret.txt"
    if not secret_file.exists():
        secret_file.write_text(secrets.token_urlsafe(48), encoding="utf-8")
    settings.configure(
        SECRET_KEY=secret_file.read_text(encoding="utf-8"),
        DEBUG=True,
        ALLOWED_HOSTS=["127.0.0.1", "localhost", "testserver"],
        ROOT_URLCONF=__name__,
        INSTALLED_APPS=[
            "django.contrib.admin", "django.contrib.auth",
            "django.contrib.contenttypes", "django.contrib.sessions",
            "django.contrib.messages", "django.contrib.staticfiles",
            f"{__name__}.PreviewApiConfig",
        ],
        MIDDLEWARE=[
            "django.contrib.sessions.middleware.SessionMiddleware",
            "django.middleware.common.CommonMiddleware",
            "django.middleware.csrf.CsrfViewMiddleware",
            "django.contrib.auth.middleware.AuthenticationMiddleware",
            "django.contrib.messages.middleware.MessageMiddleware",
            "api.admin_embedding.AdminEmbeddingMiddleware",
            "django.middleware.clickjacking.XFrameOptionsMiddleware",
        ],
        DATABASES={"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": DATA / "demo.sqlite3"}},
        MIGRATION_MODULES={app: None for app in ("api", "admin", "auth", "contenttypes", "sessions")},
        DEFAULT_AUTO_FIELD="django.db.models.AutoField",
        LANGUAGE_CODE="de",
        USE_I18N=True,
        USE_TZ=True,
        TIME_ZONE="Europe/Berlin",
        STATIC_URL="/djangostatic/",
        STATICFILES_DIRS=[WEB / "static"],
        TEMPLATES=[{
            "BACKEND": "django.template.backends.django.DjangoTemplates",
            "DIRS": [WEB / "templates"], "APP_DIRS": True,
            "OPTIONS": {"context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                *(["api.admin_theme.admin_appearance"] if (WEB / "api/admin_theme.py").exists() else []),
            ]},
        }],
        SESSION_COOKIE_NAME="crcon_admin_preview_session",
        CSRF_COOKIE_NAME="crcon_admin_preview_csrf",
        SILENCED_SYSTEM_CHECKS=["fields.E120"],
    )
    # Match the project's test backend for the historical unbounded CharField.
    from django.db.backends.sqlite3.base import DatabaseWrapper
    DatabaseWrapper.data_types["CharField"] = "varchar"
    import django
    django.setup()
    from django.contrib import admin
    from django.urls import path
    globals()["urlpatterns"] = [path("admin/", admin.site.urls)]


def seed_demo():
    from django.contrib.auth.models import Group, Permission, User
    from django.core.management import call_command
    from api.models import MobileDevice, SteamPlayer, UserAppearancePreference
    call_command("migrate", run_syncdb=True, verbosity=0)
    credential_file = DATA / "credentials.json"
    if not credential_file.exists():
        credential_file.write_text(json.dumps({"username": "preview", "password": secrets.token_urlsafe(24)}), encoding="utf-8")
    credentials = json.loads(credential_file.read_text(encoding="utf-8"))
    owner, created = User.objects.get_or_create(username=credentials["username"], defaults={"is_staff": True, "is_superuser": True, "first_name": "Frontline", "last_name": "Vorschau"})
    if created:
        owner.set_password(credentials["password"])
        owner.save()
    UserAppearancePreference.objects.get_or_create(user=owner, defaults={"preferences": {"preset": "wardogs", "mode": "dark"}})
    for name in ("Administratoren", "Moderatoren", "Support"):
        group, created = Group.objects.get_or_create(name=name)
        # Harmless fixture data, exclusively in this isolated local demo database.
        if created:
            group.permissions.add(*Permission.objects.filter(codename__in=("can_view_gamestate", "can_view_recent_logs")))
    for name, first, group in (("fln.raven", "Raven", "Administratoren"), ("fln.bravo", "Bravo", "Moderatoren"), ("fln.wolf", "Wolf", "Support")):
        user, created = User.objects.get_or_create(username=name, defaults={"first_name": first, "is_staff": True})
        if created:
            user.set_unusable_password()
            user.save()
            user.groups.add(Group.objects.get(name=group))
            SteamPlayer.objects.create(user=user, steam_id_64="76561198000000001")
    MobileDevice.objects.get_or_create(name="Demo · Einsatz-Tablet", user=owner, defaults={"platform": "android", "app_version": "Vorschau"})
    print(f"Local demo credentials: {credential_file}", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8042)
    parser.add_argument("--test", action="store_true")
    args = parser.parse_args()
    configure()
    from django.core.management import call_command
    if args.test:
        call_command("test", "api.test_admin_theme", verbosity=1)
    else:
        seed_demo()
        call_command("runserver", f"127.0.0.1:{args.port}", use_reloader=False)
