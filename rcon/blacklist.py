import logging
import os
import struct
import threading
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from enum import IntEnum, auto
from typing import Literal, Sequence, overload

import orjson
import redis
from pydantic import BaseModel, field_validator
from pydantic.dataclasses import dataclass
from sqlalchemy import and_, func, literal, or_, select
from sqlalchemy.orm import Session, selectinload

from rcon.barricade import (
    ScanPlayersRequestPayload,
    ServerRequestType,
    barricade_game_for_server,
    send_to_barricade,
)
from rcon.barricade_hllv_identity import (prepare_online_identity_snapshot,
                                          prepare_online_steam_identity, verified_steam_id)
from rcon.cache_utils import get_redis_client
from rcon.automods import action_guard
from rcon.commands import HLLCommandFailedError
from rcon.discord import dict_to_discord, send_to_discord_audit
from rcon.models import (
    Blacklist,
    BlacklistRecord,
    BlacklistSyncMethod,
    PlayerID,
    PlayerName,
    enter_session,
    get_session_maker,
)
from rcon.player_history import (
    _get_set_player,
    safe_save_player_action,
    unaccent,
)
from rcon.rcon import Rcon, get_rcon
from rcon.steam_utils import is_steam_id_64
from rcon.types import (
    BlacklistRecordType,
    BlacklistRecordWithBlacklistType,
    BlacklistType,
    GameEnum,
    PlayerActionState,
)
from rcon.utils import MISSING, get_server_number
from rcon.vip_rewards.locking import lock

logger = logging.getLogger(__name__)
red = get_redis_client()

SERVER_NUMBER = int(get_server_number())
BLACKLIST_ACTION_GUARD_RULE = "BlacklistEnforcement"


class HLLVSteamBanOwnershipUnverified(RuntimeError):
    """An existing EOS game ban cannot safely be attributed to this record."""


class HLLVBanOwnershipUnverified(RuntimeError):
    """An existing HLLV game ban cannot safely be attributed to this list."""


class HLLVSteamIdentityUnverified(RuntimeError):
    """An action was not attempted because its Steam/EOS link is unverified."""


def _is_hllv_steam_id(rcon, player_id):
    return (getattr(getattr(rcon, 'game_profile', None), 'game', None) == GameEnum.HLL_VIETNAM
            and isinstance(player_id, str) and is_steam_id_64(player_id))


@contextmanager
def blacklist_change_session():
    """A mutation must fail if either its database change or journal fails."""
    with get_session_maker()() as session:
        yield session


def commit_blacklist_change(session: Session, command):
    """Commit a mutation and all target deliveries as one transaction."""
    from rcon.blacklist_sync_journal import enqueue

    enqueue(session, command.encode(), command.server_mask)
    session.commit()


def normalize_blacklist_expiry(value: datetime | None) -> datetime | None:
    """Legacy callers pass naive UTC timestamps; store a consistent instant."""
    if value is None:
        return None
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def update_penalty_count(
    player_id: str,
    player_names: list[str],
    action: PlayerActionState,
    admin_name: str = "",
):
    """Save the action when blacklist records are added/edited for penalty count calculation"""
    try:
        player_name = player_names[0]
    except IndexError:
        player_name = ""

    try:
        safe_save_player_action(
            action_type=action,
            player_id=player_id,
            player_name=player_name,
            by=admin_name,
        )
    except Exception as e:
        # Don't let errors prevent adding/editing blacklist records
        logger.error(f"Unable to save player {action=} while adding blacklist record")
        logger.exception(e)


def get_server_number_mask():
    server_number = SERVER_NUMBER
    return 1 << (server_number - 1)


def get_blacklists(sess: Session):
    return sess.scalars(select(Blacklist).order_by(Blacklist.id)).all()


@overload
def get_blacklist(
    sess: Session, blacklist_id: int, strict: Literal[True]
) -> Blacklist: ...
@overload
def get_blacklist(
    sess: Session, blacklist_id: int, strict: Literal[False]
) -> Blacklist | None: ...
@overload
def get_blacklist(
    sess: Session, blacklist_id: int, strict: bool = False
) -> Blacklist | None: ...


def get_blacklist(
    sess: Session, blacklist_id: int, strict: bool = False
) -> Blacklist | None:
    blacklist = sess.get(Blacklist, blacklist_id)
    if not blacklist and strict:
        raise HLLCommandFailedError("No blacklist found with ID %s" % blacklist_id)
    return blacklist


@overload
def get_record(
    sess: Session, record_id: int, strict: Literal[True]
) -> BlacklistRecord: ...
@overload
def get_record(
    sess: Session, record_id: int, strict: Literal[False]
) -> BlacklistRecord | None: ...
@overload
def get_record(
    sess: Session, record_id: int, strict: bool = False
) -> BlacklistRecord | None: ...


def get_record(sess: Session, record_id: int, strict: bool = False):
    record = sess.get(BlacklistRecord, record_id)
    if not record and strict:
        raise HLLCommandFailedError("No record found with ID %s" % record_id)
    return record


def get_active_blacklist_records(sess: Session, blacklist_id: int):
    stmt = select(BlacklistRecord).filter(
        # Record must not have expired yet
        BlacklistRecord.blacklist_id == blacklist_id,
        or_(
            BlacklistRecord.expires_at.is_(None),
            BlacklistRecord.expires_at > func.now(),
        ),
    )
    return sess.scalars(stmt)


def get_player_blacklist_records(
    sess: Session,
    player_id: str,
    include_expired=True,
    include_other_servers=True,
    exclude: set[int] = None,
) -> list[BlacklistRecord]:
    stmt = (
        select(BlacklistRecord)
        .join(BlacklistRecord.player)
        .join(BlacklistRecord.blacklist)
        .filter(
            # Record must target the given player
            PlayerID.player_id
            == player_id,
        )
    )

    if not include_expired:
        stmt = stmt.filter(
            # Record must not have expired yet
            or_(
                BlacklistRecord.expires_at.is_(None),
                BlacklistRecord.expires_at > func.now(),
            )
        )

    if not include_other_servers:
        stmt = stmt.filter(
            # Blacklist must be enabled on the given server
            or_(
                Blacklist.servers.is_(None),
                Blacklist.servers.bitwise_and(get_server_number_mask()) != 0,
            )
        )

    if exclude:
        stmt = stmt.filter(BlacklistRecord.id.not_in(exclude))

    records = sess.scalars(stmt).all()
    return records


