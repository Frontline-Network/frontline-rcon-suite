import logging
import os
import re
import sys
import uuid
from collections import defaultdict
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Generator, List, Literal, Optional, Sequence, overload

import pydantic
from sqlalchemy import (
    JSON,
    TIMESTAMP,
    CheckConstraint,
    Engine,
    Enum,
    ForeignKey,
    Index,
    NullPool,
    Pool,
    String,
    Text,
    create_engine,
    select,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.exc import InvalidRequestError, ProgrammingError
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    Session,
    mapped_column,
    object_session,
    relationship,
    sessionmaker,
)
from sqlalchemy.schema import UniqueConstraint

from rcon.maps import Team
from rcon.types import (
    AuditLogType,
    BlacklistRecordType,
    BlacklistRecordWithBlacklistType,
    BlacklistRecordWithPlayerType,
    BlacklistSyncMethod,
    BlacklistType,
    BlacklistWithRecordsType,
    DBLogLineType,
    GameIntEnum,
    GameLayout,
    GetDetailedPlayer,
    MapResult,
    MapScore,
    MapsType,
    MessageTemplateCategory,
    MessageTemplateType,
    PenaltyCountType,
    PlayerAccountType,
    PlayerActionState,
    PlayerActionType,
    PlayerAtCountType,
    PlayerCommentType,
    PlayerFlagType,
    PlayerNameType,
    PlayerOptinsType,
    PlayerProfileType,
    PlayerSessionType,
    PlayerSoldierType,
    PlayerStatsType,
    PlayerTeamAssociation,
    PlayerTeamConfidence,
    PlayerVIPType,
    ServerCountType,
    SteamBansType,
    SteamInfoType,
    SteamPlayerSummaryType,
    StructuredLogLineWithMetaData,
    UnitHistoryEntry,
    WatchListType,
)
from rcon.utils import (
    SafeStringFormat,
    get_server_number,
    humanize_timedelta,
    mask_to_server_numbers,
    server_numbers_to_mask,
)

logger = logging.getLogger(__name__)

PLAYER_ID = "player_id"

_ENGINE: Engine | None = None


def _connection_name() -> str:
    """
    Identify what application component is using the SQLAlchemy session. This can be helpful when inspecting the connections
    in Postgres to identify the purpose of a connection. The connection name will be used as the application_name connection
    property and show up in the pg_stat_activity table:
    select * from pg_stat_activity;

    :return: str
    """
    args = sys.argv
    name = "CRCon Generic"
    if "manage.py" not in args[0]:
        # stuff like daphne, gunicorn (backend) etc
        name = args[0]
    elif len(args) > 1 and args[1] != "":
        # Take whatever argument we passed to manage.py (for Supervisor services, such as log_loop, etc)
        name = args[1]

    name = (os.getenv("SERVER_NUMBER") or "") + name
    # in the standard build (which we use in teh default docker setup) the name cannot exceed 63 chars (less than 64),
    # see https://www.postgresql.org/docs/current/runtime-config-logging.html#GUC-APPLICATION-NAME
    return name[:63]


def get_engine():
    global _ENGINE

    if _ENGINE:
        return _ENGINE
    url = os.getenv("HLL_DB_URL")
    if not url:
        msg = "No $HLL_DB_URL specified. Can't use database features"
        logger.error(msg)
        raise ValueError(msg)

    pool: type[Pool] | None = None
    if os.getenv("HLL_DB_DISABLE_CONNECTION_POOL") is not None:
        pool = NullPool

    engine_options: dict[str, Any] = {
        "echo": False,
        "connect_args": {"application_name": _connection_name()},
    }
    if pool is not None:
        engine_options["poolclass"] = pool
    elif os.getenv("HLL_SUPERVISOR_PROCESS") is not None:
        # Supervisor commands are long-lived but overwhelmingly serial.  The
        # SQLAlchemy default (five persistent connections plus ten overflow
        # connections) is excessive when a host runs more than a dozen such
        # commands per gameserver.  Keep one warm connection for latency and
        # allow short bursts without retaining the overflow afterwards.
        engine_options.update(
            pool_size=max(1, int(os.getenv("HLL_DB_POOL_SIZE", "1"))),
            max_overflow=max(0, int(os.getenv("HLL_DB_MAX_OVERFLOW", "2"))),
            pool_recycle=max(60, int(os.getenv("HLL_DB_POOL_RECYCLE", "900"))),
            pool_use_lifo=True,
        )

    _ENGINE = create_engine(url, **engine_options)
    return _ENGINE


class Base(DeclarativeBase):
    # TODO: Replace dict[str, Any] w/ actual types
    type_annotation_map = {
        dict[str, Any]: JSONB,
        dict[str, int]: JSONB,
        SteamPlayerSummaryType: JSONB,
        SteamBansType: JSONB,
    }


class VipRewardState(Base):
    __tablename__ = "vip_reward_state"
    server_number: Mapped[int] = mapped_column(primary_key=True)
    preview: Mapped[bool] = mapped_column(primary_key=True)
    data: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)


class VipRewardEvent(Base):
    __tablename__ = "vip_reward_event"
    id: Mapped[int] = mapped_column(primary_key=True)
    server_number: Mapped[int] = mapped_column(index=True)
    key: Mapped[str] = mapped_column(String(64))
    preview: Mapped[bool]
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB)
    processed: Mapped[bool] = mapped_column(default=False, index=True)
    __table_args__ = (UniqueConstraint("server_number", "preview", "key"),)


class VipRewardGrant(Base):
    __tablename__ = "vip_reward_grant"
    id: Mapped[int] = mapped_column(primary_key=True)
    server_number: Mapped[int] = mapped_column(index=True)
    preview: Mapped[bool]
    player_id: Mapped[str] = mapped_column(String(100), index=True)
    rule: Mapped[str] = mapped_column(String(100))
    trigger: Mapped[str] = mapped_column(String(160))
    occurred: Mapped[float]
    requested_seconds: Mapped[float]
    credited_seconds: Mapped[float] = mapped_column(default=0)
    limit: Mapped[int] = mapped_column(default=0)
    status: Mapped[str] = mapped_column(String(32), default="queued", index=True)
    reason: Mapped[str] = mapped_column(Text, default="")
    target: Mapped[str | None] = mapped_column(String(64), nullable=True)
    description: Mapped[str] = mapped_column(Text, default="")
    written_at: Mapped[float | None] = mapped_column(nullable=True)
    __table_args__ = (UniqueConstraint("server_number", "preview", "player_id", "rule", "trigger"),)

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class SeedVipCycle(Base):
    """Persistent observation state for one server and execution mode."""

    __tablename__ = "seed_vip_cycle"
    server_number: Mapped[int] = mapped_column(primary_key=True)
    preview: Mapped[bool] = mapped_column(primary_key=True)
    generation: Mapped[int] = mapped_column(nullable=False, default=0)
    phase: Mapped[str] = mapped_column(String(16), nullable=False)
    eligible: Mapped[dict[str, str]] = mapped_column(JSONB, nullable=False, default=dict)
    seeded_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    __table_args__ = (
        CheckConstraint("phase IN ('uninitialized', 'seeding', 'seeded')", name="ck_seed_vip_cycle_phase"),
        CheckConstraint("generation >= 0", name="ck_seed_vip_cycle_generation"),
    )


class SeedVipGrant(Base):
    """One durable, independently recoverable seed reward."""

    __tablename__ = "seed_vip_grant"
    id: Mapped[int] = mapped_column(primary_key=True)
    server_number: Mapped[int] = mapped_column(nullable=False, index=True)
    preview: Mapped[bool] = mapped_column(nullable=False)
    generation: Mapped[int] = mapped_column(nullable=False)
    player_id: Mapped[str] = mapped_column(String(100), nullable=False)
    player_name: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    reward_seconds: Mapped[float] = mapped_column(nullable=False)
    cumulative: Mapped[bool] = mapped_column(nullable=False)
    reward_time: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    target: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    __table_args__ = (
        UniqueConstraint("server_number", "preview", "generation", "player_id", name="uq_seed_vip_grant_cycle_player"),
        CheckConstraint("status IN ('queued', 'prepared', 'confirmed', 'rejected', 'skipped', 'review', 'reviewed', 'preview')", name="ck_seed_vip_grant_status"),
        CheckConstraint("reward_seconds >= 0", name="ck_seed_vip_grant_reward_seconds"),
    )


