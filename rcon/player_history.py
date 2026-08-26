import datetime
import logging
import math
import os
import unicodedata
from functools import cmp_to_key

from dateutil import parser
from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, contains_eager, selectinload
from sqlalchemy.sql.functions import ReturnTypeFromArgs

from rcon.commands import HLLCommandFailedError
from rcon.models import (
    BlacklistRecord,
    PlayerAccount,
    PlayerActionState,
    PlayerComment,
    PlayerFlag,
    PlayerID,
    PlayerName,
    PlayersAction,
    PlayerSession,
    PlayerSoldier,
    PlayerVIP,
    SteamInfo,
    WatchList,
    enter_session,
)
from rcon.steam_utils import is_steam_id_64
from rcon.types import (
    LivePlayerProfileType,
    PlayerActionState,
    PlayerActionType,
    PlayerCommentType,
    PlayerFlagType,
    PlayerProfileType,
)
from rcon.user_config.rcon_server_settings import RconServerSettingsUserConfig
from rcon.utils import get_server_number, strtobool


class unaccent(ReturnTypeFromArgs):
    pass


logger = logging.getLogger(__name__)


def player_has_flag(player_dict, flag) -> bool:
    flags = player_dict.get("flags") or []

    return flag in {flag["flag"] for flag in flags}


def get_player(sess: Session, player_id: str) -> PlayerID | None:
    return sess.query(PlayerID).filter(PlayerID.player_id == player_id).one_or_none()


def _player_identity_name(player: PlayerID) -> str:
    if player.account and player.account.name:
        return player.account.name
    if player.names:
        return player.names[0].name
    if player.soldier and player.soldier.name:
        return player.soldier.name
    return player.player_id


def _existing_player_blacklists(player: PlayerID) -> list[dict]:
    """Return blacklist records that still exist as active restrictions.

    The record may belong to another FLN server.  This is useful as an
    administrative risk signal, but does not make the restriction applicable
    to the current game server and must never trigger an automatic action.
    """
    return [
        record
        for record in (blacklist.to_dict() for blacklist in player.blacklists)
        if record["is_active"]
    ]


def _active_player_blacklists(player: PlayerID) -> list[dict]:
    this_server = int(get_server_number())
    return [
        record
        for record in _existing_player_blacklists(player)
        if (
            record["blacklist"]["servers"] is None
            or this_server in record["blacklist"]["servers"]
        )
    ]


def get_player_identity_links(sess: Session, players: list[PlayerID]) -> dict[str, dict]:
    """Resolve HLL and HLL:V records belonging to the same Steam account.

    HLL:V keeps its game-specific player ID because logs and admin commands need
    it. The persisted ``steam_id`` is used as a non-destructive identity link to
    the classic HLL record. Names are deliberately never used for matching.
    """
    if not players:
        return {}

    canonical_ids = {
        player.steam_id
        if player.steam_id and is_steam_id_64(player.steam_id)
        else player.player_id
        for player in players
    }
    related = (
        sess.query(PlayerID)
        .filter(
            or_(
                PlayerID.player_id.in_(canonical_ids),
                PlayerID.steam_id.in_(canonical_ids),
            )
        )
        .options(
            selectinload(PlayerID.names),
            selectinload(PlayerID.account),
            selectinload(PlayerID.soldier),
            selectinload(PlayerID.blacklists).selectinload(BlacklistRecord.blacklist),
        )
        .all()
    )

    groups: dict[str, list[PlayerID]] = {}
    for related_player in related:
        identity_key = (
            related_player.steam_id
            if related_player.steam_id and is_steam_id_64(related_player.steam_id)
            else related_player.player_id
        )
        groups.setdefault(identity_key, []).append(related_player)

    result = {}
    for player in players:
        identity_key = (
            player.steam_id
            if player.steam_id and is_steam_id_64(player.steam_id)
            else player.player_id
        )
        identity_group = groups.get(identity_key, [])
        has_classic_hll_account = is_steam_id_64(identity_key) and any(
            linked.player_id == identity_key for linked in identity_group
        )
        linked_accounts = (
            [
                {
                    "player_id": linked.player_id,
                    "steam_id": linked.steam_id,
                    "name": _player_identity_name(linked),
                    "active_blacklists": _active_player_blacklists(linked),
                    "existing_blacklists": _existing_player_blacklists(linked),
                    "game": (
                        "hll"
                        if len(linked.player_id) == 17 and linked.player_id.isdigit()
                        else "hll_vietnam"
                    ),
                }
                for linked in identity_group
                if linked.player_id != player.player_id
            ]
            if has_classic_hll_account
            else []
        )
        result[player.player_id] = {
            "linked_accounts": linked_accounts,
        }

    return result


