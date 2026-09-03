import unittest
from unittest.mock import Mock

from rcon.api_commands import RconAPI
from rcon.commands import HLLCommandFailedError


class FrontlineVipBrowserVerificationTests(unittest.TestCase):
    def make_api(self, platform, platform_account_id="123456789"):
        api = object.__new__(RconAPI)
        api.get_players = Mock(
            return_value=[{"name": "Mmm_Big_Guy", "player_id": "0" * 32}]
        )
        api.get_detailed_player_info = Mock(
            return_value={
                "name": "Mmm_Big_Guy",
                "player_id": "0" * 32,
                "platform": platform,
                "steam_id": platform_account_id,
            }
        )
        api.message_player = Mock(return_value=True)
        return api

    def test_delivers_code_and_returns_platform_identity(self):
        cases = {
            "EPlatformFamily::Steam": "steam",
            "EPlatformFamily::XboxSeries": "xbox",
            "EPlatformFamily::PS5": "playstation",
        }
        for raw_platform, expected_platform in cases.items():
            with self.subTest(raw_platform=raw_platform):
                api = self.make_api(raw_platform)
                result = api.send_frontline_vip_verification_code(
                    "mmm_big_guy", "ABCD-EFGH"
                )

                self.assertEqual(expected_platform, result["platform"])
                self.assertEqual("0" * 32, result["player_id"])
                self.assertEqual("123456789", result["platform_account_id"])
                api.message_player.assert_called_once()
                call = api.message_player.call_args.kwargs
                self.assertIn("ABCD-EFGH", call["message"])
                self.assertFalse(call["save_message"])

    def test_rejects_invalid_code_before_player_lookup(self):
        api = self.make_api("EPlatformFamily::PS5")
        with self.assertRaises(HLLCommandFailedError):
            api.send_frontline_vip_verification_code("Mmm_Big_Guy", "BAD")
        api.get_players.assert_not_called()

    def test_rejects_missing_or_ambiguous_online_name(self):
        for players in (
            [],
            [
                {"name": "SameName", "player_id": "0" * 32},
                {"name": "samename", "player_id": "1" * 32},
            ],
        ):
            with self.subTest(players=players):
                api = self.make_api("EPlatformFamily::XboxSeries")
                api.get_players.return_value = players
                with self.assertRaises(HLLCommandFailedError):
                    api.send_frontline_vip_verification_code("SameName", "ABCD-EFGH")
                api.message_player.assert_not_called()

    def test_rejects_identity_change_before_message_delivery(self):
        api = self.make_api("EPlatformFamily::Steam")
        api.get_detailed_player_info.return_value["player_id"] = "1" * 32
        with self.assertRaises(HLLCommandFailedError):
            api.send_frontline_vip_verification_code("Mmm_Big_Guy", "ABCD-EFGH")
        api.message_player.assert_not_called()


if __name__ == "__main__":
    unittest.main()
