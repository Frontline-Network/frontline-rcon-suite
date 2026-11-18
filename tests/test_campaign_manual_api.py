"""HTTP contract for manual player-campaign delivery results."""
import json
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from tests.test_blacklist_sync_api_postgres import invoke
from api import views


@pytest.mark.parametrize("result,status,error", [
    (True, 200, None),
    (False, 400, "RCON rejected the player message"),
    (None, 400, "Message delivery could not be confirmed; it may have been delivered"),
    (TimeoutError("lost response"), 400, "Message delivery could not be confirmed; it may have been delivered"),
])
def test_manual_campaign_http_reflects_delivery(result, status, error):
    send = Mock()
    if isinstance(result, Exception):
        send.side_effect = result
    else:
        send.return_value = result
    draft = {"id": "synthetic", "time_sec": 900, "message": "hello",
             "delivery_mode": "player_message", "min_session_minutes": 5}
    with (patch.object(views.rcon_api, "get_player_ids", return_value=[("Alice", "synthetic")]),
          patch.object(views.rcon_api, "message_player", send),
          patch("rcon.campaign_delivery.format_message", return_value="hello"),
          patch("api.views.RconServerSettingsUserConfig.load_from_db", return_value=SimpleNamespace(broadcast_unbans=False)),
          patch("api.views.audit")):
        response = invoke("test_player_campaign", "POST", {"api.can_message_players"},
                          {"player_id": "synthetic", "campaign": draft})
    payload = json.loads(response.content)
    assert response.status_code == status
    assert payload["failed"] is (status != 200)
    assert payload["error"] == error
    send.assert_called_once()