def get_player_profile(player_id: str, nb_sessions: int):
    nb_sessions = int(nb_sessions)

    with enter_session() as sess:
        player = (
            sess.query(PlayerID).filter(PlayerID.player_id == player_id).one_or_none()
        )
        if player is None:
            return
        profile = player.to_dict(limit_sessions=nb_sessions)
        profile["identity"] = get_player_identity_links(sess, [player])[player_id]
        return profile


def get_player_profile_by_player_ids(sess, player_ids):
    return (
        sess.query(PlayerID)
        .filter(PlayerID.player_id.in_(player_ids))
        .options(
            selectinload(PlayerID.names),
            selectinload(PlayerID.received_actions),
            selectinload(PlayerID.blacklists),
            selectinload(PlayerID.flags),
            selectinload(PlayerID.watchlist),
            selectinload(PlayerID.steaminfo),
            selectinload(PlayerID.soldier),
        )
        .all()
    )


def get_player_profile_by_id(id, nb_sessions):
    with enter_session() as sess:
        player = sess.query(PlayerID).filter(PlayerID.id == id).one_or_none()
        if player is None:
            return
        return player.to_dict(limit_sessions=nb_sessions)


def _get_profiles(sess, player_ids, nb_sessions=0):
    return (
        sess.query(PlayerID)
        .filter(PlayerID.player_id.in_(player_ids))
        .options(selectinload(PlayerID.soldier))
        .all()
    )


def _get_serializable_profiles(sess, player_ids):
    """Load every relationship used by ``PlayerID.to_dict`` in batches."""
    return (
        sess.query(PlayerID)
        .filter(PlayerID.player_id.in_(player_ids))
        .options(
            selectinload(PlayerID.names),
            selectinload(PlayerID.sessions),
            selectinload(PlayerID.received_actions),
            selectinload(PlayerID.blacklists).selectinload(BlacklistRecord.blacklist),
            selectinload(PlayerID.flags),
            selectinload(PlayerID.watchlist),
            selectinload(PlayerID.steaminfo),
            selectinload(PlayerID.soldier),
            selectinload(PlayerID.account),
        )
        .all()
    )


def _get_vips_by_player(sess, player_database_ids):
    vips_by_player: dict[int, list[PlayerVIP]] = {}
    if not player_database_ids:
        return vips_by_player

    for vip in (
        sess.query(PlayerVIP)
        .filter(PlayerVIP.player_id_id.in_(player_database_ids))
        .all()
    ):
        vips_by_player.setdefault(vip.player_id_id, []).append(vip)
    return vips_by_player


def get_profiles(player_ids, nb_sessions=1):
    with enter_session() as sess:
        players = _get_serializable_profiles(sess, player_ids)
        vips_by_player = _get_vips_by_player(sess, [player.id for player in players])

        return [
            player.to_dict(
                limit_sessions=nb_sessions,
                preloaded_vips=vips_by_player.get(player.id, []),
            )
            for player in players
        ]


