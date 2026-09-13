"""Private, bounded processing in the existing per-server routines runtime."""

import logging
import time
from copy import deepcopy

from sqlalchemy import select, text
from rcon.models import LeadershipMessage, LeadershipVote
from rcon.user_config.leadership_vote import LeadershipVoteUserConfig as Config
from rcon.utils import MapsHistory, get_server_number
from . import storage
from .storage import enter_session
from .domain import answer, event_time, private_chat, message, _normalize_team

logger = logging.getLogger(__name__)


def read_context(api):
    """Existing bulk caches only; never N individual player requests."""
    state = api.get_gamestate()
    history = MapsHistory().get_current_map() or {}
    now = time.time()
    layer = state["current_map"]["id"]
    start = history.get("start")
    if (
        not isinstance(start, (float, int))
        or start > now
        or history.get("end") is not None
        or history.get("name") != layer
    ):
        raise ValueError("No recorder-confirmed current round")
    detailed = api.get_detailed_players(compact=True)
    snapshot = api.get_raw_player_snapshot()
    captured = snapshot.get("captured_at", 0)
    if not 0 <= time.time() - captured <= 10:
        raise ValueError("Stale bulk player snapshot")
    players = list((detailed.get("players") or {}).values())
    ids = {str(p["player_id"]) for p in api.get_players(compact=True)}
    if detailed.get("fail_count") or ids != {str(p.get("player_id")) for p in players}:
        raise ValueError("Incomplete live roster")
    return {
        "round_id": f"{get_server_number()}:{layer}:{start}",
        "players": players,
        "captured_at": captured,
    }


def handle_answer(api, log):
    yes = answer(log.get("sub_content"))
    if yes is None or not Config.load_from_db().enabled:
        return False
    if not private_chat(log):
        return True
    try:
        context = read_context(api)
        player_id = str(log.get("player_id_1") or "")
        sender = next(
            (p for p in context["players"] if str(p.get("player_id")) == player_id), {}
        )
        if not sender or not private_chat(log, sender.get("team")):
            return True
        storage.ballot(
            int(get_server_number()),
            player_id,
            yes,
            event_time(log),
            context["players"],
            context["round_id"],
        )
    except Exception:
        logger.exception("Leadership answer could not be validated; no vote recorded")
    return True


def dispatch_one(api, server, context=None):
    """Durably mark every attempt before sending; ambiguous delivery is not retried."""
    with enter_session() as sess:
        storage.lock(sess, server)
        item = sess.scalar(
            select(LeadershipMessage)
            .where(
                LeadershipMessage.server_number == server,
                LeadershipMessage.status == "pending",
            )
            .order_by(LeadershipMessage.created_at, LeadershipMessage.id)
            .limit(1)
        )
        if not item:
            return False
        item.status = "sending"
        message_id = item.id
    with enter_session() as sess:
        storage.lock(sess, server)
        item = sess.get(LeadershipMessage, message_id)
        if item.status != "sending":
            return True
        vote = sess.get(LeadershipVote, item.vote_id) if item.vote_id else None
        now = time.time()
        recipient = next(
            (
                p
                for p in (context or {}).get("players", [])
                if str(p.get("player_id")) == item.player_id
            ),
            {},
        )
        allowed_phase = {
            "confirm": {"confirming"},
            "target": {"warning"},
            "warning": {"warning"},
            "invite": {"inviting", "active"},
            "ballot": {"inviting", "active"},
        }.get(item.purpose)
        if (
            not vote
            or not storage.valid_context(context, now)
            or context["round_id"] != vote.round_id
            or _normalize_team(recipient.get("team")) != vote.team
            or now - item.created_at > 180
            or (
                allowed_phase
                and (vote.status not in allowed_phase or now >= vote.payload["ends_at"])
            )
        ):
            item.status = "cancelled"
            return True
        if item.purpose in {"invite", "ballot"}:
            storage.validate_participants(
                vote, context["players"], storage.presence(sess, server), now
            )
            if not vote.payload["electorate"].get(item.player_id, {}).get("valid"):
                item.status = "cancelled"
                return True
        sent = False
        try:
            with api.without_retries():
                sent = api.message_player(item.player_id, item.body) is True
        except Exception:
            logger.exception("Private leadership notification failed")
        item.status = "sent" if sent else "failed"
        item.sent_at = time.time() if sent else None
        if sent:
            p = deepcopy(vote.payload)
            if item.purpose == "confirm":
                p["confirm_invited_at"] = item.sent_at
                p["ends_at"] = item.sent_at + p["rules"]["confirmation_seconds"]
            elif item.purpose == "invite":
                p["electorate"][item.player_id]["invited_at"] = item.sent_at
            elif item.purpose == "target":
                p["target_notified"] = True
                p["ends_at"] = item.sent_at + p["rules"]["warning_seconds"]
            vote.payload = p
            if item.purpose == "target":
                storage.notify(
                    sess,
                    server,
                    vote.reporter_id,
                    message(vote, "warning"),
                    item.sent_at,
                    vote,
                    "warning",
                )
            if item.purpose in {"target", "confirm"}:
                storage.publish(sess, vote, "delivery")
    return True


