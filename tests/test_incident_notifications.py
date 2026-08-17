from unittest import TestCase
from unittest.mock import MagicMock

from rcon.incident_notifications import notify_incident_reporter


class IncidentReporterNotificationTests(TestCase):
    def test_status_message_is_sent_to_reporter_not_report_subject(self):
        rcon_api = MagicMock()
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