def _current_session_summary(sess, player_database_ids):
    """Return session count and latest session without hydrating history rows."""
    if not player_database_ids:
        return {}

    ranked_sessions = (
        sess.query(
            PlayerSession.player_id_id.label("player_id_id"),
            PlayerSession.start.label("start"),
            PlayerSession.end.label("end"),
            PlayerSession.created.label("created"),
            func.count(PlayerSession.id)
            .over(partition_by=PlayerSession.player_id_id)
            .label("sessions_count"),
            func.row_number()
            .over(
                partition_by=PlayerSession.player_id_id,
                order_by=(PlayerSession.created.desc(), PlayerSession.id.desc()),
            )
            .label("session_rank"),
        )
        .filter(PlayerSession.player_id_id.in_(player_database_ids))
        .subquery()
    )
    rows = sess.query(ranked_sessions).filter(ranked_sessions.c.session_rank == 1).all()
    return {row.player_id_id: row for row in rows}


def _current_playtime_seconds(session_summary) -> int:
    if session_summary is None or session_summary.end:
        return 0
    started_at = session_summary.start or session_summary.created
    if started_at is None:
        return 0
    now = (
        datetime.datetime.now(tz=started_at.tzinfo)
        if started_at.tzinfo
        else datetime.datetime.now()
    )
    return max(0, int((now - started_at).total_seconds()))


def _watchlist_dict(player: PlayerID):
    watch = player.watchlist
    if watch is None:
        return None
    return {
        "id": watch.id,
        "modified": watch.modified,
        "player_id": player.player_id,
        "is_watched": watch.is_watched,
        "reason": watch.reason,
        "by": watch.by,
        "count": watch.count,
    }


def _blacklist_record_dict(record: BlacklistRecord, player_id: str):
    return {
        "id": record.id,
        "player_id": player_id,
        "reason": record.reason,
        "admin_name": record.admin_name,
        "created_at": record.created_at,
        "expires_at": record.expires_at,
        "is_active": True,
        "blacklist": record.blacklist.to_dict(with_records=False),
    }


def get_live_profiles(
    player_ids, action_window_hours: int = 24
) -> list[LivePlayerProfileType]:
    """Return the bounded profile projection required by live roster screens.

    History-heavy collections are deliberately excluded. Query count remains
    constant as the online population grows.
    """
    if not player_ids:
        return []

    with enter_session() as sess:
        players = (
            sess.query(PlayerID)
            .filter(PlayerID.player_id.in_(player_ids))
            .options(
                selectinload(PlayerID.flags),
                selectinload(PlayerID.watchlist),
                selectinload(PlayerID.steaminfo),
                selectinload(PlayerID.soldier),
            )
            .all()
        )
        if not players:
            return []

        database_ids = [player.id for player in players]
        session_summaries = _current_session_summary(sess, database_ids)

        actions_by_player: dict[int, list[dict]] = {}
        action_cutoff = datetime.datetime.utcnow() - datetime.timedelta(
            hours=max(1, int(action_window_hours))
        )
        for action in (
            sess.query(PlayersAction)
            .filter(
                PlayersAction.player_id_id.in_(database_ids),
                PlayersAction.time > action_cutoff,
            )
            .order_by(PlayersAction.player_id_id, PlayersAction.time.desc())
            .all()
        ):
            actions_by_player.setdefault(action.player_id_id, []).append(
                action.to_dict()
            )

        blacklist_records_by_player: dict[int, list[dict]] = {}
        blacklist_cutoff = datetime.datetime.now(tz=datetime.timezone.utc)
        active_blacklist_records = (
            sess.query(BlacklistRecord)
            .filter(
                BlacklistRecord.player_id_id.in_(database_ids),
                or_(
                    BlacklistRecord.expires_at.is_(None),
                    BlacklistRecord.expires_at > blacklist_cutoff,
                ),
            )
            .options(selectinload(BlacklistRecord.blacklist))
            .all()
        )
        player_ids_by_database_id = {player.id: player.player_id for player in players}
        for record in active_blacklist_records:
            blacklist_records_by_player.setdefault(record.player_id_id, []).append(
                _blacklist_record_dict(
                    record, player_ids_by_database_id[record.player_id_id]
                )
            )

        this_server = int(get_server_number())
        profiles: list[LivePlayerProfileType] = []
        for player in players:
            summary = session_summaries.get(player.id)
            blacklists = blacklist_records_by_player.get(player.id, [])
            is_blacklisted = any(
                record["blacklist"]["servers"] is None
                or this_server in record["blacklist"]["servers"]
                for record in blacklists
            )
            watchlist = _watchlist_dict(player)
            profiles.append(
                {
                    "id": player.id,
                    "player_id": player.player_id,
                    "steam_id": player.steam_id,
                    "created": player.created,
                    "sessions_count": summary.sessions_count if summary else 0,
                    "current_playtime_seconds": _current_playtime_seconds(summary),
                    "received_actions": actions_by_player.get(player.id, []),
                    "blacklists": blacklists,
                    "is_blacklisted": is_blacklisted,
                    "flags": [flag.to_dict() for flag in (player.flags or [])],
                    "watchlist": watchlist,
                    "is_watched": bool(watchlist and watchlist["is_watched"]),
                    "steaminfo": (
                        player.steaminfo.to_dict() if player.steaminfo else None
                    ),
                    "soldier": (player.soldier.to_dict() if player.soldier else None),
                }
            )

        return profiles