class PlayerID(Base):
    __tablename__ = "steam_id_64"
    id: Mapped[int] = mapped_column(primary_key=True)
    player_id: Mapped[str] = mapped_column(
        "steam_id_64", nullable=False, index=True, unique=True
    )
    # # TODO: This is a temporary Steam ID column so that we can store the Steam ID somewhere for Vietnam servers.
    # This enables us in the future to retroactively merge the Vietnam and WW2 player data into a single player profile.
    steam_id: Mapped[str | None]
    created: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    names: Mapped[list["PlayerName"]] = relationship(
        back_populates="player",
        order_by="nullslast(desc(PlayerName.last_seen))",
    )
    # If you ever change the ordering of sessions make sure you change the playtime calc code
    sessions: Mapped[list["PlayerSession"]] = relationship(
        back_populates="player",
        order_by="desc(PlayerSession.created)",
    )
    received_actions: Mapped[list["PlayersAction"]] = relationship(
        back_populates="player",
        order_by="desc(PlayersAction.time)",
    )
    flags: Mapped[list["PlayerFlag"]] = relationship(back_populates="player")
    watchlist: Mapped["WatchList"] = relationship(back_populates="player")
    steaminfo: Mapped["SteamInfo"] = relationship(back_populates="player")
    comments: Mapped[list["PlayerComment"]] = relationship(back_populates="player")
    stats: Mapped["PlayerStats"] = relationship(back_populates="player")
    blacklists: Mapped[list["BlacklistRecord"]] = relationship(back_populates="player")

    vips: Mapped[list["PlayerVIP"]] = relationship(
        back_populates="player",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )
    optins: Mapped[list["PlayerOptins"]] = relationship(back_populates="player")
    account: Mapped["PlayerAccount"] = relationship(back_populates="player")
    soldier: Mapped["PlayerSoldier"] = relationship(back_populates="player")

    @property
    def server_number(self) -> int:
        return int(os.getenv("SERVER_NUMBER"))  # type: ignore

    @hybrid_property
    def vip(self) -> Optional["PlayerVIP"]:
        return (
            object_session(self)
            .query(PlayerVIP)  # type: ignore
            .filter(
                PlayerVIP.player_id_id == self.id,
                PlayerVIP.server_number == self.server_number,
            )
            .one_or_none()
        )

    def get_penalty_count(self) -> PenaltyCountType:
        counts = defaultdict(int)
        for action in self.received_actions:

            try:
                action = PlayerActionState[action.action_type]
                counts[action] += 1
            except KeyError:
                continue

        return {
            PlayerActionState.KICK.name: counts[PlayerActionState.KICK],
            PlayerActionState.PUNISH.name: counts[PlayerActionState.PUNISH],
            PlayerActionState.TEMPBAN.name: counts[PlayerActionState.TEMPBAN],
            PlayerActionState.PERMABAN.name: counts[PlayerActionState.PERMABAN],
        }

    def get_total_playtime_seconds(self) -> int:
        total = 0

        for i, s in enumerate(self.sessions):
            if not s.end and s.start and i == 0:
                total += (datetime.now() - s.start).total_seconds()
            elif s.end and s.start:
                total += (s.end - s.start).total_seconds()

        return int(total)

    def get_current_playtime_seconds(self) -> int:
        if self.sessions:
            if self.sessions[0].end:
                return 0
            start = self.sessions[0].start or self.sessions[0].created
            return int((datetime.now() - start).total_seconds())
        return 0

    def to_dict(
        self,
        limit_sessions=5,
        *,
        preloaded_vips: list["PlayerVIP"] | None = None,
    ) -> PlayerProfileType:
        this_server = int(get_server_number())
        blacklists = [record.to_dict() for record in self.blacklists]
        is_blacklisted = any(
            record["is_active"]
            for record in [
                b
                for b in blacklists
                if b["blacklist"]["servers"] is None
                or any(server == this_server for server in b["blacklist"]["servers"])
            ]
        )
        # ``vips`` is dynamic and cannot be eager-loaded. Bulk callers may
        # provide the rows fetched in one query; single-profile callers keep
        # the existing lazy behaviour.
        vip_rows = self.vips if preloaded_vips is None else preloaded_vips
        vips = [v.to_dict() for v in vip_rows]
        is_vip = any(vip["server_number"] == this_server for vip in vips)
        return {
            "id": self.id,
            PLAYER_ID: self.player_id,
            "steam_id": self.steam_id,
            "created": self.created,
            "names": [name.to_dict() for name in self.names],
            "sessions": [session.to_dict() for session in self.sessions][
                :limit_sessions
            ],
            "sessions_count": len(self.sessions),
            "total_playtime_seconds": self.get_total_playtime_seconds(),
            "current_playtime_seconds": self.get_current_playtime_seconds(),
            "received_actions": [action.to_dict() for action in self.received_actions],
            "penalty_count": self.get_penalty_count(),
            "blacklists": blacklists,
            "is_blacklisted": is_blacklisted,
            "flags": [f.to_dict() for f in (self.flags or [])],
            "watchlist": self.watchlist.to_dict() if self.watchlist else None,
            "is_watched": self.watchlist.is_watched if self.watchlist else False,
            "steaminfo": self.steaminfo.to_dict() if self.steaminfo else None,
            "vips": vips,
            "is_vip": is_vip,
            "soldier": self.soldier.to_dict(),
            "account": self.account.to_dict(),
        }

    def __str__(self) -> str:
        aka = " | ".join([n.name for n in self.names])
        return f"{self.player_id} {aka}"


class PlayerSoldier(Base):
    __tablename__ = "player_soldier"

    id: Mapped[int] = mapped_column(primary_key=True)
    player_id_id: Mapped[int] = mapped_column(
        "playersteamid_id",
        ForeignKey("steam_id_64.id"),
        nullable=False,
        index=True,
        unique=True,
    )
    player: Mapped["PlayerID"] = relationship(back_populates="soldier")
    eos_id: Mapped[str | None] = mapped_column()
    name: Mapped[str | None] = mapped_column()
    level: Mapped[int] = mapped_column(default=0)
    platform: Mapped[str | None] = mapped_column()
    clan_tag: Mapped[str | None] = mapped_column()

    updated: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(tz=timezone.utc),
        onupdate=lambda: datetime.now(tz=timezone.utc),
    )

    @classmethod
    def update(cls, player: GetDetailedPlayer):
        logger.debug("Updating soldier %s" % player["name"])
        with enter_session() as sess:
            # Retrieve the PlayerID instance to get its ID for foreign key reference
            player_id_stmt = select(PlayerID).where(
                PlayerID.player_id == player["player_id"]
            )
            player_id_record = sess.execute(player_id_stmt).scalars().one_or_none()

            if not player_id_record:
                # Handle case where PlayerID does not exist
                logger.exception(
                    "PlayerID not found for player_id: %s" % player["player_id"]
                )
                return

            player_id_fk = player_id_record.id

            # Query for existing PlayerSoldier
            profile_stmt = select(cls).where(
                cls.player_id_id == player_id_fk
            )  # Direct filter on FK; join optional here
            profile = sess.execute(profile_stmt).scalars().one_or_none()
            if not profile:
                # Create new instance
                profile = cls(player_id_id=player_id_fk)
                sess.add(profile)

            # Proceed with updates
            profile.eos_id = player["eos_id"]
            profile.name = player["name"]
            profile.platform = player["platform"]
            profile.clan_tag = player["clan_tag"]

            if player["level"] > profile.level:
                profile.level = player["level"]

            sess.commit()

    @classmethod
    def update_missing_fields(
        cls,
        sess: Session,
        player_id: str,
        eos_id: str | None = None,
        name: str | None = None,
        level: int = 0,
        platform: str | None = None,
        clan_tag: str | None = None,
    ) -> tuple[Optional["PlayerSoldier"], bool]:
        """
        Update NULL fields only in PlayerSoldier for the given player_id.
        Does not overwrite any existing non-null values.
        Returns the updated PlayerSoldier instance or None if PlayerID not found.
        """
        # Look up PlayerID
        player_db = (
            sess.execute(select(PlayerID).where(PlayerID.player_id == player_id))
            .scalars()
            .one_or_none()
        )
        if not player_db:
            return None, False

        # Look up or create PlayerSoldier
        soldier_db = (
            sess.execute(select(cls).where(cls.player_id_id == player_db.id))
            .scalars()
            .one_or_none()
        )
        if not soldier_db:
            soldier_db = cls(player_id_id=player_db.id)
            sess.add(soldier_db)

        # Update only None fields
        changed = False
        if soldier_db.eos_id is None and eos_id is not None:
            soldier_db.eos_id = eos_id
            changed = True
        if soldier_db.name is None and name is not None:
            soldier_db.name = name
            changed = True
        if soldier_db.level == 0 and level is not None:
            soldier_db.level = level
            changed = True
        if soldier_db.platform is None and platform is not None:
            soldier_db.platform = platform
            changed = True
        if soldier_db.clan_tag is None and clan_tag is not None:
            soldier_db.clan_tag = clan_tag
            changed = True

        if changed:
            sess.commit()

        return soldier_db, changed

    def to_dict(self) -> PlayerSoldierType:
        return {
            "eos_id": self.eos_id,
            "name": self.name,
            "level": self.level,
            "platform": self.platform,
            "clan_tag": self.clan_tag,
            "updated": self.updated,
        }


