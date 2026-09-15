import logging

from rcon.logs.loop import (
    on_connected,
    on_disconnected,
    on_match_end,
    on_match_start,
    on_team_switch,
)
from rcon.user_config.leadership_vote import LeadershipVoteUserConfig as Config
from rcon.utils import get_server_number

from .domain import event_time
from .storage import end_for_event

logger = logging.getLogger(__name__)


def end(log, player_id=None):
    try:
        if Config.load_from_db().enabled:
            end_for_event(int(get_server_number()), event_time(log), player_id)
    except Exception:
        logger.exception("Leadership lifecycle event failed")


@on_disconnected
@on_team_switch
def disconnected(rcon, log):
    if log.get("player_id_1"):
        end(log, str(log["player_id_1"]))


@on_connected()
def reconnected(rcon, log):
    # A new connection can never inherit a vote from the old connection, even
    # if the disconnect hook was interrupted. Older connection logs are ignored.
    if log.get("player_id_1"):
        end(log, str(log["player_id_1"]))


@on_match_start
@on_match_end
def round_changed(rcon, log):
    end(log)