def _get_set_player(
    sess: Session,
    player_id: str,
    player_name: str | None = None,
    timestamp: float | None = None,
    *,
    steam_id: str | None = None,
):
    player = get_player(sess, player_id)
    if player is None:
        player = _save_player_id(sess, player_id)
    if player_name:
        _save_player_alias(
            sess, player, player_name, timestamp or datetime.datetime.now().timestamp()
        )
    if steam_id:
        player.steam_id = steam_id
        sess.commit()

    return player


def remove_accent(s):
    return unicodedata.normalize("NFD", s).encode("ascii", "ignore").decode("utf-8")


def get_players_by_appearance(
    page: int = 1,
    page_size: int = 500,
    last_seen_from: datetime.datetime | None = None,
    last_seen_till: datetime.datetime | None = None,
    player_id: str | None = None,
    player_name: str | None = None,
    blacklisted: bool | None = None,
    is_watched: bool | None = None,
    exact_name_match: bool = False,
    ignore_accent: bool = True,
    flags: str | list[str] | None = None,
    country: str | None = None,
):
    page = int(page)
    page_size = int(page_size)

    if isinstance(last_seen_from, str):
        last_seen_from = parser.parse(last_seen_from)

    if isinstance(last_seen_till, str):
        last_seen_till = parser.parse(last_seen_till)

    blacklisted = strtobool(blacklisted)
    is_watched = strtobool(is_watched)
    exact_name_match = strtobool(exact_name_match)
    ignore_accent = strtobool(ignore_accent)

    if page <= 0:
        raise ValueError("page needs to be >= 1")
    if page_size <= 0:
        raise ValueError("page_size needs to be >= 1")

    with enter_session() as sess:
        sub = (
            sess.query(
                PlayerSession.player_id_id,
                func.min(
                    func.coalesce(PlayerSession.start, PlayerSession.created)
                ).label("first"),
                func.max(func.coalesce(PlayerSession.end, PlayerSession.created)).label(
                    "last"
                ),
            )
            .group_by(PlayerSession.player_id_id)
            .subquery()
        )
        query = sess.query(PlayerID, sub.c.first, sub.c.last).outerjoin(
            sub, sub.c.player_id_id == PlayerID.id
        )

        if player_id:
            query = query.filter(PlayerID.player_id.ilike("%{}%".format(player_id)))

        if player_name:
            soldier_name = PlayerName.name
            account_name = PlayerAccount.name
            if ignore_accent:
                soldier_name = unaccent(PlayerName.name)
                player_name = remove_accent(player_name)
            if not exact_name_match:
                query = query.join(PlayerID.names).join(PlayerID.account).filter(
                    or_(
                        soldier_name.ilike("%{}%".format(player_name)),
                        account_name.isnot(None) & account_name.ilike("%{}%".format(player_name))
                    )
                )
            else:
                query = query.join(PlayerID.names).join(PlayerID.account).filter(
                    or_(
                        soldier_name == player_name,
                        account_name.isnot(None) & (account_name == player_name)
                    )
                )

        if blacklisted is True:
            query = query.filter(
                sess.query(BlacklistRecord)
                .where(
                    BlacklistRecord.player_id_id == PlayerID.id,
                    or_(
                        BlacklistRecord.expires_at.is_(None),
                        BlacklistRecord.expires_at > func.now(),
                    ),
                )
                .exists()
            )
        if is_watched is True:
            query = (
                query.join(PlayerID.watchlist)
                .filter(WatchList.is_watched == True)
                .options(contains_eager(PlayerID.watchlist))
            )

        if flags:
            if not isinstance(flags, list):
                flags = [flags]
            query = query.join(PlayerID.flags).filter(PlayerFlag.flag.in_(flags))

        if country:
            query = query.join(PlayerID.steaminfo).join(PlayerID.account).filter(
                SteamInfo.country == country.upper() or PlayerAccount.country == country.upper()
            )

        if last_seen_from:
            query = query.filter(sub.c.last >= last_seen_from)
        if last_seen_till:
            query = query.filter(sub.c.last <= last_seen_till)

        total = query.count()
        page = min(max(math.ceil(total / page_size), 1), page)
        players = (
            query.order_by(func.coalesce(sub.c.last, PlayerID.created).desc())
            .limit(page_size)
            .offset((page - 1) * page_size)
            # All relations used in PlayerID.to_dict should be loaded here to avoid lazyloading in the for loop below
            .options(
                selectinload(PlayerID.names),
                selectinload(PlayerID.sessions),
                selectinload(PlayerID.received_actions),
                selectinload(PlayerID.blacklists),
                selectinload(PlayerID.flags),
                selectinload(PlayerID.watchlist),
                selectinload(PlayerID.steaminfo),
                selectinload(PlayerID.account),
                selectinload(PlayerID.soldier),
            )
            .all()
        )

        identity_links = get_player_identity_links(
            sess, [player[0] for player in players]
        )

        def sort_name_match(v, v2):
            if not player_name:
                return 0
            search = player_name.lower()
            v = v.lower()
            v2 = v2.lower()
            if ignore_accent:
                v = remove_accent(v)
                v2 = remove_accent(v2)

            if search in v and search in v2:
                return 0
            if search in v:
                return -1
            return 1

        return {
            "total": total,
            "players": [
                {
                    **p[0].to_dict(limit_sessions=0),
                    "identity": identity_links[p[0].player_id],
                    "names_by_match": sorted(
                        (n.name for n in p[0].names), key=cmp_to_key(sort_name_match)
                    ),
                    "first_seen_timestamp_ms": (
                        int(p[1].timestamp() * 1000) if p[1] else None
                    ),
                    "last_seen_timestamp_ms": (
                        int(p[2].timestamp() * 1000) if p[2] else None
                    ),
                    "vip_expiration": p[0].vip.expiration if p[0].vip else None,
                }
                for p in players
            ],
            "page": page,
            "page_size": page_size,
        }


