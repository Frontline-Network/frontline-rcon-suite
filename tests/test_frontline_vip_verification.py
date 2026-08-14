import hashlib
import hmac
import json
import os
from unittest.mock import Mock, patch

os.environ.setdefault("SERVER_NUMBER", "1")
os.environ.setdefault("HLL_MAINTENANCE_CONTAINER", "1")

from rcon.frontline_vip_verification import (
    _allow_attempt,
    _attempts,
    _detect_platform,
    _signed_headers,
    handle_chat_verification,
)


def test_signed_headers_cover_exact_request_body():
    body = b'{"code":"ABCDEFGHJKLMNPQR"}'
    secret = "a" * 32

    with (
        patch("rcon.frontline_vip_verification.time.time", return_value=1234567890),
        patch(
            "rcon.frontline_vip_verification.secrets.token_hex",
            return_value="b" * 32,
        ),
    ):
        headers = _signed_headers(secret, body)

    expected = hmac.new(
        secret.encode(),
        b"1234567890\n" + (b"b" * 32) + b"\n" + body,
        hashlib.sha256,
    ).hexdigest()
    assert headers["X-FLN-Signature"] == expected


def test_platform_prefers_gameserver_profile():
    profile = {"soldier": {"platform": "EPlatformFamily::Xbox"}}
    assert _detect_platform("0002494aea2e418a9bb53cef8d225d77", profile) == "xbox"


def test_attempts_are_limited_per_gameserver_identity():
    _attempts.clear()
    with patch(
        "rcon.frontline_vip_verification.time.monotonic",
        side_effect=[0, 1, 2, 3, 4, 5, 601],
    ):
        assert all(_allow_attempt("player-1") for _ in range(5))
        assert _allow_attempt("player-1") is False
        assert _allow_attempt("player-1") is True


def test_invalid_command_is_answered_without_network_request():
    rcon = Mock()
    handled = handle_chat_verification(
        rcon,
        {
            "sub_content": "!vipverify too-short",
            "player_id_1": "0002494aea2e418a9bb53cef8d225d77",
            "player_name_1": "Biene",
        },
    )

    assert handled is True
    rcon.message_player.assert_called_once()


def test_valid_command_submits_verified_gameserver_identity():
    rcon = Mock()
    response = Mock(ok=True, content=b"{}")
    response.json.return_value = {"success": True, "message": "Verknüpft"}

    with (
        patch.dict(
            os.environ,
            {
                "FRONTLINE_VIP_REDEEM_URL": "https://fln.gg/wp-json/frontline-vip/v1/redeem",
                "FRONTLINE_VIP_REDEEM_SECRET": "s" * 32,
                "HLL_GAME": "hllv",
            },
            clear=False,
        ),
        patch(
            "rcon.frontline_vip_verification.get_player_profile",
            return_value={"soldier": {"platform": "EPlatformFamily::Steam"}},
        ),
        patch("rcon.frontline_vip_verification.get_server_number", return_value=4),
        patch(
            "rcon.frontline_vip_verification.requests.post", return_value=response
        ) as post,
        patch(
            "rcon.frontline_vip_verification._executor.submit",
            side_effect=lambda function, *args: function(*args),
        ),
        patch("rcon.frontline_vip_verification._allow_attempt", return_value=True),
    ):
        handled = handle_chat_verification(
            rcon,
            {
                "sub_content": "!vipverify ABCD-EFGH-JKLM-NPQR",
                "player_id_1": "0002494aea2e418a9bb53cef8d225d77",
                "player_name_1": "Biene",
            },
        )

    assert handled is True
    payload = json.loads(post.call_args.kwargs["data"])
    assert payload == {
        "code": "ABCDEFGHJKLMNPQR",
        "player_id": "0002494aea2e418a9bb53cef8d225d77",
        "player_name": "Biene",
        "platform": "steam",
        "game": "hll_vietnam",
        "server": "4",
    }
    assert rcon.message_player.call_count == 2
