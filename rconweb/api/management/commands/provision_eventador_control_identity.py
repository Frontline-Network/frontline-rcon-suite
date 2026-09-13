"""Provision the least-privilege identity for Eventador control requests."""

from __future__ import annotations

import os
from pathlib import Path

from django.contrib.auth.models import Permission, User
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from api.models import DjangoAPIKey

USERNAME = "eventador-control"
KEY_NOTE = "Eventador control API v1"
MINIMUM_KEY_BYTES = 32
MAXIMUM_KEY_BYTES = 512


def _read_key(path_text: str) -> str:
    path = Path(path_text)
    if not path.is_absolute() or not path.is_file() or path.is_symlink():
        raise CommandError("--key-file must be an existing absolute regular file")
    if os.name == "posix" and path.stat().st_mode & 0o077:
        raise CommandError("--key-file must not be readable or writable by group/other")
    raw = path.read_bytes()
    if not MINIMUM_KEY_BYTES <= len(raw) <= MAXIMUM_KEY_BYTES:
        raise CommandError("the key file must contain 32 to 512 bytes")
    if b"\x00" in raw:
        raise CommandError("the key file contains invalid bytes")
    try:
        key = raw.decode("ascii").strip()
    except UnicodeDecodeError as exc:
        raise CommandError("the key file must contain ASCII") from exc
    if not MINIMUM_KEY_BYTES <= len(key) <= MAXIMUM_KEY_BYTES:
        raise CommandError("the key must contain 32 to 512 characters")
    if any(character.isspace() for character in key):
        raise CommandError("the key must not contain whitespace")
    return key


class Command(BaseCommand):
    help = "Create or rotate the exact least-privilege Eventador control identity"
    requires_system_checks = []

    def add_arguments(self, parser):
        parser.add_argument("--key-file", required=True)
        parser.add_argument(
            "--rotate",
            action="store_true",
            help="Replace every existing API key for the Eventador identity",
        )

    def handle(self, *args, **options):
        key = _read_key(options["key_file"])
        with transaction.atomic():
            permission = Permission.objects.select_related("content_type").get(
                content_type__app_label="api",
                codename="can_control_eventador_events",
            )
            user, _created = User.objects.select_for_update().get_or_create(
                username=USERNAME
            )
            existing = DjangoAPIKey.objects.select_for_update().filter(user=user)
            if existing.exists() and not options["rotate"]:
                raise CommandError(
                    "the Eventador identity already has a key; use --rotate explicitly"
                )
            user.is_active = True
            user.is_staff = False
            user.is_superuser = False
            user.set_unusable_password()
            user.save()
            user.groups.clear()
            user.user_permissions.clear()
            user.user_permissions.add(permission)
            existing.delete()
            DjangoAPIKey.objects.create(user=user, api_key=key, notes=KEY_NOTE)
        self.stdout.write(
            self.style.SUCCESS(
                "Provisioned the Eventador control identity; no key was printed"
            )
        )
