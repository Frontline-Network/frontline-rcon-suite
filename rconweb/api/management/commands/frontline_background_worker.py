"""Run independent Frontline delivery loops in one shared Python process."""

from __future__ import annotations

import os
from queue import Queue
from threading import Thread

from django.core.management.base import BaseCommand, CommandError
from django.db import connections

from api.management.commands.discord_report_worker import Command as DiscordCommand
from api.management.commands.mobile_push_worker import Command as MobileCommand
from api.mobile_settings import mobile_integration_enabled
from rcon.incident_settings import ai_moderation_enabled, discord_reports_enabled


class Command(BaseCommand):
    help = "Run Mobile Push and independent Discord delivery loops concurrently"
    requires_system_checks = []

    def _worker_specs(self):
        specs = []
        if mobile_integration_enabled() and os.getenv("MOBILE_PUSH_RELAY_URL", ""):
            specs.append(("mobile-push", MobileCommand(), {}))
        if discord_reports_enabled():
            specs.append(
                (
                    "discord-events",
                    DiscordCommand(),
                    {"events_only": True, "moderation_only": False},
                )
            )
            if ai_moderation_enabled():
                specs.append(
                    (
                        "discord-moderation",
                        DiscordCommand(),
                        {"events_only": False, "moderation_only": True},
                    )
                )
        return specs

    def handle(self, *args, **options):
        specs = self._worker_specs()
        if not specs:
            raise CommandError(
                "No Frontline background integration is enabled for this container"
            )

        # App startup may have opened a Django connection on the main thread.
        # The actual loops use thread-local connections, so do not retain an
        # otherwise unused fourth connection for the process lifetime.
        connections.close_all()
        completed = Queue()

        def run(name, command, command_options):
            command.stdout = self.stdout
            command.stderr = self.stderr
            try:
                command.handle(**command_options)
            except BaseException as exc:
                completed.put((name, exc))
            else:
                completed.put(
                    (name, RuntimeError("background worker returned unexpectedly"))
                )

        self.stdout.write(
            "Frontline combined background worker started: "
            + ", ".join(name for name, _, _ in specs)
        )
        for name, command, command_options in specs:
            Thread(
                target=run,
                args=(name, command, command_options),
                name=f"frontline-{name}",
                daemon=True,
            ).start()

        failed_name, failure = completed.get()
        raise CommandError(
            f"Frontline background loop {failed_name} stopped: "
            f"{type(failure).__name__}"
        ) from failure
