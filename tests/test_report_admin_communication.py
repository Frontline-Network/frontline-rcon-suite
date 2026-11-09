"""Player-name communication reports; synthetic roster/DB and fake RCON only."""

import pytest

from tests.test_report_admin import (
    current,
    db,
    report,
    rules,
    service,
    setup,
    transport,
)

PLAYER_REPORTS = [
    ("CARTMARC", "!admin CARTMARC SL no VOIP"),
    ("RAMBO II", "!admin RAMBO II SL no VOIP"),
    ("RAMBO II", "!admin ramboii no com and no spawn points lacated"),
    (
        "NONBOKS",
        "!admin NONBOKS ist Squadleader und kommuniziert nicht "
        "(ist schon wieder auf dem Server)",
    ),
    ("NONBOKS", "!admin NONBOKS ist Squadleader und kommuniziert nicht"),
]


@pytest.mark.parametrize("name,message", PLAYER_REPORTS)
def test_player_name_communication_report(setup, name, message):
    database, players, _ = setup
    players[0]["name"] = name
    incident = report(setup, message)
    assert rules.classify(message, players) == "communication"
    assert incident["report_admin"]["status"] == "queued"
    api = transport()
    service.tick(api, 1)
    service.tick(api, 1)
    api.kick.assert_called_once()
    assert api.kick.call_args.args[0] == "target"
    assert current(database, incident["id"])["report_admin"]["status"] == "kicked"
