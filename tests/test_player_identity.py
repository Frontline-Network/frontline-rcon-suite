import os
from types import SimpleNamespace
from unittest.mock import MagicMock
from unittest.mock import patch

os.environ["HLL_MAINTENANCE_CONTAINER"] = "1"
os.environ["SERVER_NUMBER"] = "1"

from rcon.player_history import get_player_identity_links
from rcon.api_commands import RconAPI


def player(player_id, *, steam_id=None, name="Player", blacklists=None):
    return SimpleNamespace(
        player_id=player_id,
        steam_id=steam_id,
        account=SimpleNamespace(name=None),
        names=[SimpleNamespace(name=name)],
        soldier=SimpleNamespace(name=name),
        blacklists=blacklists or [],
    )


def session_returning(players):
    session = MagicMock()
    session.query.return_value.filter.return_value.options.return_value.all.return_value = (
        players
    )
    return session


def blacklist_record(*, active=True, servers=None, reason="Network ban"):
    record = MagicMock()
    record.to_dict.return_value = {
        "id": 7,
        "reason": reason,
        "is_active": active,
        "blacklist": {"name": "FLN blacklist", "servers": servers},
    }
    return record


def test_links_hllv_and_hll_by_authoritative_steam_id_not_name():
    steam_id = "76561198036685843"
    hll = player(steam_id, name="Completely different historical name")
    hllv = player("00026a3466a244829409f77af0a752d9", steam_id=steam_id, name="Biene")

    links = get_player_identity_links(session_returning([hll, hllv]), [hll, hllv])

    assert links[hllv.player_id]["linked_accounts"] == [
        {
            "player_id": steam_id,
            "steam_id": None,
            "name": "Completely different historical name",
            "game": "hll",
            "active_blacklists": [],
        }
    ]
    assert links[hll.player_id]["linked_accounts"][0]["player_id"] == hllv.player_id


def test_does_not_link_invalid_steam_identifier():
    hllv = player("0002-vietnam", steam_id="not-a-steam-id", name="Same name")
    unrelated = player("not-a-steam-id", name="Same name")

    links = get_player_identity_links(session_returning([hllv, unrelated]), [hllv])

    assert links[hllv.player_id]["linked_accounts"] == []


def test_does_not_publish_link_until_classic_hll_account_exists():
    steam_id = "76561198036685843"
    hllv = player("00026a3466a244829409f77af0a752d9", steam_id=steam_id)

    links = get_player_identity_links(session_returning([hllv]), [hllv])

    assert links[hllv.player_id]["linked_accounts"] == []


def test_reports_only_active_blacklists_applicable_to_this_server():
    steam_id = "76561198036685843"
    hll = player(
        steam_id,
        blacklists=[
            blacklist_record(reason="Active network ban"),
            blacklist_record(active=False, reason="Expired ban"),
            blacklist_record(servers=[2], reason="Other server"),
        ],
    )
    hllv = player("00026a3466a244829409f77af0a752d9", steam_id=steam_id)

    links = get_player_identity_links(session_returning([hll, hllv]), [hllv])

    assert [
        record["reason"]
        for record in links[hllv.player_id]["linked_accounts"][0][
            "active_blacklists"
        ]
    ] == ["Active network ban"]


def test_profile_api_marks_current_game_server_ban_on_linked_account():
    raw_profile = {
        "player_id": "00026a3466a244829409f77af0a752d9",
        "identity": {
            "linked_accounts": [
                {
                    "player_id": "76561198036685843",
                    "name": "Biene",
                    "game": "hll",
                    "active_blacklists": [],
                }
            ]
        },
    }
    api = RconAPI.__new__(RconAPI)
    api.get_ban = MagicMock(
        side_effect=lambda player_id: (
            [{"player_id": player_id, "type": "perma"}]
            if player_id == "76561198036685843"
            else []
        )
    )

    with patch("rcon.api_commands.player_history.get_player_profile", return_value=raw_profile), patch(
        "rcon.api_commands.player_history.get_player_comments", return_value=[]
    ):
        profile = api.get_player_profile(raw_profile["player_id"])

    linked = profile["identity"]["linked_accounts"][0]
    assert linked["is_banned"] is True
    assert linked["bans"][0]["type"] == "perma"
