import logging

from rcon.logs.loop import on_connected
from rcon.moderation import ModerationSource
from rcon.moderation_candidates import enqueue_candidate

logger = logging.getLogger(__name__)


@on_connected()
def analyze_player_name_candidate(rcon, log):
    try:
        enqueue_candidate(
            source=ModerationSource.PLAYER_NAME,
            candidate_text=str(log.get("player_name_1") or ""),
            player_id=str(log.get("player_id_1") or "") or None,
            player_name=str(log.get("player_name_1") or "") or None,
        )
    except Exception:
        logger.exception("Unable to queue player-name moderation candidate")
