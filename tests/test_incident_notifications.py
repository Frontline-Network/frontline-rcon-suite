from unittest import TestCase
from unittest.mock import MagicMock

from rcon.incident_notifications import notify_incident_reporter


class IncidentReporterNotificationTests(TestCase):
    def test_status_message_is_sent_to_reporter_not_report_subject(self):
        rcon_api = MagicMock()
        rcon_api.message_player.return_value = True
        incident = {
            "reporter_id": "reporter-player-id",
            "reporter_name": "Reporter",
            "target_id": "reported-player-id",
            "target_name": "Reported player",
        }

        self.assertTrue(
            notify_incident_reporter(
                rcon_api,
                incident,
                message="Your report is being handled.",
                by="discord:moderator",
                save_message=True,
            )
        )
        rcon_api.message_player.assert_called_once_with(
            player_id="reporter-player-id",
            message="Your report is being handled.",
            player_name="Reporter",
            by="discord:moderator",
            save_message=True,
        )

    def test_status_message_without_reporter_is_not_sent_to_subject(self):
        rcon_api = MagicMock()

        self.assertFalse(
            notify_incident_reporter(
                rcon_api,
                {
                    "target_id": "reported-player-id",
                    "target_name": "Reported player",
                },
                message="Your report is being handled.",
            )
        )
        rcon_api.message_player.assert_not_called()

    def test_rejected_and_unknown_results_do_not_claim_delivery_or_retry(self):
        for result in (False, None):
            with self.subTest(result=result):
                rcon_api = MagicMock()
                rcon_api.message_player.return_value = result
                outcome = notify_incident_reporter(
                    rcon_api, {"reporter_id": "synthetic"}, message="test"
                )
                self.assertIs(outcome, result)
                rcon_api.message_player.assert_called_once()

    def test_timeout_propagates_without_retry(self):
        rcon_api = MagicMock()
        rcon_api.message_player.side_effect = TimeoutError('response lost')
        with self.assertRaises(TimeoutError):
            notify_incident_reporter(rcon_api, {"reporter_id": "synthetic"}, message="test")
        rcon_api.message_player.assert_called_once()
