import os
import sys
from pathlib import Path

os.environ.setdefault("HLL_MAINTENANCE_CONTAINER", "1")
os.environ.setdefault("SERVER_NUMBER", "1")
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from django.db.backends.sqlite3.base import DatabaseWrapper  # noqa: E402

from .settings import *  # noqa: E402,F403

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}
ROOT_URLCONF = "rconweb.test_urls"
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
LOGGING = {"version": 1, "disable_existing_loggers": True}
SILENCED_SYSTEM_CHECKS = ["fields.E120", "models.W042"]

# Historical CRCON migrations contain an unbounded CharField. PostgreSQL accepts
# it, while SQLite renders varchar(None); the test backend does not need a limit.
DatabaseWrapper.data_types["CharField"] = "varchar"