class PlayerAccount(Base):
    __tablename__ = "player_account"

    id: Mapped[int] = mapped_column(primary_key=True)
    player_id_id: Mapped[int] = mapped_column(
        "playersteamid_id",
        ForeignKey("steam_id_64.id"),
        nullable=False,
        index=True,
        unique=True,
    )
    player: Mapped["PlayerID"] = relationship(back_populates="account")
    name: Mapped[str | None] = mapped_column()
    discord_id: Mapped[str | None] = mapped_column()
    is_member: Mapped[bool] = mapped_column(default=False)
    # ISO 3166-1 alpha-2
    country: Mapped[str | None] = mapped_column(String(2))
    # ISO 639-1
    lang: Mapped[str] = mapped_column(String(2), default="en")

    updated: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(tz=timezone.utc),
        onupdate=lambda: datetime.now(tz=timezone.utc),
    )

    @classmethod
    def update_account(
        cls,
        sess: Session,
        player_id: str,
        name: str | None = None,
        discord_id: str | None = None,
        is_member: bool = False,
        country: str | None = None,
        lang: str = "en",
    ) -> Optional["PlayerAccount"]:
        """
        Update all fields in PlayerAccount for the given player_id.
        All fields can be updated, including setting them to null.
        Returns (updated PlayerAccount instance, changed flag) or None if PlayerID not found.
        """
        # Look up PlayerID
        player_db = (
            sess.execute(select(PlayerID).where(PlayerID.player_id == player_id))
            .scalars()
            .one_or_none()
        )
        if not player_db:
            return None

        # Look up or create PlayerAccount
        account_db = (
            sess.execute(select(cls).where(cls.player_id_id == player_db.id))
            .scalars()
            .one_or_none()
        )
        if not account_db:
            account_db = cls(player_id_id=player_db.id)
            sess.add(account_db)

        account_db.name = name
        account_db.discord_id = discord_id
        account_db.is_member = is_member
        account_db.country = country.upper() if country else None
        account_db.lang = lang.lower() if lang else "en"
        sess.commit()

        return account_db

    def to_dict(self) -> PlayerAccountType:
        return {
            "name": self.name,
            "discord_id": self.discord_id,
            "is_member": self.is_member,
            "country": self.country,
            "lang": self.lang,
            "updated": self.updated,
        }


class SteamInfo(Base):
    __tablename__ = "steam_info"

    id: Mapped[int] = mapped_column(primary_key=True)
    player_id_id: Mapped[int] = mapped_column(
        "playersteamid_id",
        ForeignKey("steam_id_64.id"),
        nullable=False,
        index=True,
        unique=True,
    )
    created: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated: Mapped[datetime] = mapped_column(onupdate=datetime.utcnow)
    profile: Mapped[SteamPlayerSummaryType] = mapped_column(default=JSONB.NULL)
    country: Mapped[str | None] = mapped_column(index=True)
    bans: Mapped[SteamBansType] = mapped_column(default=JSONB.NULL)

    player: Mapped[PlayerID] = relationship(back_populates="steaminfo")

    @property
    def has_bans(self):
        return any(
            self.bans.get(k)
            for k in [
                "VACBanned",
                "NumberOfVACBans",
                "DaysSinceLastBan",
                "NumberOfGameBans",
            ]
            if self.bans
        )

    def to_dict(self) -> SteamInfoType:
        return {
            "id": self.id,
            "created": self.created,
            "updated": self.updated,
            "profile": self.profile,
            "country": self.country if self.country else None,
            "bans": self.bans,
            "has_bans": self.has_bans,
        }


class WatchList(Base):
    __tablename__ = "player_watchlist"

    id: Mapped[int] = mapped_column(primary_key=True)
    modified: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    player_id_id: Mapped[int] = mapped_column(
        "playersteamid_id",
        ForeignKey("steam_id_64.id"),
        nullable=False,
        index=True,
        unique=True,
    )
    is_watched: Mapped[bool] = mapped_column(nullable=False)
    reason: Mapped[str] = mapped_column(default="")
    by: Mapped[str] = mapped_column()
    count: Mapped[int] = mapped_column(default=0)

    player: Mapped[PlayerID] = relationship(back_populates="watchlist")

    def to_dict(self) -> WatchListType:
        return {
            "id": self.id,
            "modified": self.modified,
            PLAYER_ID: self.player.player_id,
            "is_watched": self.is_watched,
            "reason": self.reason,
            "by": self.by,
            "count": self.count,
        }


class UserConfig(Base):
    __tablename__ = "user_config"

    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(unique=True, index=True)
    # TODO: Fix this on the UI settings branch once merged
    value: Mapped[dict[str, Any]] = mapped_column()


