"""Isolated PostgreSQL settings for the Eventador provider contract tests."""

from .settings import *  # noqa: F403

CACHES = {  # noqa: F405
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "eventador-control-tests",
    }
}
CHANNEL_LAYERS = {  # noqa: F405
    "default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}
}
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]  # noqa: F405
LOGGING = {  # noqa: F405
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "WARNING"},
}