def _save_player_id(sess, player_id: str) -> PlayerID:
    player = get_player(sess, player_id)

    if not player:
        logger.info("Adding first time seen %s", player_id)
        player = PlayerID(player_id=player_id)
        try:
            # CONNECTED and stats workers can observe a new player at the same
            # time. Isolate the insert in a savepoint so a uniqueness race does
            # not invalidate the caller's complete database transaction.
            with sess.begin_nested():
                sess.add(player)
                sess.add(PlayerAccount(player=player))
                sess.add(PlayerSoldier(player=player))
                sess.flush()
        except IntegrityError:
            player = get_player(sess, player_id)
            if player is None:
                raise
            logger.debug("Player %s was inserted concurrently", player_id)
        else:
            sess.commit()

    return player


def _save_player_alias(sess, player: PlayerID, player_name: str, timestamp=None):
    name = (
        sess.query(PlayerName)
        .filter(PlayerName.name == player_name, PlayerName.player == player)
        .one_or_none()
    )

    if timestamp:
        dt = datetime.datetime.fromtimestamp(timestamp)
    else:
        dt = datetime.datetime.now()
    if not name:
        name = PlayerName(name=player_name, player=player, last_seen=dt)
        sess.add(name)
        logger.info("Adding player %s with new name %s", player.player_id, player_name)
        sess.commit()
    else:
        name.last_seen = dt
        sess.commit()

    return name


