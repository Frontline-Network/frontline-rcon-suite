"""Reconcile a VIP replacement file against both sources for one game server."""
import logging
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select

from rcon.models import PlayerID, PlayerName, PlayerVIP, enter_session
from rcon.utils import INDEFINITE_VIP_DATE, get_server_number
from rcon.vip_rewards.locking import lock
from rcon.vip_rewards.service import expiration

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class VipEntry:
    name: str
    expires: datetime | None
    listed: bool

    def matches(self, name, expires):
        return self.listed and self.name == name and self.expires == expires


def inventory(api):
    entries = {
        row["player_id"]: VipEntry(row["name"], row["vip_expiration"], True)
        for row in api.get_live_vip_ids()
    }
    alias = (select(PlayerName.name).where(PlayerName.player_id_id == PlayerID.id)
             .order_by(PlayerName.last_seen.desc().nulls_last(), PlayerName.id.desc())
             .limit(1).scalar_subquery())
    with enter_session() as session:
        rows = session.execute(
            select(PlayerID.player_id, PlayerVIP.expiration, alias)
            .join_from(PlayerVIP, PlayerID, PlayerVIP.player_id_id == PlayerID.id)
            .where(PlayerVIP.server_number == get_server_number())
        )
        for pid, expires, name in rows:
            if pid not in entries:
                entries[pid] = VipEntry(name or pid, expires, False)
    return entries


def replace_vips(api, name_ids):
    desired = {}
    seen = set()
    for name, pid, expires in name_ids:
        if not name or not pid or pid.casefold() in seen:
            raise ValueError("Missing name or missing or duplicate player ID")
        seen.add(pid.casefold())
        desired[pid] = (name, expiration(expires or INDEFINITE_VIP_DATE))
    if not desired:
        raise ValueError("Empty VIP replacement list")

    errors = []
    with lock(f"vip-import:{get_server_number()}"), api.without_retries():
        before = inventory(api)
        existing_ids = {pid.casefold(): pid for pid in before}
        if len(existing_ids) != len(before):
            raise ValueError("Ambiguous stored VIP identities")
        desired = {existing_ids.get(pid.casefold(), pid): target for pid, target in desired.items()}
        for pid, (name, expires) in desired.items():
            if pid in before and before[pid].matches(name, expires):
                continue
            try:
                if api.add_vip(pid, name, expires.isoformat()) is not True:
                    errors.append(f"VIP grant not confirmed: {pid}")
            except Exception:
                logger.exception("VIP import grant failed for %s", pid)
                errors.append(f"VIP grant outcome unknown: {pid}")

        # Require a confirmed replacement set before retiring any omitted rights.
        if errors:
            return errors
        current = inventory(api)
        for pid, target in desired.items():
            if pid not in current or not current[pid].matches(*target):
                errors.append(f"VIP grant could not be verified: {pid}")
        if errors:
            return errors

        for pid in before.keys() - desired.keys():
            try:
                if not api._revoke_stored_or_live_vip(pid, pid in current and current[pid].listed):
                    errors.append(f"VIP removal not confirmed: {pid}")
            except Exception:
                logger.exception("VIP import removal failed for %s", pid)
                errors.append(f"VIP removal outcome unknown: {pid}")

        final = inventory(api)
        for pid in final.keys() - desired.keys():
            errors.append(f"VIP remains after import: {pid}")
        for pid, target in desired.items():
            if pid not in final or not final[pid].matches(*target):
                errors.append(f"VIP differs after import: {pid}")
    return errors or ["ALL OK"]