class PlayerFlag(Base):
    __tablename__ = "player_flags"
    __table_args__ = (
        UniqueConstraint("playersteamid_id", "flag", name="unique_flag_player_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    player_id_id: Mapped[int] = mapped_column(
        "playersteamid_id", ForeignKey("steam_id_64.id"), nullable=False, index=True
    )
    flag: Mapped[str] = mapped_column(nullable=False, index=True)
    comment: Mapped[str] = mapped_column(String, nullable=True)
    modified: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    player: Mapped[PlayerID] = relationship(back_populates="flags")

    def to_dict(self) -> PlayerFlagType:
        return {
            "id": self.id,
            "flag": self.flag,
            "comment": self.comment,
            "modified": self.modified,
        }


class PlayerOptins(Base):
    __tablename__ = "player_optins"
    __table_args__ = (
        UniqueConstraint(
            "playersteamid_id", "optin_name", name="unique_optins_player_id"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    player_id_id: Mapped[int] = mapped_column(
        "playersteamid_id", ForeignKey("steam_id_64.id"), nullable=False, index=True
    )
    optin_name: Mapped[str] = mapped_column(nullable=False, index=True)
    optin_value: Mapped[str] = mapped_column(nullable=True)
    modified: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    player: Mapped[PlayerID] = relationship(back_populates="optins")

    def to_dict(self) -> PlayerOptinsType:
        return {
            "id": self.id,
            "optin_name": self.optin_name,
            "optin_value": self.optin_value,
            "modified": self.modified,
        }


class PlayerName(Base):
    __tablename__ = "player_names"
    __table_args__ = (
        UniqueConstraint("playersteamid_id", "name", name="unique_name_steamid"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    player_id_id: Mapped[int] = mapped_column(
        "playersteamid_id", ForeignKey("steam_id_64.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(nullable=False)
    created: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    last_seen: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    player: Mapped[PlayerID] = relationship(back_populates="names")

    def to_dict(self) -> PlayerNameType:
        return {
            "id": self.id,
            "name": self.name,
            PLAYER_ID: self.player.player_id,
            "created": self.created,
            "last_seen": self.last_seen,
        }


class PlayerSession(Base):
    __tablename__ = "player_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    player_id_id: Mapped[int] = mapped_column(
        "playersteamid_id", ForeignKey("steam_id_64.id"), nullable=False, index=True
    )
    start: Mapped[datetime] = mapped_column()
    end: Mapped[datetime] = mapped_column()
    created: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    server_number: Mapped[int] = mapped_column()
    server_name: Mapped[str] = mapped_column()

    player: Mapped[PlayerID] = relationship(back_populates="sessions")

    def to_dict(self) -> PlayerSessionType:
        return {
            "id": self.id,
            PLAYER_ID: self.player.player_id,
            "start": self.start,
            "end": self.end,
            "created": self.created,
        }


class CampaignDelivery(Base):
    """Durable delivery state for one campaign in one player session."""

    __tablename__ = "campaign_deliveries"
    __table_args__ = (
        UniqueConstraint(
            "server_number",
            "campaign_id",
            "player_session_id",
            name="unique_campaign_delivery_session",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    server_number: Mapped[int] = mapped_column(nullable=False, index=True)
    campaign_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    player_id_id: Mapped[int] = mapped_column(
        ForeignKey("steam_id_64.id"), nullable=False, index=True
    )
    player_session_id: Mapped[int] = mapped_column(
        ForeignKey("player_sessions.id"), nullable=False, index=True
    )
    player_name: Mapped[str] = mapped_column(String, nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    attempt_count: Mapped[int] = mapped_column(nullable=False, default=0)
    eligible_at: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False, index=True)
    next_attempt_at: Mapped[datetime | None] = mapped_column(TIMESTAMP, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP, nullable=False, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP, nullable=False, default=datetime.utcnow
    )
    last_attempt_at: Mapped[datetime | None] = mapped_column(TIMESTAMP, nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(TIMESTAMP, nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)


class VipLifecycleDelivery(Base):
    """Persistent VIP lifecycle delivery for one player session."""

    __tablename__ = "vip_lifecycle_deliveries"
    __table_args__ = (
        UniqueConstraint(
            "server_family",
            "rule",
            "player_id_id",
            "status_fingerprint",
            name="unique_vip_lifecycle_status_delivery",
        ),
        UniqueConstraint(
            "server_number",
            "rule",
            "player_session_id",
            "test_mode",
            name="unique_vip_lifecycle_delivery_session",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    server_number: Mapped[int] = mapped_column(nullable=False, index=True)
    server_family: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    rule: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    player_id_id: Mapped[int] = mapped_column(
        ForeignKey("steam_id_64.id"), nullable=False, index=True
    )
    player_session_id: Mapped[int | None] = mapped_column(
        ForeignKey("player_sessions.id"), nullable=True, index=True
    )
    player_name: Mapped[str] = mapped_column(String, nullable=False)
    status_fingerprint: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True
    )
    message: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    attempt_count: Mapped[int] = mapped_column(nullable=False, default=0)
    test_mode: Mapped[bool] = mapped_column(nullable=False, default=False)
    status_checked_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    last_attempt_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    sent_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)


class PlayersAction(Base):
    __tablename__ = "players_actions"

    id: Mapped[int] = mapped_column(primary_key=True)
    action_type: Mapped[str] = mapped_column(nullable=False)
    player_id_id: Mapped[int] = mapped_column(
        "playersteamid_id", ForeignKey("steam_id_64.id"), nullable=False, index=True
    )
    reason: Mapped[str] = mapped_column()
    by: Mapped[str] = mapped_column()
    time: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    player: Mapped[PlayerID] = relationship(back_populates="received_actions")

    def to_dict(self) -> PlayerActionType:
        return {
            "action_type": self.action_type,
            "reason": self.reason,
            "by": self.by,
            "time": self.time,
        }


class LogLine(Base):
    __tablename__ = "log_lines"
    __table_args__ = (
        UniqueConstraint("event_time", "raw", name="unique_log_line"),
        Index("ix_log_lines_server_event_time", "server", "event_time"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    version: Mapped[int] = mapped_column(default=1)
    creation_time: Mapped[datetime] = mapped_column(TIMESTAMP, default=datetime.utcnow)
    event_time: Mapped[datetime] = mapped_column(nullable=False, index=True)
    type: Mapped[str] = mapped_column(nullable=True)
    player1_name: Mapped[str] = mapped_column(nullable=True)
    player1_player_id: Mapped[int] = mapped_column(
        "player1_steamid", ForeignKey("steam_id_64.id"), nullable=True, index=True
    )
    player2_name: Mapped[str] = mapped_column(nullable=True)
    player2_player_id: Mapped[int] = mapped_column(
        "player2_steamid", ForeignKey("steam_id_64.id"), nullable=True, index=True
    )
    weapon: Mapped[str] = mapped_column()
    raw: Mapped[str] = mapped_column(nullable=False)
    content: Mapped[str] = mapped_column()
    player_1: Mapped[PlayerID] = relationship(foreign_keys=[player1_player_id])
    player_2: Mapped[PlayerID] = relationship(foreign_keys=[player2_player_id])
    server: Mapped[str] = mapped_column()
    game: Mapped[int] = mapped_column(
        default=GameIntEnum.HLL_WW2.value, server_default=str(GameIntEnum.HLL_WW2.value)
    )

    def get_weapon(self) -> str | None:
        if self.weapon:
            return self.weapon
        # Backward compatibility for logs before weapon was added
        if self.type and self.type.lower() in ("kill", "team kill"):
            try:
                return self.raw.rsplit(" with ", 1)[-1]
            except:
                logger.exception("Unable to extract weapon")

        return None

    def to_dict(self) -> DBLogLineType:
        # TODO: Fix typing
        return {
            "id": self.id,
            "version": self.version,
            "creation_time": self.creation_time,
            "event_time": self.event_time,
            "type": self.type,
            "player1_name": self.player1_name,
            "player1_id": self.player_1.player_id if self.player_1 else None,
            "player2_name": self.player2_name,
            "player2_id": self.player_2.player_id if self.player_2 else None,
            "raw": self.raw,
            "content": self.content,
            "server": self.server,
            "weapon": self.get_weapon(),
        }

    def compatible_dict(self) -> StructuredLogLineWithMetaData:
        # TODO: Add typing
        return {
            "version": self.version,
            "timestamp_ms": int(self.event_time.timestamp() * 1000),
            "event_time": self.event_time,
            "relative_time_ms": None,  # TODO
            "raw": self.raw,
            "line_without_time": None,  # TODO
            "action": self.type,
            "player_name_1": self.player1_name,
            "player_id_1": self.player_1.player_id if self.player_1 else None,
            "player_name_2": self.player2_name,
            "player_id_2": self.player_2.player_id if self.player_2 else None,
            "weapon": self.get_weapon(),
            "message": self.content,
            "sub_content": None,  # TODO
        }


class Maps(Base):
    __tablename__ = "map_history"
    __table_args__ = (
        UniqueConstraint(
            "start", "end", "server_number", "map_name", name="unique_map"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    creation_time: Mapped[datetime] = mapped_column(TIMESTAMP, default=datetime.utcnow)
    start: Mapped[datetime] = mapped_column(nullable=False, index=True)
    end: Mapped[datetime] = mapped_column(index=True)
    server_number: Mapped[int] = mapped_column(index=True)
    map_name: Mapped[str] = mapped_column(nullable=False, index=True)
    # A dict with the result of the game mapped as Axis=int, Allied=int
    result: Mapped[dict[str, int]] = mapped_column(nullable=True)
    game_layout: Mapped["GameLayout"] = mapped_column(
        JSON, nullable=False, default=GameLayout
    )
    cap_flips: Mapped[list[MapScore]] = mapped_column(
        JSON, nullable=False, default=list
    )
    match_time: Mapped[int] = mapped_column(default=0)
    game: Mapped[int] = mapped_column(
        default=GameIntEnum.HLL_WW2.value, server_default=str(GameIntEnum.HLL_WW2.value)
    )

    player_stats: Mapped[list["PlayerStats"]] = relationship(back_populates="map")

    def to_dict(self, with_stats=False) -> MapsType:
        return {
            "id": self.id,
            "creation_time": self.creation_time,
            "start": self.start.replace(tzinfo=timezone.utc),
            "end": self.end.replace(tzinfo=timezone.utc),
            "server_number": self.server_number,
            "map_name": self.map_name,
            "result": (
                {
                    "axis": self.result.get("Axis", 0),
                    "allied": self.result.get("Allied", 0),
                }
                if self.result is not None and self.result.get("Allied") is not None
                else None
            ),
            "game_layout": self.game_layout,
            "cap_flips": self.cap_flips,
            "match_time": self.match_time,
            "player_stats": (
                []
                if not with_stats or not self.player_stats
                else [s.to_dict() for s in self.player_stats]
            ),
        }


def _stats_game_profile(game):
    # Import lazily: game profiles themselves import the shared models.
    from rcon.game.registry import get_game_profile
    from rcon.types import GameEnum

    try:
        game_id = GameIntEnum.HLL_WW2 if game is None else GameIntEnum(game)
        return get_game_profile(GameEnum[game_id.name])
    except (ValueError, KeyError, TypeError):
        return None


def calc_weapon_type_usage(weapons: dict[str, int], game=None) -> dict[str, int]:
    kills_by_type = defaultdict(int)
    profile = _stats_game_profile(game)
    catalog = profile.weapons if profile else {}

    for weapon_name, count in weapons.items():
        if weapon_name in catalog:
            weapon_type = catalog[weapon_name]
            kills_by_type[weapon_type.value] += count

    return dict(kills_by_type)


class PlayerStats(Base):
    __tablename__ = "player_stats"
    __table_args__ = (
        UniqueConstraint("playersteamid_id", "map_id", name="unique_map_player"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    player_id_id: Mapped[int] = mapped_column(
        "playersteamid_id", ForeignKey("steam_id_64.id"), nullable=False, index=True
    )
    map_id: Mapped[int] = mapped_column(
        ForeignKey("map_history.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column()
    kills: Mapped[int] = mapped_column()
    kills_streak: Mapped[int] = mapped_column()
    deaths: Mapped[int] = mapped_column()
    deaths_without_kill_streak: Mapped[int] = mapped_column()
    teamkills: Mapped[int] = mapped_column()
    teamkills_streak: Mapped[int] = mapped_column()
    deaths_by_tk: Mapped[int] = mapped_column()
    deaths_by_tk_streak: Mapped[int] = mapped_column()
    nb_vote_started: Mapped[int] = mapped_column()
    nb_voted_yes: Mapped[int] = mapped_column()
    nb_voted_no: Mapped[int] = mapped_column()
    time_seconds: Mapped[int] = mapped_column()
    kills_per_minute: Mapped[float] = mapped_column()
    deaths_per_minute: Mapped[float] = mapped_column()
    kill_death_ratio: Mapped[float] = mapped_column()
    longest_life_secs: Mapped[int] = mapped_column()
    shortest_life_secs: Mapped[int] = mapped_column()
    combat: Mapped[int] = mapped_column()
    offense: Mapped[int] = mapped_column()
    defense: Mapped[int] = mapped_column()
    support: Mapped[int] = mapped_column()
    vehicle_kills: Mapped[int] = mapped_column()
    vehicles_destroyed: Mapped[int] = mapped_column()
    most_killed: Mapped[dict[str, int]] = mapped_column()
    death_by: Mapped[dict[str, int]] = mapped_column()
    weapons: Mapped[dict[str, int]] = mapped_column()
    death_by_weapons: Mapped[dict[str, int]] = mapped_column()
    level: Mapped[int] = mapped_column()
    kills_and_assists: Mapped[int] = mapped_column()
    deaths_and_redeploys: Mapped[int] = mapped_column()
    units: Mapped[list[UnitHistoryEntry]] = mapped_column(JSON)

    player: Mapped[PlayerID] = relationship(
        foreign_keys=[player_id_id], back_populates="stats"
    )
    map: Mapped[Maps] = relationship(back_populates="player_stats")

    def detect_team(self) -> PlayerTeamAssociation:
        profile = _stats_game_profile(self.map.game if self.map else None)
        weapon_sides = profile.weapon_sides if profile else {}
        def get_value(item):
            return item[1]

        axis_count = 0
        allies_count = 0
        if len(self.weapons) > 0:
            for weapon in sorted(self.weapons.items(), key=get_value, reverse=True):
                if weapon_sides.get(weapon[0]) == Team.ALLIES:
                    allies_count += weapon[1]
                elif weapon_sides.get(weapon[0]) == Team.AXIS:
                    axis_count += weapon[1]

        if len(self.death_by_weapons) > 0:
            for weapon in sorted(
                self.death_by_weapons.items(), key=get_value, reverse=True
            ):
                if weapon_sides.get(weapon[0]) is None:
                    continue
                op = (
                    Team.AXIS
                    if weapon_sides.get(weapon[0]) == Team.ALLIES
                    else Team.ALLIES
                )
                if op == Team.ALLIES:
                    allies_count += weapon[1]
                elif op == Team.AXIS:
                    axis_count += weapon[1]

        assoc: PlayerTeamAssociation
        if axis_count == 0 and allies_count == 0:
            return PlayerTeamAssociation(
                side=Team.UNKNOWN, confidence=PlayerTeamConfidence.STRONG, ratio=0
            )
        elif axis_count > allies_count:
            assoc = PlayerTeamAssociation(
                side=Team.AXIS,
                confidence=PlayerTeamConfidence.MIXED,
                ratio=round(axis_count / (axis_count + allies_count) * 100, 2),
            )
        elif allies_count > axis_count:
            assoc = PlayerTeamAssociation(
                side=Team.ALLIES,
                confidence=PlayerTeamConfidence.MIXED,
                ratio=round(allies_count / (axis_count + allies_count) * 100, 2),
            )
        else:
            assoc = PlayerTeamAssociation(
                side=Team.UNKNOWN,
                confidence=PlayerTeamConfidence.MIXED,
                ratio=50,
            )
        assoc["confidence"] = (
            PlayerTeamConfidence.STRONG
            if assoc["ratio"] > 85
            else PlayerTeamConfidence.MIXED
        )
        return assoc

    def to_dict(self) -> PlayerStatsType:
        return {
            "id": self.id,
            PLAYER_ID: self.player.player_id,
            "player": self.name,
            "platform": (
                self.player.soldier.platform
                if self.player and self.player.soldier
                else None
            ),
            "steaminfo": (
                self.player.steaminfo.to_dict()
                if self.player and self.player.steaminfo
                else None
            ),
            "map_id": self.map_id,
            "kills": self.kills,
            "kills_by_type": calc_weapon_type_usage(self.weapons, self.map.game if self.map else None),
            "kills_streak": self.kills_streak,
            "deaths": self.deaths,
            "deaths_by_type": calc_weapon_type_usage(self.death_by_weapons, self.map.game if self.map else None),
            "deaths_without_kill_streak": self.deaths_without_kill_streak,
            "teamkills": self.teamkills,
            "teamkills_streak": self.teamkills_streak,
            "deaths_by_tk": self.deaths_by_tk,
            "deaths_by_tk_streak": self.deaths_by_tk_streak,
            "nb_vote_started": self.nb_vote_started,
            "nb_voted_yes": self.nb_voted_yes,
            "nb_voted_no": self.nb_voted_no,
            "time_seconds": self.time_seconds,
            "kills_per_minute": self.kills_per_minute,
            "deaths_per_minute": self.deaths_per_minute,
            "kill_death_ratio": self.kill_death_ratio,
            "longest_life_secs": self.longest_life_secs,
            "shortest_life_secs": self.shortest_life_secs,
            "combat": self.combat,
            "offense": self.offense,
            "defense": self.defense,
            "support": self.support,
            "vehicle_kills": self.vehicle_kills,
            "vehicles_destroyed": self.vehicles_destroyed,
            "most_killed": self.most_killed,
            "death_by": self.death_by,
            "weapons": self.weapons,
            "death_by_weapons": self.death_by_weapons,
            "team": self.detect_team(),
            "level": self.level,
            "kills_and_assists": self.kills_and_assists,
            "deaths_and_redeploys": self.deaths_and_redeploys,
            "units": self.units,
        }


class AutobalanceDecision(Base):
    """Append-friendly audit record for every autobalancer proposal and outcome."""

    __tablename__ = "autobalance_decisions"
    __table_args__ = (
        UniqueConstraint("decision_id", name="unique_autobalance_decision_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    decision_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    incident_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    server_number: Mapped[int] = mapped_column(nullable=False, index=True)
    round_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    round_started_at: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP, nullable=False, default=datetime.utcnow, index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP, nullable=False, default=datetime.utcnow
    )
    mode: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, index=True)
    source_team: Mapped[str] = mapped_column(String, nullable=False)
    target_team: Mapped[str] = mapped_column(String, nullable=False)
    player_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    player_name: Mapped[str | None] = mapped_column(String, nullable=True)
    volunteer: Mapped[bool] = mapped_column(nullable=False, default=False)
    protection_tier: Mapped[int | None] = mapped_column(nullable=True)
    rating: Mapped[float | None] = mapped_column(nullable=True)
    rating_confidence: Mapped[float | None] = mapped_column(nullable=True)
    rating_model_version: Mapped[str] = mapped_column(
        String, nullable=False, default="legacy"
    )
    strategy_version: Mapped[str] = mapped_column(
        String, nullable=False, default="legacy"
    )
    reason: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    before_snapshot: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict
    )
    after_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    approved_by: Mapped[str | None] = mapped_column(String, nullable=True)
    executed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP, nullable=True)
    review_verdict: Mapped[str | None] = mapped_column(String, nullable=True)
    review_category: Mapped[str | None] = mapped_column(String, nullable=True)
    review_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_by: Mapped[str | None] = mapped_column(String, nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP, nullable=True)
    review_preferred_strategy: Mapped[str | None] = mapped_column(String, nullable=True)
    review_preferred_player_id: Mapped[str | None] = mapped_column(
        String, nullable=True
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "incident_id": self.incident_id,
            "server_number": self.server_number,
            "round_id": self.round_id,
            "round_started_at": self.round_started_at,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "mode": self.mode,
            "status": self.status,
            "source_team": self.source_team,
            "target_team": self.target_team,
            "player_id": self.player_id,
            "player_name": self.player_name,
            "volunteer": self.volunteer,
            "protection_tier": self.protection_tier,
            "rating": self.rating,
            "rating_confidence": self.rating_confidence,
            "rating_model_version": self.rating_model_version,
            "strategy_version": self.strategy_version,
            "reason": self.reason,
            "before_snapshot": self.before_snapshot,
            "after_snapshot": self.after_snapshot,
            "approved_by": self.approved_by,
            "executed_at": self.executed_at,
            "review_verdict": self.review_verdict,
            "review_category": self.review_category,
            "review_comment": self.review_comment,
            "reviewed_by": self.reviewed_by,
            "reviewed_at": self.reviewed_at,
            "review_preferred_strategy": self.review_preferred_strategy,
            "review_preferred_player_id": self.review_preferred_player_id,
        }


class AutobalanceSnapshot(Base):
    """Durable, reviewable live team/squad evidence for future backtests."""

    __tablename__ = "autobalance_snapshots"
    __table_args__ = (
        UniqueConstraint(
            "server_number",
            "round_id",
            "captured_at",
            name="unique_autobalance_snapshot",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    server_number: Mapped[int] = mapped_column(nullable=False, index=True)
    round_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    captured_at: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False, index=True)
    map_name: Mapped[str] = mapped_column(String, nullable=False, index=True)
    map_elapsed_seconds: Mapped[int] = mapped_column(nullable=False)
    time_remaining_seconds: Mapped[int] = mapped_column(nullable=False)
    allies_count: Mapped[int] = mapped_column(nullable=False)
    axis_count: Mapped[int] = mapped_column(nullable=False)
    counts_match: Mapped[bool] = mapped_column(nullable=False)
    fail_count: Mapped[int] = mapped_column(nullable=False)
    stable_map: Mapped[bool] = mapped_column(nullable=False)
    rating_confidence: Mapped[float | None] = mapped_column(nullable=True)
    rating_model_version: Mapped[str] = mapped_column(
        String, nullable=False, default="legacy", index=True
    )
    players: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, nullable=False, default=list
    )


class AutobalancePlayerRoleStats(Base):
    """Exact role-aware score deltas derived from durable live snapshots."""

    __tablename__ = "autobalance_player_role_stats"
    __table_args__ = (
        UniqueConstraint(
            "server_number",
            "round_id",
            "player_id",
            "role_family",
            name="unique_autobalance_player_role_stats",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    server_number: Mapped[int] = mapped_column(nullable=False, index=True)
    round_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    map_name: Mapped[str] = mapped_column(String, nullable=False, index=True)
    player_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    role_family: Mapped[str] = mapped_column(String, nullable=False, index=True)
    first_seen: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False)
    last_seen: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False, index=True)
    time_seconds: Mapped[int] = mapped_column(nullable=False, default=0)
    kills: Mapped[int] = mapped_column(nullable=False, default=0)
    deaths: Mapped[int] = mapped_column(nullable=False, default=0)
    teamkills: Mapped[int] = mapped_column(nullable=False, default=0)
    combat: Mapped[int] = mapped_column(nullable=False, default=0)
    offense: Mapped[int] = mapped_column(nullable=False, default=0)
    defense: Mapped[int] = mapped_column(nullable=False, default=0)
    support: Mapped[int] = mapped_column(nullable=False, default=0)
    valid_intervals: Mapped[int] = mapped_column(nullable=False, default=0)
    ambiguous_intervals: Mapped[int] = mapped_column(nullable=False, default=0)
    invalid_intervals: Mapped[int] = mapped_column(nullable=False, default=0)
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP, nullable=False, default=datetime.utcnow
    )


class AutobalanceRoundAnalysis(Base):
    """Versioned cached aggregate derived from raw logs or exact snapshots."""

    __tablename__ = "autobalance_round_analyses"
    __table_args__ = (
        UniqueConstraint(
            "server_number",
            "map_id",
            "algorithm_version",
            "config_hash",
            name="unique_autobalance_round_analysis",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    server_number: Mapped[int] = mapped_column(nullable=False, index=True)
    map_id: Mapped[int] = mapped_column(
        ForeignKey("map_history.id"), nullable=False, index=True
    )
    algorithm_version: Mapped[str] = mapped_column(String, nullable=False, index=True)
    config_hash: Mapped[str] = mapped_column(String, nullable=False, index=True)
    analyzed_at: Mapped[datetime] = mapped_column(
        TIMESTAMP, nullable=False, default=datetime.utcnow, index=True
    )
    source: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, index=True)
    quality_score: Mapped[float] = mapped_column(nullable=False)
    analysis: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict
    )


class PlayerComment(Base):
    __tablename__ = "player_comments"
    id: Mapped[int] = mapped_column(primary_key=True)
    creation_time: Mapped[datetime] = mapped_column(TIMESTAMP, default=datetime.utcnow)
    by: Mapped[str] = mapped_column()
    player_id_id: Mapped[int] = mapped_column(
        "playersteamid_id", ForeignKey("steam_id_64.id"), nullable=False, index=True
    )
    content: Mapped[str] = mapped_column(nullable=False)

    player: Mapped[PlayerID] = relationship(back_populates="comments")

    def to_dict(self) -> PlayerCommentType:
        return {
            "id": self.id,
            "creation_time": self.creation_time,
            "player_id": self.player.player_id,
            "content": self.content,
            "by": self.by,
        }


class ServerCount(Base):
    __tablename__ = "server_counts"
    __table_args__ = (
        UniqueConstraint("server_number", "datapoint_time", name="unique_server_count"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    server_number: Mapped[int] = mapped_column()
    creation_time: Mapped[datetime] = mapped_column(TIMESTAMP, default=datetime.utcnow)
    datapoint_time: Mapped[datetime] = mapped_column(TIMESTAMP, unique=True, index=True)
    map_id: Mapped[int] = mapped_column(
        ForeignKey("map_history.id"), nullable=False, index=True
    )
    count: Mapped[int] = mapped_column(nullable=False)
    vip_count: Mapped[int] = mapped_column(nullable=False)
    players: Mapped["PlayerAtCount"] = relationship(back_populates="data_point")
    map: Mapped[Maps] = relationship(lazy="joined")

    def to_dict(self, players_as_tuple=False, with_player_list=True) -> ServerCountType:
        players = []

        if with_player_list and self.players:
            for p in self.players:
                p = p.to_dict()
                if players_as_tuple:
                    players.append((p["name"], p[PLAYER_ID], p["vip"]))
                else:
                    players.append(p)

        # TODO: Fix typing
        return {
            "server_number": self.server_number,
            "minute": self.datapoint_time,
            "count": self.count,
            "players": self.players,
            "map": self.map.map_name,
            "vip_count": self.vip_count,
        }


class PlayerAtCount(Base):
    __tablename__ = "player_at_count"
    __table_args__ = (
        UniqueConstraint(
            "playersteamid_id", "servercount_id", name="unique_player_at_count"
        ),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    player_id_id: Mapped[int] = mapped_column(
        "playersteamid_id", ForeignKey("steam_id_64.id"), nullable=False, index=True
    )
    servercount_id: Mapped[int] = mapped_column(
        ForeignKey("server_counts.id"), nullable=False, index=True
    )
    vip: Mapped[bool] = mapped_column()
    data_point: Mapped[ServerCount] = relationship(back_populates="players")
    player: Mapped[PlayerID] = relationship(lazy="joined")

    def to_dict(self) -> PlayerAtCountType:
        try:
            name = self.player.names[0].name
        except:
            logger.exception("Unable to load name for %s", self.player.player_id)
            name = ""

        return {
            PLAYER_ID: self.player.player_id,
            "name": name,
            "vip": self.vip,
        }


class PlayerVIP(Base):
    __tablename__: str = "player_vip"
    __table_args__ = (
        UniqueConstraint(
            "playersteamid_id", "server_number", name="unique_player_server_vip"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    expiration: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False
    )
    # Not making this unique (even though it should be) to avoid breaking existing CRCONs
    server_number: Mapped[int] = mapped_column()

    player_id_id: Mapped[int] = mapped_column(
        "playersteamid_id", ForeignKey("steam_id_64.id"), nullable=False, index=True
    )

    player: Mapped[PlayerID] = relationship(back_populates="vips")

    def to_dict(self) -> PlayerVIPType:
        return {
            "server_number": self.server_number,
            "expiration": self.expiration,
        }


class AuditLog(Base):
    __tablename__: str = "audit_log"
    __table_args__ = (Index("ix_audit_log_creation_time", "creation_time"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(nullable=False, index=True)
    creation_time: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=datetime.utcnow
    )
    # Not making this unique (even though it should be) to avoid breaking existing CRCONs
    command: Mapped[str] = mapped_column(nullable=False, index=True)
    command_arguments: Mapped[str] = mapped_column()
    command_result: Mapped[str] = mapped_column()

    def to_dict(self) -> AuditLogType:
        return {
            "id": self.id,
            "username": self.username,
            "creation_time": self.creation_time,
            "command": self.command,
            "command_arguments": self.command_arguments,
            "command_result": self.command_result,
        }


class LeadershipPresence(Base):
    """Observed leadership identity, invalidated on gaps, lifecycle events and restart."""
    __tablename__ = "leadership_presence"
    server_number: Mapped[int] = mapped_column(primary_key=True)
    player_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)


class LeadershipVote(Base):
    """One row per vote; JSON maps key electorate/ballots by stable player ID.

    All mutations hold the server advisory transaction lock. The unique live
    slot is a second, database-enforced guard against parallel team votes.
    """
    __tablename__ = "leadership_vote"
    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    server_number: Mapped[int] = mapped_column(index=True)
    team: Mapped[str] = mapped_column(String(16))
    target_id: Mapped[str] = mapped_column(String(100), index=True)
    reporter_id: Mapped[str] = mapped_column(String(100), index=True)
    round_id: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(24), index=True)
    slot: Mapped[str | None] = mapped_column(String(60), unique=True)
    created_at: Mapped[float]
    ended_at: Mapped[float | None]
    payload: Mapped[dict] = mapped_column(JSON, default=dict)


class LeadershipMessage(Base):
    __tablename__ = "leadership_message"
    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    server_number: Mapped[int] = mapped_column(index=True)
    vote_id: Mapped[str | None] = mapped_column(
        ForeignKey("leadership_vote.id", ondelete="CASCADE"), index=True
    )
    player_id: Mapped[str] = mapped_column(String(100))
    purpose: Mapped[str] = mapped_column(String(32))
    body: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16), default="pending", index=True)
    created_at: Mapped[float]
    sent_at: Mapped[float | None]


class AdminIncident(Base):
    """A durable, cross-server admin report used by the mobile incident inbox."""

    __tablename__ = "admin_incident"
    __table_args__ = (
        CheckConstraint(
            "source IN ('chat', 'manual', 'ai_chat', 'ai_player_name')",
            name="ck_admin_incident_source",
        ),
        CheckConstraint(
            "status IN ('new', 'claimed', 'resolved', 'dismissed')",
            name="ck_admin_incident_status",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    server_number: Mapped[int] = mapped_column(nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(16), nullable=False, default="manual")
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="new", index=True
    )
    reporter_id: Mapped[str | None] = mapped_column(String(100), index=True)
    reporter_name: Mapped[str | None] = mapped_column(String(255))
    reporter_context: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, default=dict
    )
    target_id: Mapped[str | None] = mapped_column(String(100), index=True)
    target_name: Mapped[str | None] = mapped_column(String(255))
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    raw_message: Mapped[str | None] = mapped_column(Text)
    leadership_vote_id: Mapped[str | None] = mapped_column(String(36), index=True)
    leadership_vote: Mapped[dict | None] = mapped_column(JSON)
    assigned_to: Mapped[str | None] = mapped_column(String(150), index=True)
    dedupe_key: Mapped[str | None] = mapped_column(String(64), index=True)
    revision: Mapped[int] = mapped_column(nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(tz=timezone.utc),
        index=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(tz=timezone.utc),
        onupdate=lambda: datetime.now(tz=timezone.utc),
        index=True,
    )
    resolved_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))

    events: Mapped[list["AdminIncidentEvent"]] = relationship(
        back_populates="incident",
        cascade="all, delete-orphan",
        order_by="AdminIncidentEvent.created_at",
    )
    subjects: Mapped[list["AdminIncidentSubject"]] = relationship(
        back_populates="incident",
        cascade="all, delete-orphan",
        order_by="AdminIncidentSubject.created_at",
    )

    def to_dict(self, include_events: bool = False) -> dict[str, Any]:
        result = {
            "id": self.id,
            "server_number": self.server_number,
            "source": self.source,
            "status": self.status,
            "reporter_id": self.reporter_id,
            "reporter_name": self.reporter_name,
            "reporter_context": self.reporter_context or {},
            "target_id": self.target_id,
            "target_name": self.target_name,
            "reason": self.reason,
            "raw_message": self.raw_message,
            "leadership_vote": self.leadership_vote,
            "report_admin": next((
                {k: v for k, v in event.payload.items() if k in {
                    "status", "mode", "rule", "target_id", "target_name", "result",
                    "teamkill_count", "teamkill_log_ids", "window_seconds", "updated_at", "sent_reason",
                    "assessment", "ready_at", "reason_analysis",
                }} for event in (self.events if include_events else ()) if event.event_type == "report_admin"
            ), None),
            "assigned_to": self.assigned_to,
            "revision": self.revision,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "resolved_at": self.resolved_at,
            "subjects": [subject.to_dict() for subject in self.subjects],
        }
        result["primary_subject"] = next(
            (
                subject.to_dict()
                for subject in self.subjects
                if subject.is_primary and subject.state == "confirmed"
            ),
            None,
        )
        if include_events:
            result["events"] = [event.to_dict() for event in self.events]
        return result


class AdminIncidentSubject(Base):
    """A player or squad mentioned by an admin incident report."""

    __tablename__ = "admin_incident_subject"
    __table_args__ = (
        CheckConstraint(
            "kind IN ('player', 'squad')", name="ck_admin_incident_subject_kind"
        ),
        CheckConstraint(
            "state IN ('suggested', 'confirmed', 'rejected')",
            name="ck_admin_incident_subject_state",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    incident_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("admin_incident.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    kind: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    state: Mapped[str] = mapped_column(
        String(16), nullable=False, default="suggested", index=True
    )
    is_primary: Mapped[bool] = mapped_column(nullable=False, default=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    player_id: Mapped[str | None] = mapped_column(String(100), index=True)
    team: Mapped[str | None] = mapped_column(String(100))
    squad_name: Mapped[str | None] = mapped_column(String(100))
    squad_id: Mapped[str | None] = mapped_column(String(100))
    squad_type: Mapped[str | None] = mapped_column(String(32))
    role: Mapped[str | None] = mapped_column(String(100))
    leader_player_id: Mapped[str | None] = mapped_column(String(100))
    leader_name: Mapped[str | None] = mapped_column(String(255))
    confidence: Mapped[float | None] = mapped_column()
    match_method: Mapped[str | None] = mapped_column(String(64))
    matched_text: Mapped[str | None] = mapped_column(String(255))
    parser_version: Mapped[str | None] = mapped_column(String(32))
    snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    confirmed_by: Mapped[str | None] = mapped_column(String(150))
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=lambda: datetime.now(tz=timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(tz=timezone.utc),
        onupdate=lambda: datetime.now(tz=timezone.utc),
    )

    incident: Mapped[AdminIncident] = relationship(back_populates="subjects")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "incident_id": self.incident_id,
            "kind": self.kind,
            "state": self.state,
            "is_primary": self.is_primary,
            "display_name": self.display_name,
            "player_id": self.player_id,
            "team": self.team,
            "squad_name": self.squad_name,
            "squad_id": self.squad_id,
            "squad_type": self.squad_type,
            "role": self.role,
            "leader_player_id": self.leader_player_id,
            "leader_name": self.leader_name,
            "confidence": self.confidence,
            "match_method": self.match_method,
            "matched_text": self.matched_text,
            "parser_version": self.parser_version,
            "snapshot": self.snapshot or {},
            "confirmed_by": self.confirmed_by,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class AdminIncidentEvent(Base):
    __tablename__ = "admin_incident_event"

    id: Mapped[int] = mapped_column(primary_key=True)
    incident_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("admin_incident.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    actor: Mapped[str] = mapped_column(String(150), nullable=False)
    event_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    idempotency_key: Mapped[str | None] = mapped_column(
        String(64), unique=True, index=True
    )
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(tz=timezone.utc),
        index=True,
    )

    incident: Mapped[AdminIncident] = relationship(back_populates="events")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "incident_id": self.incident_id,
            "actor": self.actor,
            "event_type": self.event_type,
            "idempotency_key": self.idempotency_key,
            "payload": self.payload,
            "created_at": self.created_at,
        }


class AdminIncidentPushDelivery(Base):
    """Local receipt for a privacy-preserving relay notification."""

    __tablename__ = "admin_incident_push_delivery"
    __table_args__ = (
        UniqueConstraint("event_id", "device_id", name="unique_push_event_device"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[int] = mapped_column(
        ForeignKey("admin_incident_event.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    device_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    delivered_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    error: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=lambda: datetime.now(tz=timezone.utc)
    )


class AdminIncidentDiscordDelivery(Base):
    """Durable outbox state for one event sent to the Frontline Discord service."""

    __tablename__ = "admin_incident_discord_delivery"

    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[int] = mapped_column(
        ForeignKey("admin_incident_event.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    attempts: Mapped[int] = mapped_column(nullable=False, default=0)
    next_attempt_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        default=lambda: datetime.now(tz=timezone.utc),
        index=True,
    )
    delivered_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), index=True
    )
    last_error: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=lambda: datetime.now(tz=timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(tz=timezone.utc),
        onupdate=lambda: datetime.now(tz=timezone.utc),
    )


class ModerationAnalysisRecord(Base):
    """Local analysis/audit record; shadow content never leaves this database."""

    __tablename__ = "moderation_analysis"
    __table_args__ = (
        CheckConstraint(
            "source IN ('report', 'ai_chat', 'ai_player_name')",
            name="ck_moderation_analysis_source",
        ),
        CheckConstraint(
            "visibility IN ('incident', 'shadow', 'ignore')",
            name="ck_moderation_analysis_visibility",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    incident_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("admin_incident.id", ondelete="CASCADE"), index=True
    )
    source: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    player_id: Mapped[str | None] = mapped_column(String(100), index=True)
    candidate_fingerprint: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True
    )
    # Candidate content is retained locally only and is purged after 30 days
    # for shadow/ignored results.  It is never included in service metrics.
    candidate_text: Mapped[str | None] = mapped_column(Text)
    analysis: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    visibility: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    model_version: Mapped[str] = mapped_column(String(100), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(64), nullable=False)
    policy_profile_id: Mapped[str] = mapped_column(String(64), nullable=False)
    policy_version: Mapped[str] = mapped_column(String(32), nullable=False)
    dedupe_until: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(tz=timezone.utc),
        index=True,
    )


class ModerationCandidateOutbox(Base):
    """Local-only candidate content and its reliable analysis job state."""

    __tablename__ = "moderation_candidate_outbox"
    __table_args__ = (
        CheckConstraint(
            "source IN ('ai_chat', 'ai_player_name')",
            name="ck_moderation_candidate_source",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    source: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    server_number: Mapped[int] = mapped_column(nullable=False, index=True)
    player_id: Mapped[str | None] = mapped_column(String(100), index=True)
    player_name: Mapped[str | None] = mapped_column(String(255))
    candidate_text: Mapped[str] = mapped_column(Text, nullable=False)
    candidate_fingerprint: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True
    )
    matched_rule_ids: Mapped[list[str]] = mapped_column(
        JSON, nullable=False, default=list
    )
    policy: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    shadow_only: Mapped[bool] = mapped_column(nullable=False, default=True)
    attempts: Mapped[int] = mapped_column(nullable=False, default=0)
    next_attempt_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        default=lambda: datetime.now(tz=timezone.utc),
        index=True,
    )
    delivered_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    analysis_received_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), index=True
    )
    last_error: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(tz=timezone.utc),
        index=True,
    )


class PlayerNameModerationState(Base):
    """Last name state checked for a stable player identity.

    This table stores only the normalized handle and evaluation versions. It is
    intentionally independent from 30-day moderation-content retention so an
    unchanged name never causes periodic AI calls.
    """

    __tablename__ = "player_name_moderation_state"

    player_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    normalized_name: Mapped[str] = mapped_column(String(255), nullable=False)
    model_version: Mapped[str] = mapped_column(String(100), nullable=False)
    policy_profile_id: Mapped[str] = mapped_column(String(64), nullable=False)
    policy_version: Mapped[str] = mapped_column(String(32), nullable=False)
    candidate_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    checked_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(tz=timezone.utc),
    )


class Blacklist(Base):
    __tablename__: str = "blacklist"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    sync: Mapped[BlacklistSyncMethod] = mapped_column(
        Enum(BlacklistSyncMethod), default=BlacklistSyncMethod.KICK_ONLY
    )
    servers: Mapped[Optional[int]]

    records: Mapped[list["BlacklistRecord"]] = relationship(
        back_populates="blacklist", cascade="all, delete"
    )

    def get_server_numbers(self) -> Optional[set[int]]:
        if self.servers is None:
            return None

        return mask_to_server_numbers(self.servers)

    def set_server_numbers(self, server_numbers: Sequence[int] | None):
        if server_numbers is None:
            self.set_all_servers()
        else:
            self.servers = server_numbers_to_mask(*server_numbers)

    def set_all_servers(self):
        self.servers = None

    @overload
    def to_dict(self, with_records: Literal[True]) -> BlacklistWithRecordsType: ...
    @overload
    def to_dict(self, with_records: Literal[False]) -> BlacklistType: ...
    @overload
    def to_dict(self, with_records: bool = False) -> BlacklistType: ...

    def to_dict(self, with_records: bool = False) -> BlacklistType:
        res = {
            "id": self.id,
            "name": self.name,
            "sync": self.sync.value,
            "servers": (
                None if self.servers is None else list(self.get_server_numbers())
            ),
        }
        if with_records:
            res["records"] = [
                record.to_dict(with_blacklist=False) for record in self.records
            ]
        return res


class BlacklistRecord(Base):
    __tablename__: str = "blacklist_record"
    id: Mapped[int] = mapped_column(primary_key=True)
    reason: Mapped[str]
    admin_name: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=lambda: datetime.now(tz=timezone.utc)
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True))

    player_id_id: Mapped[int] = mapped_column(
        ForeignKey("steam_id_64.id"), nullable=False, index=True
    )
    blacklist_id: Mapped[int] = mapped_column(
        ForeignKey("blacklist.id", ondelete="CASCADE"), nullable=False, index=True
    )

    player: Mapped["PlayerID"] = relationship(back_populates="blacklists")
    blacklist: Mapped["Blacklist"] = relationship(back_populates="records")

    def expires_in(self):
        if not self.expires_at:
            return None
        return self.expires_at - datetime.now(tz=timezone.utc)

    def is_expired(self):
        if not self.expires_at:
            return None
        return self.expires_at <= datetime.now(tz=timezone.utc)

    def get_formatted_reason(self):
        variables = {
            "player_id": self.player.player_id,
            "player_name": self.player.names[0].name if self.player.names else "",
            "banned_at": self.created_at.strftime("%b %d %Y %H:%M"),
            "banned_until": (
                self.expires_at.strftime("%b %d %Y %H:%M")
                if self.expires_at
                else "forever"
            ),
            "expires_at": (
                self.expires_at.strftime("%b %d %Y %H:%M")
                if self.expires_at
                else "never"
            ),
            "duration": (
                humanize_timedelta(self.expires_at - self.created_at)
                if self.expires_at
                else "forever"
            ),
            "expires": humanize_timedelta(self.expires_at).replace("forever", "never"),
            "ban_id": self.id,
            "admin_name": self.admin_name,
            "blacklist_name": self.blacklist.name,
        }
        try:
            return self.reason.format_map(SafeStringFormat(**variables))
        except (ValueError, AttributeError, IndexError, KeyError, TypeError):
            # Existing reasons may contain literal or malformed braces. Preserve
            # them rather than blocking enforcement or the entire list view.
            logger.warning("Invalid format in blacklist reason for record %s", self.id)
            return self.reason

    # I know this isn't entirely representative but I cba to add 4 different types, 3 is already more than enough
    @overload
    def to_dict(
        self, with_blacklist: Literal[True] = True, with_player: Literal[False] = False
    ) -> BlacklistRecordWithBlacklistType: ...
    @overload
    def to_dict(
        self, with_blacklist: Literal[True] = True, with_player: Literal[True] = False
    ) -> BlacklistRecordWithPlayerType: ...
    @overload
    def to_dict(
        self, with_blacklist: Literal[False] = True, with_player: bool = False
    ) -> BlacklistRecordType: ...

    def to_dict(
        self, with_blacklist: bool = True, with_player: bool = False
    ) -> BlacklistRecordWithBlacklistType:
        res = {
            "id": self.id,
            "player_id": self.player.player_id,
            "reason": self.reason,
            "admin_name": self.admin_name,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "is_active": not self.is_expired(),
        }

        if with_blacklist:
            res["blacklist"] = self.blacklist.to_dict(with_records=False)

        if with_player:
            res["player"] = {
                "id": self.player.id,
                "player_id": self.player.player_id,
                "created": self.player.created,
                "names": [name.to_dict() for name in self.player.names],
                "steaminfo": (
                    self.player.steaminfo.to_dict() if self.player.steaminfo else None
                ),
            }
            res["formatted_reason"] = self.get_formatted_reason()

        return res


def install_unaccent():
    with enter_session() as sess:
        sess.execute(text("CREATE EXTENSION IF NOT EXISTS unaccent;"))


def get_session_maker() -> sessionmaker:
    engine = get_engine()
    sess = sessionmaker()
    sess.configure(bind=engine)
    return sess


@contextmanager
def enter_session() -> Generator[Session, None, None]:
    session_maker = get_session_maker()

    try:
        sess: Session = session_maker()
        yield sess
        # Only commit if there were no exceptions, otherwise rollback
        sess.commit()
    except (ProgrammingError, InvalidRequestError) as e:
        logger.exception(e)
        sess.rollback()
    finally:
        sess.close()


# TODO: This probably belongs in rcon.types
class LogLineWebHookField(pydantic.BaseModel):
    """A Discord Webhook URL and optional roles to ping for log events and applicable servers

    LOG_LINE_WEBHOOKS in config.yml
    """

    url: str
    mentions: Optional[List[str]] = []
    servers: List[str] = []

    @pydantic.field_validator("mentions")
    def valid_role(cls, values):
        if not values:
            return []

        for role_or_user in values:
            if not re.search(r"<@&\d+>|<@\d+>", role_or_user):
                print(f"Invalid Discord role or user {role_or_user}")
                raise ValueError(f"Invalid Discord role {role_or_user}")

        return values


class MessageTemplate(Base):
    __tablename__ = "message_template"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column()
    content: Mapped[str]
    category: Mapped[MessageTemplateCategory] = mapped_column(
        Enum(MessageTemplateCategory)
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=datetime.utcnow
    )
    updated_by: Mapped[str]

    def to_dict(self) -> MessageTemplateType:
        return {
            "id": self.id,
            "title": self.title,
            "content": self.content,
            "category": self.category,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "updated_by": self.updated_by,
        }