def save_player(
    player_name: str,
    player_id: str,
    timestamp: float | None = None,
    *,
    steam_id: str | None = None
) -> None:
    """Create a PlayerID record if non existent and save the player name alias"""
    with enter_session() as sess:
        player = _save_player_id(sess, player_id)
        _save_player_alias(
            sess, player, player_name, timestamp or datetime.datetime.now().timestamp()
        )
        if steam_id:
            player.steam_id = steam_id
            sess.commit()


def save_player_action(
    action_type: PlayerActionState,
    player_id: str,
    player_name: str | None,
    by: str,
    reason: str = "",
    timestamp: float | None = None,
    *,
    steam_id: str | None = None
):
    with enter_session() as sess:
        player = _get_set_player(
            sess,
            player_name=player_name,
            player_id=player_id,
            timestamp=timestamp,
            steam_id=steam_id,
        )
        sess.add(
            PlayersAction(
                action_type=action_type.name.upper(),
                player=player,
                reason=reason,
                by=by,
            )
        )


def safe_save_player_action(
    action_type: PlayerActionState,
    player_id: str,
    player_name: str | None,
    by: str,
    reason: str = "",
    *,
    steam_id: str | None = None,
):
    try:
        return save_player_action(
            action_type,
            player_id,
            player_name,
            by,
            reason,
            steam_id=steam_id,
        )
    except Exception as e:
        logger.exception(
            "Failed to record player action: %s %s", action_type, player_name
        )
        return False


def save_start_player_session(
    player_id: str,
    timestamp: float,
    server_name: str | None = None,
    server_number: int | None = None
):
    config = RconServerSettingsUserConfig.load_from_db()

    server_name = server_name or config.short_name

    if server_number is None:
        server_number = int(get_server_number())

    with enter_session() as sess:
        player = get_player(sess, player_id)
        if not player:
            logger.error(
                "Can't record player session for %s, player not found", player_id
            )
            return

        start_time = datetime.datetime.fromtimestamp(timestamp)
        already_saved = (
            sess.query(PlayerSession)
            .filter(PlayerSession.player == player)
            .filter(PlayerSession.start == start_time)
            .first()
        )

        if already_saved is not None:
            logger.info(
                f"Player session starting at {start_time} for player {player_id} already recorded, skipping..."
            )
            return

        sess.add(
            PlayerSession(
                player=player,
                start=start_time,
                server_name=server_name,
                server_number=server_number,
            )
        )
        logger.info(
            "Recorded player %s session start at %s",
            player_id,
            datetime.datetime.fromtimestamp(timestamp),
        )
        sess.commit()


def save_end_player_session(player_id: str, timestamp):
    with enter_session() as sess:
        player = get_player(sess, player_id)
        if not player:
            logger.error(
                "Can't record player session for %s, player not found", player_id
            )
            return

        last_session = (
            sess.query(PlayerSession)
            .filter(PlayerSession.player == player)
            .order_by(PlayerSession.created.desc())
            .first()
        )

        if last_session is None:
            logger.warning(
                "Can't record player session for %s, last session not found",
                player_id,
            )
            return

        if last_session.end:
            logger.warning(
                "Last session was already ended for %s. Creating a new one instead",
                player_id,
            )
            last_session = PlayerSession(
                player=player,
            )
        last_session.end = datetime.datetime.fromtimestamp(timestamp)
        logger.info("Recorded player %s session end at %s", player_id, last_session.end)
        sess.commit()


