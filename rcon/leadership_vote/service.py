"""Private, bounded processing in the existing per-server routines runtime."""

import logging
import time
from copy import deepcopy

from sqlalchemy import select, text
from rcon.models import LeadershipMessage, LeadershipVote
from rcon.user_config.leadership_vote import LeadershipVoteUserConfig as Config
from rcon.utils import MapsHistory, get_server_number, parse_raw_player_info
from . import storage
from .storage import enter_session
from .domain import (
    INVITATIONS,
    answer,
    event_time,
    private_chat,
    message,
    _normalize_team,
)

logger = logging.getLogger(__name__)


def read_context(api):
    """One timestamped bulk roster, never a join of independently cached lists.

    The UI's detailed/player lists can describe different instants. Joining
    those lists during ordinary connects/disconnects reset every leader's
    tenure and cancelled votes even though their own seats had not changed.
    Adapt every row of the same bulk sample and fail closed on invalid rows.
    """
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
    snapshot = api.get_raw_player_snapshot()
    captured = snapshot.get("captured_at", 0)
    if not 0 <= time.time() - captured <= 10:
        raise ValueError("Stale bulk player snapshot")
    rows = snapshot.get("players")
    if not isinstance(rows, list):
        raise ValueError("Incomplete bulk player snapshot")
    players = [
        parse_raw_player_info(
            api.game_profile.player_adapter.adapt(row), api.config.game
        )
        for row in rows
    ]
    ids = [str(p.get("player_id") or "") for p in players]
    if not all(ids) or len(set(ids)) != len(ids):
        raise ValueError("Invalid or duplicate bulk player identity")
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
            "invite": {"inviting", "active"},
            "invite_de": {"inviting", "active"},
            "ballot": {"inviting", "active"},
        }.get(item.purpose)
        if (
            not vote
            or item.player_id == vote.target_id
            or item.purpose in {"target", "warning"}
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
        if item.purpose in INVITATIONS | {"ballot"}:
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
            elif item.purpose in INVITATIONS:
                member = p["electorate"][item.player_id]
                if member.get("invited_at") is None:
                    member["invited_at"] = item.sent_at
                member["last_invited_at"] = item.sent_at
            vote.payload = p
            if item.purpose == "confirm":
                storage.publish(sess, vote, "delivery")
        if item.purpose == "invite_de":
            # Commit the English follow-up with the German attempt's receipt.
            # It cannot overtake German or be enqueued twice. A failed language
            # is not retried; the other language still gets its single attempt.
            storage.notify(
                sess,
                server,
                item.player_id,
                message(vote, "invite"),
                time.time(),
                vote,
                "invite",
            )
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
