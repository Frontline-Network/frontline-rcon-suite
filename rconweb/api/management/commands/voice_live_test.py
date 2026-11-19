"""Operator-only management command for a single RCON3 volunteer case."""

import json
from django.core.management.base import BaseCommand, CommandError

from rcon import voice_live_test
from rcon.api_commands import get_rcon_api
from rcon.leadership_vote.service import read_context
from rcon.utils import get_server_number


class Command(BaseCommand):
    help = "Arm, inspect or cancel one ten-minute Vietnam voice pilot test"
    requires_system_checks = []

    def add_arguments(self, parser):
        parser.add_argument("--server", type=int, required=True)
        sub = parser.add_subparsers(dest="operation", required=True)
        arm = sub.add_parser("arm")
        arm.add_argument("--target-id", required=True)
        arm.add_argument("--reporter-id", required=True)
        chat = sub.add_parser("chat")
        chat.add_argument("--reporter-id", required=True)
        chat.add_argument("--minutes", type=int, required=True)
        sub.add_parser("status")
        sub.add_parser("cancel").add_argument("--window", required=True)

    def handle(self, *args, **options):
        from rcon.types import GameEnum

        server = options["server"]
        if server != int(get_server_number()):
            raise CommandError("Run in the backend for the selected server")
        try:
            if options["operation"] in {"arm", "chat"}:
                api = get_rcon_api()
                if api.game_profile.game != GameEnum.HLL_VIETNAM:
                    raise ValueError(
                        "This one-time pilot command requires Hell Let Loose Vietnam"
                    )
                context = read_context(api)
                if options["operation"] == "chat":
                    voice_live_test.arm_chat(server, options["reporter_id"], context, options["minutes"])
                else:
                    voice_live_test.arm(server, options["target_id"], options["reporter_id"], context)
            elif options["operation"] == "cancel":
                voice_live_test.cancel(server, options["window"])
            self.stdout.write(json.dumps(voice_live_test.inspect_window(server)))
        except ValueError as exc:
            raise CommandError(str(exc)) from exc
