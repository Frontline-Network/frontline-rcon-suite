import os
import sys
from pathlib import Path

os.environ.setdefault("HLL_MAINTENANCE_CONTAINER", "1")
os.environ.setdefault("RCONWEB_TEST_MODE", "1")
os.environ.setdefault("SERVER_NUMBER", "1")
# The production entrypoint adds the outer ``rconweb/`` directory to
# ``sys.path`` so the historical ``api`` Django app is importable. Repository-
# root pytest runs need the same layout before Django populates INSTALLED_APPS.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from django.db.backends.sqlite3.base import DatabaseWrapper  # noqa: E402

from . import settings as _runtime_settings  # noqa: E402
from .settings import *  # noqa: E402,F403

# Production imports this package as ``rconweb.settings`` because manage.py
# places the outer rconweb directory on sys.path. Repository-root tests load
# this module through ``rconweb.rconweb`` instead, so expose the same canonical
# module name before Django imports the historical ``api`` application.
sys.modules.setdefault("rconweb.settings", _runtime_settings)

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}
ROOT_URLCONF = "rconweb.rconweb.test_urls"
CSRF_FAILURE_VIEW = "rconweb.rconweb.csrf.csrf_failure"
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    # Production owns dedicated file/console handlers. Tests need RCON records
    # to reach pytest's root capture handler so logging assertions remain
    # deterministic after Django initializes during collection.
    "loggers": {
        "rcon": {"handlers": [], "level": "DEBUG", "propagate": True},
    },
}
SILENCED_SYSTEM_CHECKS = ["fields.E120", "models.W042"]

# Historical CRCON migrations contain an unbounded CharField. PostgreSQL accepts
# it, while SQLite renders varchar(None); the test backend does not need a limit.
DatabaseWrapper.data_types["CharField"] = "varchar"