def execute(api, server, vote):
    """One non-retrying send per durable reservation. Offline is NOT kick proof."""
    confirmed = False
    send_started = False
    try:
        context = read_context(api)
        if storage.begin_send(server, vote["id"], context):
            send_started = True
            reason = (
                f"Führungsabstimmung / Leadership vote: {vote['yes']} Ja/yes; "
                f"nötig/required {vote['required']}. Kein Bann / no ban. [Vote {vote['id']}]"
            )
            with api.without_retries(), storage.automatic_action():
                confirmed = (
                    api.kick(
                        vote["target_id"],
                        reason,
                        by="system:leadership-vote",
                        player_name=vote["target_name"],
                    )
                    is True
                )
    except Exception:
        logger.exception("Leadership kick result uncertain; automatic retry prohibited")
    if send_started:
        storage.complete(server, vote["id"], confirmed)
    else:
        storage.abort_before_send(server, vote["id"])


def tick(api, server):
    context = None
    with enter_session() as sess:
        cfg = storage.config(sess, server)
        pending = sess.scalar(
            select(LeadershipMessage.id)
            .where(
                LeadershipMessage.server_number == server,
                LeadershipMessage.status == "pending",
            )
            .limit(1)
        )
    if cfg.enabled or pending:
        try:
            context = read_context(api)
        except Exception:
            logger.warning(
                "Leadership live context unavailable; fail closed", exc_info=True
            )
    storage.observe(server, context if cfg.enabled else None)
    for vote in storage.advance(server, context):
        execute(api, server, vote)
    for _ in range(8):
        if not dispatch_one(api, server, context):
            break


class Runtime:
    """Single owner for split/shared supervisor layouts; isolated five-second step."""

    def __init__(self):
        self.owner = None
        self.server = int(get_server_number())
        self.cleanup_at = 0

    def step(self, api):
        try:
            if self.owner is None:
                with enter_session() as probe:
                    engine = probe.bind
                self.owner = engine.connect()
                if self.owner.dialect.name == "postgresql":
                    acquired = self.owner.scalar(
                        text("SELECT pg_try_advisory_lock(194873, :server)"),
                        {"server": self.server},
                    )
                    self.owner.commit()
                    if not acquired:
                        self.close()
                        return
                storage.recover(self.server)
            self.owner.execute(text("SELECT 1"))
            self.owner.commit()
            tick(api, self.server)
            if time.time() >= self.cleanup_at:
                from rcon.incident_settings import incident_retention_days

                storage.cleanup(self.server, incident_retention_days())
                self.cleanup_at = time.time() + 3600
        except Exception:
            logger.exception("Leadership step failed; no automatic retry of actions")
            self.close()

    def close(self):
        owner, self.owner = self.owner, None
        if owner is not None:
            try:
                if owner.dialect.name == "postgresql" and not owner.invalidated:
                    owner.rollback()
                    owner.execute(
                        text("SELECT pg_advisory_unlock(194873, :server)"),
                        {"server": self.server},
                    )
                    owner.commit()
            except Exception:
                logger.exception(
                    "Leadership owner connection could not be released cleanly"
                )
                owner.invalidate()
            finally:
                owner.close()
