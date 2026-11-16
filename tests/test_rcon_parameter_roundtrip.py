"""RCON command text survives both JSON layers without extra escaping."""
import json

import pytest

from rcon.commands import ServerCtl
from rcon.connection import Request


@pytest.mark.parametrize("message", [
    'A "quoted" message',
    r"C:\servers\folder\\name",
    'Français, 中文, emoji 🎮; "quotes" and \\ backslash',
    "line one\nline two\tend",
])
def test_message_and_ban_parameters_roundtrip(message):
    sent = []
    ctl = object.__new__(ServerCtl)

    def capture(name, version, content):
        _, body = Request(name, version, "test", content).to_bytes()
        sent.append((name, json.loads(json.loads(body)["contentBody"])))
        return True

    ctl.exchange_success = capture
    ctl.exchange = capture
    ctl.message_all_players(message)
    ctl.message_player('id"\\', message)
    ctl.temp_ban('id"\\', 2, reason=message, admin_name=message)
    ctl.add_vip('id"\\', message)
    ctl.set_broadcast(message)
    assert sent == [
        ("MessageAllPlayers", {"Message": message}),
        ("MessagePlayer", {"PlayerId": 'id"\\', "Message": message}),
        ("TemporaryBanPlayer", {"PlayerId": 'id"\\', "Duration": 2, "Reason": message, "AdminName": message}),
        ("AddVip", {"PlayerId": 'id"\\', "Comment": message}),
        ("ServerBroadcast", {"Message": message}),
    ]


def test_bulk_messages_also_keep_original_values():
    sent = []
    ctl = object.__new__(ServerCtl)

    def capture(name, version, content):
        _, body = Request(name, version, "test", content).to_bytes()
        sent.append(json.loads(json.loads(body)["contentBody"]))
        return len(sent)

    ctl.send = capture
    ctl.receive_success = lambda _: True
    assert ctl.bulk_message_players(['id"\\'], ['Bonjour "ami" \\']) is True
    assert sent == [{"PlayerId": 'id"\\', "Message": 'Bonjour "ami" \\'}]