def search_blacklist_records(
    sess: Session,
    player_id: str = None,
    reason: str = None,
    blacklist_id: int = None,
    exclude_expired: bool = False,
    expired_only: bool = False,
    page_size: int = 50,
    page: int = 1,
) -> tuple[list[BlacklistRecord], int]:
    if page <= 0:
        raise ValueError("page needs to be >= 1")
    if page_size <= 0:
        raise ValueError("page_size needs to be >= 1")

    filters = []

    if player_id:
        filters.append(PlayerID.player_id == player_id)
    if reason:
        clean_reason = unaccent(literal(reason))
        pattern = literal("%") + clean_reason + literal("%")
        filters.append(
            and_(clean_reason != "", or_(
                unaccent(BlacklistRecord.reason).ilike(pattern),
                PlayerID.names.any(
                    unaccent(PlayerName.name).ilike(pattern)
                ),
            ))
        )
    if blacklist_id is not None:
        filters.append(BlacklistRecord.blacklist_id == blacklist_id)
    if expired_only:
        filters.extend(
            [
                BlacklistRecord.expires_at.is_not(None),
                BlacklistRecord.expires_at <= func.now(),
            ]
        )
    elif exclude_expired:
        filters.append(
            or_(
                BlacklistRecord.expires_at.is_(None),
                BlacklistRecord.expires_at > func.now(),
            )
        )

    total = sess.execute(
        select(func.count(BlacklistRecord.id))
        .join(BlacklistRecord.player)
        .filter(*filters)
    ).scalar_one()

    stmt = (
        select(BlacklistRecord)
        .join(BlacklistRecord.player)
        .filter(*filters)
        .order_by(BlacklistRecord.created_at.desc(), BlacklistRecord.id.desc())
        .limit(page_size)
        .offset((page - 1) * page_size)
        .options(selectinload(BlacklistRecord.blacklist))
        .options(selectinload(BlacklistRecord.player).selectinload(PlayerID.names))
        .options(selectinload(BlacklistRecord.player).selectinload(PlayerID.steaminfo))
    )
    return sess.scalars(stmt).all(), total


def is_player_blacklisted(
    sess: Session, player_id: str, exclude: set[int] = {}
) -> BlacklistRecord | None:
    """Determine whether a player is blacklisted, and return
    the blacklist record with the highest priority.

    Parameters
    ----------
    player_id : str
        The player's Steam64ID or Windows UUID
    exclude : set[int]
        An optional set of record IDs to exclude

    Returns
    -------
    BlacklistRecord | None
        The blacklist record with highest priority if the
        player has unexpired records. Returns `None` if no
        such record exists.
    """
    records = get_player_blacklist_records(
        sess,
        player_id,
        include_expired=False,
        include_other_servers=False,
        exclude=exclude,
    )

    if not records:
        return

    return get_highest_priority_record(records)


def is_higher_priority_record(record: BlacklistRecord, other: BlacklistRecord):
    return _is_higher_priority_record(
        record.created_at,
        record.expires_at,
        other.created_at,
        other.expires_at,
    )


def _is_higher_priority_record(
    record_created_at: datetime,
    record_expires_at: datetime | None,
    other_created_at: datetime,
    other_expires_at: datetime | None,
):
    # If both records expire at the same time, select the record
    # that was created most recently
    if record_expires_at == other_expires_at:
        return record_created_at > other_created_at

    # After having asserted that their expiration dates differ, if
    # either record has no expiration date, it must have the highest
    # priority
    elif record_expires_at is None:
        return True
    elif other_expires_at is None:
        return False

    # Otherwise, both have an expiration date. Select the record that
    # takes the longest to expire.
    return record_expires_at > other_expires_at


def get_highest_priority_record(records: Sequence[BlacklistRecord]):
    if not records:
        return None

    # Find record with highest priority
    highest = records[0]
    for record in records[1:]:
        if is_higher_priority_record(record, highest):
            highest = record
    return highest


def round_timedelta_to_hours(td: timedelta | datetime):
    if isinstance(td, datetime):
        td = normalize_blacklist_expiry(td) - datetime.now(tz=timezone.utc)
    return max(round(td.total_seconds() / (60 * 60)), 1)


def _blacklist_record_has_expired(record: BlacklistRecord) -> bool:
    expires_at = normalize_blacklist_expiry(getattr(record, "expires_at", None))
    return expires_at is not None and expires_at <= datetime.now(tz=timezone.utc)


_BLACKLIST_ACTION_EXPIRED = object()
_BLACKLIST_ACTION_DEFERRED = object()
_BLACKLIST_ACTION_CHANGED = object()


class BanState(IntEnum):
    NONE = 0
    TEMP = 1
    PERMA = 2


def get_ban_state_from_record(record: BlacklistRecord | BlacklistRecordType | None):
    if record is None:
        return BanState.NONE

    if isinstance(record, BlacklistRecord):
        sync = record.blacklist.sync
        expires_at = record.expires_at
        # is_other_servers = record.blacklist and SERVER_NUMBER not in record.blacklist.get_server_numbers()
        # is_expired = record.is_expired()
    else:
        sync = record["blacklist"]["sync"]
        expires_at = record["expires_at"]
        # is_other_servers = record["blacklist"] and SERVER_NUMBER not in record["blacklist"]["servers"]
        # is_expired = expires_at and expires_at < datetime.now(tz=timezone.utc)

    # if is_other_servers or is_expired:
    #     return BanState.NONE

    if sync == BlacklistSyncMethod.KICK_ONLY:
        return BanState.NONE
    elif expires_at is None:
        return BanState.PERMA
    else:
        return BanState.TEMP


def _require_blacklist_action_review_clear(player_id: str):
    pending = action_guard.pending_players(SERVER_NUMBER, BLACKLIST_ACTION_GUARD_RULE)
    if '*' in pending or player_id in pending:
        raise RuntimeError("Previous blacklist action awaits review")


def synchronize_ban(
    rcon: Rcon, player_id: str, new_record: BlacklistRecord | None, old_state: BanState
):
    with lock(f"blacklist-sync:{SERVER_NUMBER}"):
        _require_blacklist_action_review_clear(player_id)
        return _synchronize_ban(rcon, player_id, new_record, old_state)


def _synchronize_ban(
    rcon: Rcon, player_id: str, new_record: BlacklistRecord | None, old_state: BanState
):
    """Update a ban associated with a blacklist record.

    Be aware that this method does not verify whether the record has expired
    and/or does not affect the player on the current server.

    Parameters
    ----------
    rcon : Rcon
        A RCON client
    player_id : str
        The Steam64ID or Windows Store UUID of the player
    new_record : BlacklistRecord | None
        The updated blacklist record, or None if the record was removed
    old_state : BanState
        The current (and possibly outdated) state of the player's ban
    """
    logger.info("Synchronizing ban for player %s", player_id)
    new_state = get_ban_state_from_record(new_record)
    short_record = new_state == BanState.TEMP and _blacklist_remaining_hours(new_record) < 1

    # Remove the existing ban if it will not be overwritten later. Also remove if the
    # player is to be banned upon connecting, so that they can see the updated ban reason
    if not short_record and (
        new_state != old_state
        or (new_record is not None and new_record.blacklist.sync == BlacklistSyncMethod.BAN_ON_CONNECT)
    ):
        try:
            if old_state == BanState.TEMP:
                if rcon.remove_temp_ban(player_id) is not True:
                    raise RuntimeError("Game server did not confirm temporary ban removal")
            elif old_state == BanState.PERMA:
                if rcon.remove_perma_ban(player_id) is not True:
                    raise RuntimeError("Game server did not confirm permanent ban removal")
        except HLLCommandFailedError as exc:
            raise RuntimeError("Could not confirm blacklist ban removal") from exc

    # If there is no new record we are done and can return
    if new_record is None:
        return

    # Check whether the player is online (and grab their name)
    try:
        player_info = rcon.get_detailed_player_info(player_id=player_id)
    except HLLCommandFailedError:
        player_name = None
        is_online = False
    else:
        player_name = player_info["name"]
        is_online = True

    if (
        new_record.blacklist.sync != BlacklistSyncMethod.BAN_IMMEDIATELY
        and not is_online
    ):
        # We only kick or ban the player once they come online, so
        # we don't need to do anything as of now.
        return

    result = apply_blacklist_punishment(
        rcon, new_record, player_id=player_id, player_name=player_name, is_online=is_online
    )
    if result is not True and result is not _BLACKLIST_ACTION_EXPIRED and result is not _BLACKLIST_ACTION_DEFERRED:
        raise RuntimeError("Could not confirm blacklist action")


