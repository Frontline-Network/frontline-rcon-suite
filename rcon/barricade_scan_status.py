"""Aggregate readiness for experimental Barricade scans; no identities."""
import os

from sqlalchemy import func, select

from rcon.barricade_scan_journal import BarricadeScanIntegration, get_session_maker
from rcon.barricade_scan_presence import observed_players
from rcon.cache_utils import get_redis_client
from rcon.player_presence import database_scope
from rcon.session_journal_observation import read as read_journal_observation


def scan_status(server_number: int) -> dict:
    """Report evidence availability, not a peer connection or delivery guarantee."""
    if type(server_number) is not int or not 1 <= server_number <= 32:
        raise ValueError('Invalid server number')
    if os.getenv('HLL_BARRICADE_DURABLE_SCANS') != '1':
        return {'state': 'disabled'}
    try:
        with get_session_maker()() as session:
            registered = session.scalar(select(func.count()).select_from(BarricadeScanIntegration).where(
                BarricadeScanIntegration.server_number == server_number))
        if not registered:
            return {'state': 'unregistered'}
        scope = database_scope(os.environ['HLL_DB_URL'])
        red = get_redis_client(global_pool=True)
        roster = observed_players(red, scope=scope, server_number=server_number)
        if roster is None:
            return {'state': 'waiting_roster'}
        observation = read_journal_observation(red, scope=scope, server_number=server_number)
        if observation is None:
            return {'state': 'waiting_logs'}
        if observation.pending or observation.unpublished_anonymous:
            return {'state': 'pending_logs'}
        return {'state': 'evidence_available'}
    except Exception:
        # Do not expose database/Redis URLs or exception details to the UI.
        return {'state': 'unavailable'}