def add_flag_to_player(
    player_id: str,
    flag: str,
    comment: str | None = None,
    player_name: str | None = None,
    *,
    steam_id: str | None = None,
) -> tuple[PlayerProfileType, PlayerFlagType]:
    with enter_session() as sess:
        player = _get_set_player(
            sess,
            player_name=player_name,
            player_id=player_id,
            steam_id=steam_id,
        )
        exists = (
            sess.query(PlayerFlag)
            .filter(PlayerFlag.player_id_id == player.id, PlayerFlag.flag == flag)
            .all()
        )
        if exists:
            logger.warning("Flag already exists")
            raise HLLCommandFailedError("Flag already exists")
        new = PlayerFlag(flag=flag, comment=comment, player=player)
        sess.add(new)
        sess.commit()
        res = player.to_dict()
        return res, new.to_dict()


def remove_flag(
    flag_id: int | None = None,
    player_id: str | None = None,
    flag: str | None = None,
) -> tuple[PlayerProfileType, PlayerFlagType]:
    with enter_session() as sess:
        if isinstance(flag_id, int):
            exists = (
                sess.query(PlayerFlag)
                .filter(PlayerFlag.id == int(flag_id))
                .one_or_none()
            )
        else:
            exists = (
                sess.query(PlayerFlag)
                .filter(PlayerID.player_id == player_id)
                .filter(PlayerFlag.flag == flag)
                .one_or_none()
            )

        if not exists:
            logger.warning("Flag does not exists")
            raise HLLCommandFailedError("Flag does not exists")
        player = exists.player.to_dict()
        old_flag = exists.to_dict()
        sess.delete(exists)
        sess.commit()

    return player, old_flag


def get_player_messages(player_id: str) -> list[PlayerActionType]:
    with enter_session() as sess:
        player = sess.query(PlayerID).filter_by(player_id=player_id).one_or_none()
        actions: list[PlayerActionType] = []
        if player:
            actions = [
                action.to_dict()
                for action in player.received_actions
                if action.action_type == PlayerActionState.MESSAGE.value
            ]

        return actions


def get_player_comments(player_id: str) -> list[PlayerCommentType]:
    with enter_session() as sess:
        player = sess.query(PlayerID).filter_by(player_id=player_id).one()
        return [c.to_dict() for c in player.comments]


def post_player_comment(player_id: str, comment, user: str = "Bot"):
    with enter_session() as sess:
        player = sess.query(PlayerID).filter_by(player_id=player_id).one()
        player.comments.append(PlayerComment(content=comment, by=user))
        sess.commit()


if __name__ == "__main__":
    save_player("Achile5115", "76561198172574911")
    save_start_player_session("76561198172574911", datetime.datetime.now().timestamp())
    save_end_player_session(
        "76561198172574911",
        int(
            (datetime.datetime.now() + datetime.timedelta(minutes=30)).timestamp()
            * 1000
        ),
    )
    save_end_player_session(
        "76561198172574911",
        int(
            (datetime.datetime.now() + datetime.timedelta(minutes=30)).timestamp()
            * 1000
        ),
    )
    save_player("Second Achile5115", "76561198172574911")
    save_player("Dr.WeeD", "4242")
    save_player("Dr.WeeD2", "4242")
    save_player("Dr.WeeD3", "4242")
    save_player("Dr.WeeD4", "4242")
    save_player("Dr.WeeD5", "4242")
    save_player("Dr.WeeD6", "4242")
    save_player("test", "76561197984877751")
    save_start_player_session("4242", datetime.datetime.now().timestamp())
    save_end_player_session(
        "4242",
        int(
            (datetime.datetime.now() + datetime.timedelta(minutes=30)).timestamp()
            * 1000
        ),
    )
    save_end_player_session(
        "4242",
        int(
            (datetime.datetime.now() + datetime.timedelta(minutes=30)).timestamp()
            * 1000
        ),
    )

    import pprint

    pprint.pprint(get_players_by_appearance())

    add_flag_to_player("76561198156263725", "🐷")