def apply_blacklist_punishment(
    rcon: Rcon,
    record: BlacklistRecord,
    player_id: str = None,
    player_name: str = None,
    is_online: bool = True,
):
    if player_id is None:
        player_id = record.player.player_id
    with lock(f"blacklist-sync:{SERVER_NUMBER}"):
        if _blacklist_record_has_expired(record):
            logger.info("Skipping blacklist action: record has expired")
            return _BLACKLIST_ACTION_EXPIRED
        for _ in range(3):
            if _blacklist_record_has_expired(record):
                return _BLACKLIST_ACTION_EXPIRED
            state = get_ban_state_from_record(record)
            guard_action = "kick" if state == BanState.NONE else "ban"
            if state == BanState.TEMP and _blacklist_remaining_hours(record) < 1:
                guard_action = "kick"
            if guard_action == "kick" and not is_online:
                return _BLACKLIST_ACTION_DEFERRED
            try:
                token = action_guard.reserve(SERVER_NUMBER, player_id, [BLACKLIST_ACTION_GUARD_RULE], guard_action)
            except Exception:
                logger.exception("Blacklist action not sent: durable reservation unavailable")
                return False
            if token is None:
                logger.warning("Blacklist action not sent: previous result awaits review")
                return False
            try:
                result = _apply_blacklist_punishment(rcon, record, player_id=player_id, player_name=player_name,
                                                    expected_action=guard_action)
            except Exception:
                logger.exception("Blacklist action result uncertain; reservation retained")
                return False
            if result is True or result is False or result is _BLACKLIST_ACTION_EXPIRED or result is _BLACKLIST_ACTION_CHANGED:
                try:
                    action_guard.finish(SERVER_NUMBER, player_id, token,
                                        "confirmed" if result is True else "rejected", expected=1)
                except Exception:
                    logger.exception("Could not finalize blacklist action; reservation retained")
                    return result is True
            if result is _BLACKLIST_ACTION_CHANGED:
                continue
            return result if result is _BLACKLIST_ACTION_EXPIRED else result is True
        return False


def _blacklist_remaining_hours(record):
    expiry = normalize_blacklist_expiry(record.expires_at)
    return int((expiry - datetime.now(tz=timezone.utc)).total_seconds() // 3600)


def _apply_blacklist_punishment(
    rcon: Rcon,
    record: BlacklistRecord,
    player_id: str = None,
    player_name: str = None,
    expected_action: str = None,
):
    logger.info("Applying punishment to %s", player_id)
    try:
        # A record can expire after it was selected or while the action guard
        # was being reserved. Never turn that stale record into a new kick or
        # the minimum one-hour server ban.
        if _blacklist_record_has_expired(record):
            logger.info("Skipping blacklist action: record has expired")
            return _BLACKLIST_ACTION_EXPIRED
        state = get_ban_state_from_record(record)
        reason = record.get_formatted_reason()

        if player_id is None:
            player_id = record.player.player_id
        if player_name is None:
            names = record.player.names
            player_name = names[0].name if names else player_id

        if _blacklist_record_has_expired(record):
            logger.info("Skipping blacklist action: record has expired")
            return _BLACKLIST_ACTION_EXPIRED

        hours = _blacklist_remaining_hours(record) if state == BanState.TEMP else None
        actual_action = "kick" if state == BanState.NONE or (state == BanState.TEMP and hours < 1) else "ban"
        if expected_action is not None and actual_action != expected_action:
            return _BLACKLIST_ACTION_CHANGED
        if state == BanState.TEMP and hours < 1:
            state = BanState.NONE
        # Apply any bans/kicks
        match state:
            case BanState.NONE:
                logger.info(
                    "Attempting to kick player %s due to blacklist, reason: %s",
                    player_name,
                    reason,
                )
                accepted = rcon.kick(
                    player_name=player_name,
                    reason=reason,
                    by=f"BLACKLIST: {record.admin_name}",
                    player_id=player_id,
                )

            case BanState.TEMP:
                logger.info(
                    "Attempting to ban player %s for %s hour(s) due to blacklist "
                    "(blacklist expires at %s), reason: %s",
                    player_name,
                    hours,
                    record.expires_at,
                    reason,
                )
                accepted = rcon.temp_ban(
                    player_id=player_id,
                    duration_hours=hours,
                    reason=reason,
                    by=f"BLACKLIST: {record.admin_name}",
                )

            case BanState.PERMA:
                logger.info(
                    "Attempting to ban player %s due to blacklist, reason: %s",
                    player_name,
                    reason,
                )
                accepted = rcon.perma_ban(
                    player_id=player_id,
                    reason=reason,
                    by=f"BLACKLIST: {record.admin_name}",
                )

        if accepted is not True:
            logger.warning("Blacklist action was not confirmed")
            try:
                send_to_discord_audit(
                    message="Failed to confirm blacklist action; please check the logs",
                    command_name="blacklist", by="ERROR",
                )
            except Exception:
                logger.exception("Unable to send blacklist error to audit log")
            return False if accepted is False else None

    except Exception:
        logger.exception("Failed to apply blacklist")
        try:
            send_to_discord_audit(
                message="Failed to apply blacklist, please check the logs and report the error",
                command_name="blacklist",
                by="ERROR",
            )
        except:
            logger.error("Unable to send blacklist error to audit log")
        return None

    else:
        try:
            send_to_discord_audit(
                message=f"{dict_to_discord(dict(player=player_name, reason=reason))}",
                command_name="blacklist",
                by="BLACKLIST",
            )
        except:
            logger.error("Unable to send blacklist to audit log")
        return True


def add_record_to_blacklist(
    player_id: str,
    blacklist_id: int,
    reason: str,
    expires_at: datetime | None = None,
    admin_name: str = "",
):
    with blacklist_change_session() as sess:
        player = _get_set_player(sess, player_id)
        player_names = [n.name for n in player.names]
        if not player:
            raise RuntimeError(
                "Unable to create player Steam ID, check the DB connection"
            )

        blacklist = get_blacklist(sess, blacklist_id, True)

        record = BlacklistRecord(
            player=player,
            blacklist=blacklist,
            reason=reason,
            expires_at=normalize_blacklist_expiry(expires_at),
            admin_name=admin_name,
        )
        sess.add(record)
        sess.flush()

        res = record.to_dict()

        commit_blacklist_change(sess,
            BlacklistCommand(
                command=BlacklistCommandType.CREATE_RECORD,
                server_mask=blacklist.servers,
                payload=BlacklistCreateRecordCommand(
                    player_id=player_id,
                    record_id=record.id,
                ).model_dump(),
            )
        )

    if expires_at:
        action = PlayerActionState.TEMPBAN
    else:
        action = PlayerActionState.PERMABAN

    update_penalty_count(
        player_id=player_id,
        player_names=player_names,
        action=action,
        admin_name=admin_name,
    )

    return res


def edit_record_from_blacklist(
    record_id: int,
    blacklist_id: int = MISSING,
    reason: str = MISSING,
    expires_at: datetime | None = MISSING,
):
    with blacklist_change_session() as sess:
        record = get_record(sess, record_id, True)
        player_names = [n.name for n in record.player.names]

        # Save old state
        old_record = record.to_dict()
        old_server_mask = record.blacklist.servers

        # Update attributes
        if blacklist_id != MISSING:
            record.blacklist_id = blacklist_id
        if reason != MISSING:
            record.reason = reason
        if expires_at != MISSING:
            record.expires_at = normalize_blacklist_expiry(expires_at)

        # Return if nothing was modified
        if not sess.is_modified(record):
            return old_record

        sess.flush()
        if blacklist_id != MISSING:
            sess.expire(record, ["blacklist"])
        new_record = record.to_dict()

        # Check whether there were any changes made which would require resyncing a ban
        if (
            old_record["blacklist"]["id"] != new_record["blacklist"]["id"]
            or old_record["blacklist"]["sync"] != new_record["blacklist"]["sync"]
            or old_record["expires_at"] != new_record["expires_at"]
            or old_record["reason"] != new_record["reason"]
        ):
            # Merge old and new mask
            if old_server_mask is None or record.blacklist.servers is None:
                server_mask = (2**32) - 1
            else:
                server_mask = old_server_mask | record.blacklist.servers

            # Send edit command to both old and new servers
            commit_blacklist_change(sess,
                BlacklistCommand(
                    command=BlacklistCommandType.EDIT_RECORD,
                    server_mask=server_mask,
                    payload=BlacklistEditRecordCommand(
                        old_record=old_record
                    ).model_dump(),
                )
            )
        else:
            sess.commit()

        current_time = datetime.now(tz=timezone.utc)
        # temp ban -> perma ban
        if old_record["expires_at"] and not new_record["expires_at"]:
            update_penalty_count(
                player_id=record.player.player_id,
                player_names=player_names,
                action=PlayerActionState.PERMABAN,
                admin_name=new_record["admin_name"],
            )
        # perma ban -> temp ban that isn't already expired
        elif (
            not old_record["expires_at"]
            and new_record["expires_at"]
            and new_record["expires_at"] > current_time
        ):
            update_penalty_count(
                player_id=record.player.player_id,
                player_names=player_names,
                action=PlayerActionState.TEMPBAN,
                admin_name=new_record["admin_name"],
            )
        # temp ban -> different duration temp ban that isn't already expired
        elif (
            old_record["expires_at"]
            and new_record["expires_at"]
            and new_record["expires_at"] > current_time
        ):
            update_penalty_count(
                player_id=record.player.player_id,
                player_names=player_names,
                action=PlayerActionState.TEMPBAN,
                admin_name=new_record["admin_name"],
            )

        return new_record


def remove_record_from_blacklist(record_id: int, *, expected_blacklist_id: int | None = None):
    with blacklist_change_session() as sess:
        # Lock while checking the requested list and deleting so a concurrent
        # move to another list cannot turn an authorized removal into a
        # deletion from that other list.
        record = sess.get(BlacklistRecord, record_id, with_for_update=True)
        if not record or (expected_blacklist_id is not None
                          and record.blacklist_id != expected_blacklist_id):
            return False

        res = record.to_dict()

        needs_sync = not record.is_expired()
        server_mask = record.blacklist.servers
        sess.delete(record)

        if needs_sync:
            commit_blacklist_change(sess,
                BlacklistCommand(
                    command=BlacklistCommandType.DELETE_RECORD,
                    server_mask=server_mask,
                    payload=BlacklistDeleteRecordCommand(
                        old_record=res,
                    ).model_dump(),
                )
            )
        else:
            sess.commit()

    return True


def create_blacklist(
    name: str, sync: BlacklistSyncMethod, servers: Sequence[int] | None
):
    with enter_session() as sess:
        blacklist = Blacklist(
            name=name,
            sync=sync,
            servers=0,
        )
        blacklist.set_server_numbers(servers)
        sess.add(blacklist)
        sess.commit()
        return blacklist.to_dict()


def edit_blacklist(
    blacklist_id: int,
    name: str = MISSING,
    sync: BlacklistSyncMethod = MISSING,
    servers: Sequence[int] | None = MISSING,
):
    with blacklist_change_session() as sess:
        blacklist = get_blacklist(sess, blacklist_id, True)
        # Save old state
        old_blacklist = blacklist.to_dict()
        old_server_mask = blacklist.servers

        # Update attributes
        if name != MISSING:
            blacklist.name = name
        if sync != MISSING:
            blacklist.sync = sync
        if servers != MISSING:
            blacklist.set_server_numbers(servers)

        # Return if nothing was modified
        if not sess.is_modified(blacklist):
            return old_blacklist

        sess.flush()
        new_blacklist = blacklist.to_dict()

        # Merge old and new mask
        if old_server_mask is None or blacklist.servers is None:
            server_mask = (2**32) - 1
        else:
            server_mask = old_server_mask | blacklist.servers

        # Send edit command to both old and new servers
        commit_blacklist_change(sess,
            BlacklistCommand(
                command=BlacklistCommandType.EDIT_LIST,
                server_mask=server_mask,
                payload=BlacklistEditListCommand(
                    old_blacklist=old_blacklist, new_blacklist=new_blacklist
                ).model_dump(),
            )
        )

        return new_blacklist


def delete_blacklist(blacklist_id: int):
    if blacklist_id == 0:
        raise ValueError("The default blacklist cannot be deleted")

    with blacklist_change_session() as sess:
        blacklist = get_blacklist(sess, blacklist_id)
        if not blacklist:
            return False

        res = blacklist.to_dict()

        # Since we're about to delete all records we need to
        # first capture all details needed to determine whether
        # the report had priority or not.
        records = get_active_blacklist_records(sess, blacklist_id)
        if not records:
            # If there's no active records on this blacklist we do not need to
            # worry about ban syncing and can just delete straight away.
            sess.delete(blacklist)
            sess.commit()
            return True

        # Iterate over all records and extract all necessary details
        # Format is {player_id: (r.created_at, r.expired_at)}
        banned_players: dict[str, tuple[datetime, datetime | None]] = {}
        for record in records:
            player_id = record.player.player_id

            # Players can be on the same blacklist multiple times. Here we check
            # whether we have already seen a record of that player and if it has
            # a lower priority, replace it.
            if other := banned_players.get(player_id):
                if not _is_higher_priority_record(
                    record.created_at, record.expires_at, *other
                ):
                    continue

            banned_players[player_id] = (record.created_at, record.expires_at)

        server_mask = blacklist.servers
        sess.delete(blacklist)

        commit_blacklist_change(sess,
            BlacklistCommand(
                command=BlacklistCommandType.DELETE_LIST,
                server_mask=server_mask,
                payload=BlacklistDeleteListCommand(
                    blacklist=res,
                    banned_players=banned_players,
                ).model_dump(),
            )
        )

        return True


def blacklist_or_ban(
    rcon: Rcon,
    blacklist_id: int | None,
    player_id: str,
    reason: str,
    expires_at: datetime | None = None,
    admin_name: str = "",
):
    # First try blacklisting the player if a blacklist_id is provided
    if blacklist_id is not None:
        try:
            # Note the "return"
            return add_record_to_blacklist(
                player_id=player_id,
                blacklist_id=blacklist_id,
                reason=reason,
                expires_at=expires_at,
                admin_name=admin_name,
            )
        except Exception:
            # A database commit may have succeeded despite a lost response.
            # Falling back to an immediate game ban could duplicate the
            # durable action that will be processed after recovery.
            logger.exception("Could not confirm blacklist update; no fallback ban attempted")
            raise

    if expires_at:
        expires_at = normalize_blacklist_expiry(expires_at)
        remaining = expires_at - datetime.now(tz=timezone.utc)
        if remaining.total_seconds() <= 0:
            logger.info("Skipping direct temporary ban: expiry has already passed")
            return False
        return rcon.temp_ban(
            player_id=player_id,
            reason=reason,
            duration_hours=round_timedelta_to_hours(remaining),
            by=admin_name,
        )
    else:
        return rcon.perma_ban(player_id=player_id, reason=reason, by=admin_name)


def expire_all_player_blacklists(player_id: str):
    with blacklist_change_session() as sess:
        records = get_player_blacklist_records(
            sess,
            player_id=player_id,
            include_expired=False,
        )

        kick_only_mask = 0
        ban_mask = 0
        if records:
            expire_time = datetime.now(tz=timezone.utc)
            server_mask = 0

            for record in records:
                record.expires_at = expire_time
                servers = record.blacklist.servers
                if servers is None:
                    servers = 2**32 - 1
                server_mask |= servers
                if record.blacklist.sync == BlacklistSyncMethod.KICK_ONLY:
                    kick_only_mask |= servers
                else:
                    ban_mask |= servers
        commit_blacklist_change(sess,
            BlacklistCommand(
                command=BlacklistCommandType.EXPIRE_ALL,
                # server_mask=server_mask,
                server_mask=2**32 - 1,
                payload=BlacklistExpireAllCommand(
                    player_id=player_id, kick_only_server_mask=kick_only_mask & ~ban_mask
                ).model_dump(),
            )
        )


class BlacklistCommandType(IntEnum):
    CREATE_RECORD = auto()
    EDIT_RECORD = auto()
    DELETE_RECORD = auto()
    # CREATE_LIST = auto()
    EDIT_LIST = auto()
    DELETE_LIST = auto()
    EXPIRE_ALL = auto()
    BARRICADE_WARN_ONLINE = auto()


class BlacklistCreateRecordCommand(BaseModel):
    player_id: str
    record_id: int


class BlacklistEditRecordCommand(BaseModel):
    old_record: BlacklistRecordWithBlacklistType


class BlacklistDeleteRecordCommand(BaseModel):
    old_record: BlacklistRecordWithBlacklistType


class BlacklistEditListCommand(BaseModel):
    old_blacklist: BlacklistType
    new_blacklist: BlacklistType


class BlacklistDeleteListCommand(BaseModel):
    blacklist: BlacklistType
    banned_players: dict[str, tuple[datetime, datetime | None]]


class BlacklistExpireAllCommand(BaseModel):
    player_id: str
    # None identifies a historical command that did not capture the prior
    # synchronization modes. Never infer ownership from that old payload.
    kick_only_server_mask: int | None = None

    @field_validator('kick_only_server_mask')
    @classmethod
    def validate_server_mask(cls, value):
        if value is not None and not 0 <= value <= 0xFFFFFFFF:
            raise ValueError('Invalid kick-only server mask')
        return value


class BlacklistBarricadeWarnOnlineCommand(BaseModel):
    player_ids: list[str]
    game: str | None = None


@dataclass
class BlacklistCommand:
    command: BlacklistCommandType
    server_mask: int
    payload: dict

    @field_validator("server_mask", mode="before")
    @classmethod
    def convert_none_to_mask(cls, v: int | None) -> int:
        if v is None:
            # Create mask with the first 32 bits flipped
            return 2**32 - 1
        return v

    def encode(self):
        return struct.pack("II", self.command, self.server_mask) + orjson.dumps(
            self.payload
        )

    @classmethod
    def decode(cls, data: bytes):
        split_at = struct.calcsize("II")

        command_id, server_mask = struct.unpack("II", data[:split_at])
        command = BlacklistCommandType(command_id)

        payload = orjson.loads(data[split_at:])

        return cls(command=command, server_mask=server_mask, payload=payload)


class BlacklistCommandHandler:
    CHANNEL = "blacklist"

    def __init__(self) -> None:
        redis_url = os.getenv("HLL_REDIS_URL")
        if not redis_url:
            raise RuntimeError("HLL_REDIS_URL not set")

        # Initialize our own little Redis client, because the shared one has
        # a global timeout and attempts to decode our little packets
        self.red = redis.Redis.from_url(
            redis_url, single_connection_client=True, decode_responses=False
        )

        self.pubsub = self.red.pubsub(ignore_subscribe_messages=True)
        self.rcon = get_rcon()

    def run(self, stop_event: threading.Event | None = None):
        """Run the command handler loop. This is a blocking call."""
        stop_event = stop_event or threading.Event()
        logger.info("Starting blacklist command handler loop")

        # Subscribe to channel
        self.pubsub.subscribe(self.CHANNEL)

        # A bounded wait makes the service cooperatively stoppable when it runs
        # as a thread in the shared supervisor runtime. The standalone command
        # keeps its original indefinite behavior because its event is never set.
        while not stop_event.is_set():
            try:
                from rcon.blacklist_sync_journal import process_one
                process_one(SERVER_NUMBER, self.dispatch, is_ready=self._game_server_ready,
                            prepare=self._prepare_delivery)
            except Exception:
                logger.exception("Unable to process durable blacklist delivery")
            message = self.pubsub.get_message(timeout=1.0)
            if message is None:
                continue
            try:
                data = message["data"]
                if BlacklistCommand.decode(data).server_mask & get_server_number_mask():
                    self.dispatch(data, self._prepare_delivery(data))
            except Exception:
                logger.exception("Failed to process legacy blacklist notification")
        self.pubsub.close()

    def _game_server_ready(self):
        """Only an actual game-server response permits queued side effects."""
        try:
            state = self.rcon.get_gamestate()
            return isinstance(state, dict) and bool(state)
        except Exception:
            logger.debug("Blacklist synchronization deferred: game server unavailable")
            return False

    def _prepare_delivery(self, data: bytes):
        """Resolve online Steam identities before acquiring the shared lock."""
        try:
            cmd = BlacklistCommand.decode(data)
        except Exception:
            # Leave malformed entries to normal dispatch, which moves them to
            # review instead of deferring them forever as a failed live read.
            return None
        if (cmd.command == BlacklistCommandType.EDIT_LIST
                and getattr(getattr(self.rcon, 'game_profile', None), 'game', None) == GameEnum.HLL_VIETNAM):
            try:
                payload = BlacklistEditListCommand.model_validate(cmd.payload)
                if self._hllv_kick_list_newly_enabled(payload):
                    return {'kick_list_players': prepare_online_identity_snapshot(self.rcon)}
            except (ValueError, KeyError, TypeError):
                # Snapshot failures must remain queued; malformed command
                # payloads are handled by normal dispatch and review.
                try:
                    BlacklistEditListCommand.model_validate(cmd.payload)
                except Exception:
                    return None
                raise
        if cmd.command == BlacklistCommandType.CREATE_RECORD:
            player_id = cmd.payload.get('player_id')
        elif cmd.command in (BlacklistCommandType.EDIT_RECORD, BlacklistCommandType.DELETE_RECORD):
            player_id = cmd.payload.get('old_record', {}).get('player_id')
        else:
            player_id = None
        if (getattr(getattr(self.rcon, 'game_profile', None), 'game', None) == GameEnum.HLL_VIETNAM
                and isinstance(player_id, str) and is_steam_id_64(player_id)):
            return prepare_online_steam_identity(self.rcon, player_id)
        return None

    def dispatch(self, data: bytes, prepared=None):
        """Execute one decoded delivery, propagating failures to its journal."""
        with lock(f"blacklist-sync:{SERVER_NUMBER}"):
            return self._dispatch(data, prepared)

    def _dispatch(self, data: bytes, prepared=None):
        cmd = BlacklistCommand.decode(data)
        if not (cmd.server_mask & get_server_number_mask()):
            raise ValueError("Blacklist delivery targets another server")
        handlers = {
            BlacklistCommandType.CREATE_RECORD: (BlacklistCreateRecordCommand, self.handle_create_record),
            BlacklistCommandType.EDIT_RECORD: (BlacklistEditRecordCommand, self.handle_edit_record),
            BlacklistCommandType.DELETE_RECORD: (BlacklistDeleteRecordCommand, self.handle_delete_record),
            BlacklistCommandType.EDIT_LIST: (BlacklistEditListCommand, self.handle_edit_list),
            BlacklistCommandType.DELETE_LIST: (BlacklistDeleteListCommand, self.handle_delete_list),
            BlacklistCommandType.EXPIRE_ALL: (BlacklistExpireAllCommand, self.handle_expire_all),
            BlacklistCommandType.BARRICADE_WARN_ONLINE: (BlacklistBarricadeWarnOnlineCommand, self.handle_barricade_warn_online),
        }
        schema, handler = handlers[cmd.command]
        logger.info("Handling %s command", cmd.command.name)
        payload = schema.model_validate(cmd.payload)
        if cmd.command in (BlacklistCommandType.CREATE_RECORD, BlacklistCommandType.EDIT_RECORD,
                           BlacklistCommandType.DELETE_RECORD, BlacklistCommandType.EDIT_LIST):
            handler(payload, prepared=prepared)
        else:
            handler(payload)

    @staticmethod
    def send(cmd: BlacklistCommand):
        if cmd.server_mask == 0:
            # Command will be ignored by all servers, don't bother sending it.
            return

        red.publish(BlacklistCommandHandler.CHANNEL, cmd.encode())

    def handle_create_record(self, payload: BlacklistCreateRecordCommand, prepared=None):
        """Handle a new record being created."""
        with blacklist_change_session() as sess:
            top_record = is_player_blacklisted(sess, player_id=payload.player_id)

            if top_record is None or top_record.id != payload.record_id:
                # The new ban does not have priority, so we don't
                # have to do anything
                logger.info(
                    "Newly created record does not take priority and will be ignored"
                )
                return

            if _is_hllv_steam_id(self.rcon, payload.player_id):
                self._apply_hllv_steam_record(sess, payload.player_id, top_record, prepared)
                return

            old_record = is_player_blacklisted(
                sess, player_id=payload.player_id, exclude={payload.record_id}
            )

            synchronize_ban(
                self.rcon,
                player_id=payload.player_id,
                new_record=top_record,
                old_state=get_ban_state_from_record(old_record),
            )

    def _apply_hllv_steam_record(self, sess, steam_id, top_record, prepared):
        if not isinstance(prepared, dict) or prepared.get('steam_id') != steam_id:
            raise HLLVSteamIdentityUnverified('HLLV Steam identity was not prepared')
        eos_id = prepared.get('eos_id')
        if eos_id is None:
            if top_record.blacklist.sync == BlacklistSyncMethod.BAN_IMMEDIATELY:
                if top_record.expires_at is None or _blacklist_remaining_hours(top_record) >= 1:
                    raise HLLVSteamIdentityUnverified('No verified online EOS identity for immediate ban')
            logger.info('Steam restriction retained for the next verified HLLV connection')
            return
        eos_record = is_player_blacklisted(sess, player_id=eos_id)
        if eos_record is not None and get_highest_priority_record([top_record, eos_record]).id != top_record.id:
            logger.info('Existing EOS restriction has higher priority')
            return
        with self.rcon.without_retries():
            details = self.rcon.get_uncached_detailed_player_info(player_id=eos_id)
        if verified_steam_id(self.rcon, eos_id, details) != steam_id:
            raise HLLVSteamIdentityUnverified('HLLV Steam-to-EOS association changed before action')
        result = apply_blacklist_punishment(self.rcon, top_record, player_id=eos_id,
                                            player_name=details.get('name'))
        if result is not True and result is not _BLACKLIST_ACTION_EXPIRED:
            raise RuntimeError('Could not confirm HLLV blacklist action')

    def _handle_hllv_steam_record_change(self, sess, old_record, new_record, prepared):
        old_applies = (old_record['blacklist']['servers'] is None
                       or SERVER_NUMBER in old_record['blacklist']['servers'])
        if old_applies and old_record['blacklist']['sync'] != BlacklistSyncMethod.KICK_ONLY:
            # The game server does not expose an ownership marker proving an
            # existing EOS ban came from this record. Never remove or replace
            # a possibly independent ban based on a Steam-only identifier.
            raise HLLVSteamBanOwnershipUnverified('Existing EOS game-ban ownership needs review')
        if new_record is None:
            return
        if new_record.blacklist.sync == BlacklistSyncMethod.KICK_ONLY:
            # A newly applicable kick-only record, or a remaining record that
            # becomes effective when the old one disappears, must still be
            # applied to a verified online player. Unchanged/lower-priority
            # edits must not generate another kick.
            same_record = new_record.id == old_record['id']
            became_effective = (not old_applies and same_record) or (
                old_applies and not same_record and _is_higher_priority_record(
                    old_record['created_at'], old_record['expires_at'],
                    new_record.created_at, new_record.expires_at,
                )
            )
            if not became_effective:
                return
        self._apply_hllv_steam_record(sess, old_record['player_id'], new_record, prepared)

    def handle_edit_record(self, payload: BlacklistEditRecordCommand, prepared=None):
        """Handle a record being edited.

        This simply will synchronize the player's ban if either the old
        or new ban had or has priority. You may assume at least one of
        the attributes below were changed, otherwise this method can and
        should be avoided.
        - record.expires_at
        - record.reason
        - record.blacklist.sync"""
        old_record = payload.old_record
        with blacklist_change_session() as sess:
            new_record = is_player_blacklisted(sess, player_id=old_record["player_id"])
            if _is_hllv_steam_id(self.rcon, old_record['player_id']):
                self._handle_hllv_steam_record_change(sess, old_record, new_record, prepared)
                return
            old_applies = (
                old_record["blacklist"]["servers"] is None
                or SERVER_NUMBER in old_record["blacklist"]["servers"]
            )

            if not new_record and old_applies:
                synchronize_ban(
                    self.rcon,
                    player_id=old_record["player_id"],
                    new_record=None,
                    old_state=get_ban_state_from_record(old_record),
                )

            # Check whether the old or new record had or has priority
            elif new_record and (new_record.id == old_record["id"] or (
                old_applies
                and _is_higher_priority_record(
                    old_record["created_at"],
                    old_record["expires_at"],
                    new_record.created_at,
                    new_record.expires_at,
                )
            )):
                synchronize_ban(
                    self.rcon,
                    player_id=old_record["player_id"],
                    new_record=new_record,
                    old_state=get_ban_state_from_record(old_record) if old_applies else BanState.NONE,
                )

    def handle_delete_record(self, payload: BlacklistDeleteRecordCommand, prepared=None):
        """Handle a record being deleted.

        This assumes that the record has not expired and is active on the current
        server.
        """
        old_record = payload.old_record
        with blacklist_change_session() as sess:
            new_record = is_player_blacklisted(sess, player_id=old_record["player_id"])
            if _is_hllv_steam_id(self.rcon, old_record['player_id']):
                self._handle_hllv_steam_record_change(sess, old_record, new_record, prepared)
                return

            if (
                # Check whether the removed record had a higher priority
                # than the current top record
                new_record is None
                or _is_higher_priority_record(
                    old_record["created_at"],
                    old_record["expires_at"],
                    new_record.created_at,
                    new_record.expires_at,
                )
            ):
                synchronize_ban(
                    self.rcon,
                    player_id=old_record["player_id"],
                    new_record=new_record,
                    old_state=get_ban_state_from_record(old_record),
                )

    @staticmethod
    def _hllv_kick_list_newly_enabled(payload):
        old, new = payload.old_blacklist, payload.new_blacklist
        old_applies = old['servers'] is None or SERVER_NUMBER in old['servers']
        new_applies = new['servers'] is None or SERVER_NUMBER in new['servers']
        return not old_applies and new_applies and new['sync'] == BlacklistSyncMethod.KICK_ONLY

    def _apply_new_hllv_kick_list(self, payload, prepared):
        if not isinstance(prepared, dict) or not isinstance(prepared.get('kick_list_players'), dict):
            raise HLLVSteamIdentityUnverified('New kick-only list needs a verified roster')
        players = prepared['kick_list_players']
        list_id = payload.new_blacklist['id']
        with blacklist_change_session() as sess:
            current = get_blacklist(sess, list_id)
            if (current is None or current.sync != BlacklistSyncMethod.KICK_ONLY
                    or (current.servers is not None and not current.servers & get_server_number_mask())):
                raise RuntimeError('Blacklist configuration changed before reconciliation')
            def live_details(eos, identity):
                steam = identity['steam_id']
                with self.rcon.without_retries():
                    details = self.rcon.get_uncached_detailed_player_info(player_id=eos)
                if (not isinstance(details, dict) or details.get('player_id') != eos
                        or details.get('eos_id') != eos
                        or str(details.get('platform') or '').strip().lower() != identity['platform']
                        or (steam and verified_steam_id(self.rcon, eos, details) != steam)
                        or (not steam and details.get('steam_id'))):
                    raise HLLVSteamIdentityUnverified('Player identity changed before list reconciliation')
                return details

            actions = []
            for eos, identity in players.items():
                records = [is_player_blacklisted(sess, eos)]
                steam = identity['steam_id']
                if steam:
                    records.append(is_player_blacklisted(sess, steam))
                records = [entry for entry in records if entry is not None]
                effective = get_highest_priority_record(records) if records else None
                if effective is None or effective.blacklist_id != list_id:
                    continue
                # Prepare the whole batch before sending the first action.
                live_details(eos, identity)
                actions.append((eos, identity, effective))
            for eos, identity, effective in actions:
                try:
                    details = live_details(eos, identity)
                except Exception as exc:
                    # An earlier player may already have been acted upon.
                    raise RuntimeError('Identity changed during kick-only list reconciliation') from exc
                result = apply_blacklist_punishment(self.rcon, effective, player_id=eos,
                                                    player_name=details.get('name'))
                if result is not True and result is not _BLACKLIST_ACTION_EXPIRED:
                    # Earlier players may already have been acted upon; do not
                    # identify this as a wholly unattempted identity failure.
                    raise RuntimeError('Could not confirm kick-only list reconciliation')

    def handle_edit_list(self, payload: BlacklistEditListCommand, prepared=None):
        """Handle a blacklist being edited.

        This must be called only on servers targeted by the blacklist
        before and/or after editing."""
        old_blacklist = payload.old_blacklist
        new_blacklist = payload.new_blacklist

        if (getattr(getattr(self.rcon, 'game_profile', None), 'game', None) == GameEnum.HLL_VIETNAM
                and self._hllv_kick_list_newly_enabled(payload)):
            return self._apply_new_hllv_kick_list(payload, prepared)

        was_banning = (
            old_blacklist["servers"] is None
            or SERVER_NUMBER in old_blacklist["servers"]
        ) and old_blacklist["sync"] != BlacklistSyncMethod.KICK_ONLY

        is_banning = (
            new_blacklist["servers"] is None
            or SERVER_NUMBER in new_blacklist["servers"]
        ) and new_blacklist["sync"] != BlacklistSyncMethod.KICK_ONLY

        enable_immediate = (
            was_banning and is_banning
            and old_blacklist["sync"] == BlacklistSyncMethod.BAN_ON_CONNECT
            and new_blacklist["sync"] == BlacklistSyncMethod.BAN_IMMEDIATELY
        )
        if was_banning == is_banning and not enable_immediate:
            if (was_banning and old_blacklist['sync'] == BlacklistSyncMethod.BAN_IMMEDIATELY
                    and new_blacklist['sync'] == BlacklistSyncMethod.BAN_ON_CONNECT
                    and getattr(getattr(self.rcon, 'game_profile', None), 'game', None) == GameEnum.HLL_VIETNAM):
                # Existing game bans may keep players out before the new
                # connect-only rule can show its message. Their ownership is
                # not established, so never silently acknowledge or remove
                # them. Perform this check before any game-server action.
                with blacklist_change_session() as sess:
                    if next(iter(get_active_blacklist_records(sess, new_blacklist['id'])), None) is not None:
                        raise HLLVBanOwnershipUnverified('List mode change needs game-ban ownership review')
            return

        with blacklist_change_session() as sess:
            records = list(get_active_blacklist_records(sess, new_blacklist["id"]))
            if any(_is_hllv_steam_id(self.rcon, record.player.player_id) for record in records):
                # Do not process other entries first and then discover that a
                # Steam-ID item needs an EOS/ownership reconciliation.
                raise HLLVSteamBanOwnershipUnverified('Steam list changes need EOS ownership review')
            for record in records:
                player_id = record.player.player_id
                if enable_immediate:
                    current = is_player_blacklisted(sess, player_id)
                    if current is not None and current.id == record.id:
                        synchronize_ban(self.rcon, player_id, record, get_ban_state_from_record(record))
                    continue
                other_records = [
                    other for other in get_player_blacklist_records(
                        sess, player_id, include_expired=False, include_other_servers=False,
                        exclude={record.id},
                    )
                    if other.blacklist_id != new_blacklist["id"]
                    and other.blacklist.sync != BlacklistSyncMethod.KICK_ONLY
                ]
                other = get_highest_priority_record(other_records)
                before = get_highest_priority_record(
                    ([record] if was_banning else []) + ([other] if other else [])
                )
                after = get_highest_priority_record(
                    ([record] if is_banning else []) + ([other] if other else [])
                )
                if before is after:
                    continue
                if before is None:
                    old_state = BanState.NONE
                else:
                    old_state = BanState.PERMA if before.expires_at is None else BanState.TEMP

                synchronize_ban(
                    rcon=self.rcon,
                    player_id=player_id,
                    new_record=after,
                    old_state=old_state,
                )

    def handle_delete_list(self, payload: BlacklistDeleteListCommand):
        """Handle a blacklist being deleted.

        If no active records are on the given blacklist this method is obsolete.
        Assumes that the highest priority record for each player is included
        in the payload, but only if they are active. Expired records should be
        omitted."""
        if not payload.banned_players:
            return

        failures = 0
        with blacklist_change_session() as sess:
            steam_ids = {player_id for player_id in payload.banned_players
                         if _is_hllv_steam_id(self.rcon, player_id)}
            if steam_ids:
                if payload.blacklist["sync"] != BlacklistSyncMethod.KICK_ONLY:
                    raise HLLVSteamBanOwnershipUnverified('Steam list deletion needs EOS ownership review')
                # No action is needed if there is no remaining restriction,
                # or if an existing one was strictly higher priority even
                # before deletion. Equal priority is ambiguous: record order
                # can determine which rule was effective. Preflight every
                # Steam entry before touching any other player.
                for player_id in steam_ids:
                    remaining = is_player_blacklisted(sess, player_id)
                    if remaining is None:
                        continue
                    removed_created, removed_expires = payload.banned_players[player_id]
                    if not _is_higher_priority_record(
                        remaining.created_at, remaining.expires_at,
                        removed_created, removed_expires,
                    ):
                        raise HLLVSteamIdentityUnverified('Steam list deletion has remaining restrictions')
            for player_id, (created_at, expires_at) in payload.banned_players.items():
                if player_id in steam_ids:
                    continue
                try:
                    new_record = is_player_blacklisted(sess, player_id)
                    if (
                        # Check whether the removed record had a higher priority
                        # than the current top record
                        new_record is None
                        or _is_higher_priority_record(
                            created_at,
                            expires_at,
                            new_record.created_at,
                            new_record.expires_at,
                        )
                    ):
                        if payload.blacklist["sync"] == BlacklistSyncMethod.KICK_ONLY:
                            old_state = BanState.NONE
                        elif expires_at is None:
                            old_state = BanState.PERMA
                        else:
                            old_state = BanState.TEMP
                        synchronize_ban(self.rcon, player_id, new_record, old_state)
                except Exception:
                    failures += 1
                    logger.exception(
                        "Failed to synchronize ban for player %s after deleting blacklist",
                        player_id,
                    )
        if failures:
            raise RuntimeError(f"Could not confirm {failures} blacklist synchronization(s)")

    def handle_expire_all(self, payload: BlacklistExpireAllCommand):
        if _is_hllv_steam_id(self.rcon, payload.player_id):
            mask = getattr(payload, 'kick_only_server_mask', None)
            if mask is not None and mask & get_server_number_mask():
                with blacklist_change_session() as sess:
                    if is_player_blacklisted(sess, payload.player_id) is not None:
                        raise HLLVSteamIdentityUnverified('A Steam restriction is still active')
                logger.info('Expired kick-only Steam restrictions need no game-server unban')
                return
            raise HLLVSteamBanOwnershipUnverified('Steam expiry needs EOS ownership review')
        with lock(f"blacklist-sync:{SERVER_NUMBER}"):
            _require_blacklist_action_review_clear(payload.player_id)
            self._handle_expire_all(payload)

    def _handle_expire_all(self, payload: BlacklistExpireAllCommand):
        """Handle all of a player's active blacklist records being expired,
        effectively granting them access to the server whilst keeping all
        previous blacklists logged.

        Note that if a player was only temporarily blacklisted but also had
        a permanent ban, that permanent ban will also be removed."""
        # Check if the player is temp-banned
        if next(
            (
                True
                for ban in self.rcon.get_temp_bans()
                if ban["player_id"] == payload.player_id
            ),
            False,
        ):
            # Remove their temp-ban
            if self.rcon.remove_temp_ban(payload.player_id) is not True:
                raise RuntimeError("Game server did not confirm temporary ban removal")

        # Check if the player is perma-banned
        if next(
            (
                True
                for ban in self.rcon.get_perma_bans()
                if ban["player_id"] == payload.player_id
            ),
            False,
        ):
            # Remove their perma-ban
            if self.rcon.remove_perma_ban(payload.player_id) is not True:
                raise RuntimeError("Game server did not confirm permanent ban removal")

    def handle_barricade_warn_online(
        self, payload: BlacklistBarricadeWarnOnlineCommand
    ):
        game = barricade_game_for_server()
        if payload.game is not None and payload.game != game:
            return
        online_player_ids = [
            player_id
            for _, player_id in self.rcon.get_player_ids()
            if player_id in payload.player_ids
        ]

        if online_player_ids:
            send_to_barricade(
                request_type=ServerRequestType.SCAN_PLAYERS,
                payload=ScanPlayersRequestPayload(player_ids=online_player_ids, game=game).model_dump(),
            )
