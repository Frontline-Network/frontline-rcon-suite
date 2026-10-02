"""Durable server-scoped voting; at most one non-retrying kick send.

All mutations and manual incident actions share a PostgreSQL transaction gate.
A send marker is committed before network I/O. Uncertain outcomes are never retried.
"""

import math
import time
import uuid
from copy import deepcopy
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime, timezone

from sqlalchemy import delete, select, text

from rcon.models import (
    AdminIncident,
    AdminIncidentEvent,
    LeadershipMessage,
    LeadershipPresence,
    LeadershipVote,
    UserConfig,
    get_session_maker,
)
from rcon.user_config.leadership_vote import LeadershipVoteUserConfig as Config
from rcon.user_config.utils import _invalidate_user_config_cache
from .domain import (
    OPEN,
    INVITATIONS,
    MAX_OBSERVATION_GAP,
    electorate,
    identity,
    may_report,
    message,
    report_command,
    squad_target,
)

_automatic_action = ContextVar("leadership_automatic_action", default=False)


@contextmanager
def automatic_action():
    token = _automatic_action.set(True)
    try:
        yield
    finally:
        _automatic_action.reset(token)


@contextmanager
def enter_session():
    # Unlike the legacy session helper, NEVER suppress a failed commit.
    with get_session_maker().begin() as sess:
        yield sess


def lock(sess, server):
    if sess.bind.dialect.name == "postgresql":
        sess.execute(
            text("SELECT pg_advisory_xact_lock(194872, :server)"),
            {"server": int(server)},
        )


def config_key(server):
    return f"{server}_LeadershipVoteUserConfig"


def config(sess, server):
    row = sess.scalar(select(UserConfig).where(UserConfig.key == config_key(server)))
    return Config.model_validate(row.value) if row else Config()


def command_conflicts(sess, server):
    conflicts = set()
    for row in sess.scalars(
        select(UserConfig).where(
            UserConfig.key.in_(
                [
                    f"{server}_ChatCommandsUserConfig",
                    f"{server}_RConChatCommandsUserConfig",
                    f"{server}_AutobalancerUserConfig",
                    f"{server}_VoteMapUserConfig",
                ]
            )
        )
    ):
        data = row.value
        if not data.get("enabled", False):
            continue
        words = list(data.get("describe_words") or [])
        for command in data.get("command_words") or []:
            if command.get("enabled", True):
                words.extend(command.get("words") or [])
        words.extend([data.get("volunteer_command", ""), data.get("command", "")])
        conflicts.update(
            str(w).strip().casefold()
            for w in words
            if str(w).strip().casefold() in {"!yes", "!no"}
        )
    return sorted(conflicts)


def discord_ready(sess):
    from rcon.incident_settings import discord_reports_enabled

    if not discord_reports_enabled():
        return False
    # Read metadata only; never load tokens into the workflow payload.
    row = (
        sess.execute(
            text(
                "SELECT enabled, service_url, channel_id, moderator_role_ids, "
                "(length(outbound_capability_ciphertext) > 0) AS paired "
                "FROM api_discordreportintegration WHERE id = 1"
            )
        )
        .mappings()
        .one_or_none()
    )
    return bool(
        row
        and row["enabled"]
        and row["service_url"]
        and row["paired"]
        and row["channel_id"]
        and row["moderator_role_ids"] not in (None, "", "[]", [])
    )


def report_delivered(sess, vote):
    from rcon.models import AdminIncidentDiscordDelivery

    return (
        sess.scalar(
            select(AdminIncidentDiscordDelivery.id)
            .join(
                AdminIncidentEvent,
                AdminIncidentEvent.id == AdminIncidentDiscordDelivery.event_id,
            )
            .join(AdminIncident, AdminIncident.id == AdminIncidentEvent.incident_id)
            .where(
                AdminIncident.leadership_vote_id == vote.id,
                AdminIncidentEvent.event_type == "created",
                AdminIncidentDiscordDelivery.delivered_at.is_not(None),
            )
            .limit(1)
        )
        is not None
    )


def presence(sess, server):
    return {
        r.player_id: r.payload
        for r in sess.scalars(
            select(LeadershipPresence).where(LeadershipPresence.server_number == server)
        )
    }


def observe(server, context, now=None):
    now = time.time() if now is None else now
    with enter_session() as sess:
        lock(sess, server)
        rows = {
            r.player_id: r
            for r in sess.scalars(
                select(LeadershipPresence).where(
                    LeadershipPresence.server_number == server
                )
            )
        }
        players = (context or {}).get("players", [])
        live = {}
        for player in players:
            ident = identity(player)
            if not ident:
                continue
            pid = str(player["player_id"])
            previous = rows.get(pid)
            data = previous.payload if previous else {}
            if (
                data.get("identity") != ident
                or data.get("round_id") != context["round_id"]
                or not 0 <= now - data.get("seen_at", 0) <= MAX_OBSERVATION_GAP
            ):
                data = dict(
                    identity=ident,
                    round_id=context["round_id"],
                    since=now,
                    token=str(uuid.uuid4()),
                )
            live[pid] = dict(data, seen_at=now)
            if previous:
                previous.payload = live[pid]
            else:
                sess.add(
                    LeadershipPresence(
                        server_number=server, player_id=pid, payload=live[pid]
                    )
                )
        for pid, row in rows.items():
            if pid not in live:
                sess.delete(row)


def summary(v):
    p = v.payload
    return dict(
        id=v.id,
        server_number=v.server_number,
        team=v.team,
        target_id=v.target_id,
        round_id=v.round_id,
        status=v.status,
        phase=v.status,
        mode=p["rules"]["mode"],
        created_at=v.created_at,
        ended_at=v.ended_at,
        **{
            k: p.get(k)
            for k in (
                "target_name",
                "target_role",
                "target_resolution",
                "squad",
                "reason",
                "rules",
                "started_at",
                "confirmed_at",
                "start_trigger",
                "ends_at",
                "required",
                "yes",
                "no",
                "result",
                "electorate",
                "ballots",
                "execution",
                "participant_count",
            )
        },
    )


def publish(sess, v, kind, actor="system:leadership-vote"):
    sess.flush()
    for incident in sess.scalars(
        select(AdminIncident).where(AdminIncident.leadership_vote_id == v.id)
    ):
        incident.leadership_vote = summary(v)
        incident.revision += 1
        incident.updated_at = datetime.fromtimestamp(time.time(), timezone.utc)
        incident.events.append(
            AdminIncidentEvent(
                actor=actor,
                event_type="leadership_vote_" + kind,
                payload={"vote": summary(v)},
            )
        )


def notify(sess, server, player_id, body, now, vote=None, purpose="feedback"):
    # No private vote notices to the reported player, including legacy results.
    if vote and str(player_id) == str(vote.target_id):
        return
    if purpose in {"target", "warning"}:
        return
    if player_id:
        sess.add(
            LeadershipMessage(
                server_number=server,
                vote_id=vote.id if vote else None,
                player_id=str(player_id),
                purpose=purpose,
                body=body,
                status="pending",
                created_at=now,
            )
        )


def outcome(v, de, en):
    return de + " / " + en


def recount(p):
    ballots = {
        pid: b
        for pid, b in p.get("ballots", {}).items()
        if p.get("electorate", {}).get(pid, {}).get("valid", False)
    }
    p["ballots"] = ballots
    p["yes"] = sum(b["yes"] for b in ballots.values())
    p["no"] = len(ballots) - p["yes"]


def finish(sess, v, status, result, now, actor="system:leadership-vote"):
    p = deepcopy(v.payload)
    p["result"] = result
    recount(p)
    v.payload, v.status, v.slot, v.ended_at = p, status, None, now
    for item in sess.scalars(
        select(LeadershipMessage).where(
            LeadershipMessage.vote_id == v.id,
            LeadershipMessage.status.in_({"pending", "sending"}),
        )
    ):
        item.status = "cancelled"
    recipients = {v.reporter_id}
    recipients |= {
        pid
        for pid, data in p.get("electorate", {}).items()
        if data.get("invited_at") is not None
    }
    for pid in recipients - {v.target_id}:
        notify(sess, v.server_number, pid, message(v, "result"), now, v, "result")
    if status == "kicked":
        for incident in sess.scalars(
            select(AdminIncident).where(AdminIncident.leadership_vote_id == v.id)
        ):
            incident.status = "resolved"
            incident.assigned_to = actor
            incident.resolved_at = datetime.fromtimestamp(now, timezone.utc)
    publish(sess, v, status, actor)


def valid_context(context, now):
    return bool(
        context
        and context.get("round_id")
        and 0 <= now - context.get("captured_at", 0) <= 10
    )


def target_current(v, players, observations, now):
    target = next((p for p in players if str(p.get("player_id")) == v.target_id), None)
    record = observations.get(v.target_id)
    return bool(
        target
        and record
        and unique_seat(v.payload["target_identity"], players)
        and identity(target) == v.payload["target_identity"]
        and record["identity"] == v.payload["target_identity"]
        and record["token"] == v.payload["target_token"]
        and 0 <= now - record["seen_at"] <= MAX_OBSERVATION_GAP
    )


def unique_seat(ident, players):
    return (
        sum(
            1
            for player in players
            if (current := identity(player))
            and all(current[key] == ident[key] for key in ("team", "kind", "squad_id"))
        )
        == 1
    )


def validate_participants(v, players, observations, now):
    by_id = {str(p.get("player_id")): p for p in players}
    p = deepcopy(v.payload)
    for pid, member in p["electorate"].items():
        record = observations.get(pid)
        if (
            not record
            or not unique_seat(member["identity"], players)
            or identity(by_id.get(pid)) != member["identity"]
            or record["identity"] != member["identity"]
            or record["token"] != member["token"]
            or not 0 <= now - record["seen_at"] <= MAX_OBSERVATION_GAP
        ):
            member["valid"] = False  # never revalidate after a transient role change
    recount(p)
    changed = p != v.payload
    v.payload = p
    return changed


def enqueue(sess, incident, context, now):
    server = incident.server_number
    lock(sess, server)
    cfg = config(sess, server)
    if (
        not cfg.enabled
        or command_conflicts(sess, server)
        or not report_command(incident.raw_message)
        or not discord_ready(sess)
    ):
        return
    if not context.get("private_chat") or not valid_context(context, now):
        return
    stamp = context.get("event_time")
    if stamp is None or not 0 <= now - stamp <= 30:
        return
    target = squad_target(
        [s.to_dict() for s in incident.subjects],
        incident.reporter_context,
        context["players"],
        incident.raw_message,
    )
    if not target or not may_report(context["players"], incident.reporter_id, target):
        return
    observations = {
        pid: record
        for pid, record in presence(sess, server).items()
        if record.get("round_id") == context["round_id"]
    }
    target_obs = observations.get(target["player_id"])
    if not target_obs or target_obs["identity"] != {
        k: target[k] for k in ("team", "role", "kind", "squad", "squad_id")
    }:
        return
    if not 0 <= now - target_obs.get("seen_at", 0) <= MAX_OBSERVATION_GAP:
        return
    roster = electorate(
        context["players"], target, observations, now, cfg.leadership_seconds
    )
    if len(roster) < cfg.minimum_participants:
        return
    recent = list(
        sess.scalars(
            select(LeadershipVote).where(
                LeadershipVote.server_number == server,
                (LeadershipVote.status.in_(OPEN))
                | (LeadershipVote.ended_at >= now - 86400),
            )
        )
    )
    if any(v.status in OPEN and v.team == target["team"] for v in recent):
        return
    if any(
        v.ended_at is not None
        and (
            v.payload.get("confirmed_at") is not None
            or v.payload.get("warning_started_at") is not None
        )
        and (
            (
                v.team == target["team"]
                and now - v.ended_at
                < max(cfg.team_gap_seconds, v.payload["rules"]["team_gap_seconds"])
            )
            or (
                v.target_id == target["player_id"]
                and now - v.ended_at
                < max(
                    cfg.target_cooldown_seconds,
                    v.payload["rules"]["target_cooldown_seconds"],
                )
            )
        )
        for v in recent
    ):
        return
    # Link the canonical current target only for an eligible vote, after all
    # gates. Preserve the original text and existing suggestions for admins.
    # This also keeps manual takeover/target-change guards and Discord actions
    # bound to the same player as the vote, including newly recognized aliases.
    from rcon.admin_incidents import _subject_from_payload, _sync_primary_target

    primary = next(
        (
            s
            for s in incident.subjects
            if s.state == "confirmed"
            and (s.player_id if s.kind == "player" else s.leader_player_id)
            == target["player_id"]
        ),
        None,
    )
    if primary is None:
        is_commander = target["kind"] == "commander"
        primary = _subject_from_payload(
            {
                "kind": "player" if is_commander else "squad",
                "state": "confirmed",
                "display_name": target["name"] if is_commander else target["squad"],
                "player_id": target["player_id"] if is_commander else None,
                "leader_player_id": None if is_commander else target["player_id"],
                "leader_name": None if is_commander else target["name"],
                "team": target["team"],
                "squad_name": target["squad"],
                "squad_id": target["squad_id"],
                "role": target["role"],
                "match_method": "leadership_reference",
                "parser_version": target["resolution"]["version"],
                "snapshot": {"leadership_resolution": target["resolution"]},
            },
            actor="system:leadership-vote",
        )
        incident.subjects.append(primary)
    for subject in incident.subjects:
        subject.is_primary = subject is primary
    _sync_primary_target(incident)
    v = LeadershipVote(
        server_number=server,
        team=target["team"],
        target_id=target["player_id"],
        reporter_id=incident.reporter_id,
        round_id=context["round_id"],
        status="inviting",
        slot=f"{server}:{target['team']}",
        created_at=now,
        payload={
            "target_name": target["name"],
            "target_role": target["kind"],
            "target_resolution": target["resolution"],
            "squad": target["squad"],
            "target_identity": target_obs["identity"],
            "target_token": target_obs["token"],
            "reason": incident.reason,
            "rules": cfg.model_dump(),
            "yes": 0,
            "no": 0,
            "ballots": {},
            "electorate": roster,
            # Historical cooldown marker retained for older clients. Starting
            # from a report does not cast a ballot on behalf of its reporter.
            "confirmed_at": now,
            "started_at": now,
            "start_trigger": "report",
            "ends_at": now + cfg.duration_seconds,
            "participant_count": len(roster),
            "required": cfg.required(len(roster)),
        },
    )
    sess.add(v)
    sess.flush()
    incident.leadership_vote_id = v.id
    for pid in roster:
        notify(sess, server, pid, message(v, "invite_de"), now, v, "invite_de")
    publish(sess, v, "inviting")


def start(sess, v, players, now):
    cfg = Config.model_validate(v.payload["rules"])
    observations = presence(sess, v.server_number)
    if not target_current(v, players, observations, now) or not report_delivered(
        sess, v
    ):
        return False
    target = dict(v.payload["target_identity"], player_id=v.target_id)
    roster = electorate(players, target, observations, now, cfg.leadership_seconds)
    if (
        not may_report(players, v.reporter_id, target)
        or len(roster) < cfg.minimum_participants
    ):
        return False
    p = deepcopy(v.payload)
    p.update(
        electorate=roster,
        participant_count=len(roster),
        required=cfg.required(len(roster)),
        confirmed_at=now,
        started_at=now,
        ends_at=now + cfg.duration_seconds,
    )
    v.payload, v.status = p, "inviting"
    for pid in roster:
        notify(sess, v.server_number, pid, message(v, "invite_de"), now, v, "invite_de")
    publish(sess, v, "inviting")
    return True


def ballot(server, player_id, yes, stamp, players, round_id, now=None):
    now = time.time() if now is None else now
    if stamp is None or not 0 <= now - stamp <= 30:
        return False
    with enter_session() as sess:
        lock(sess, server)
        if not config(sess, server).enabled or command_conflicts(sess, server):
            return False
        observations = presence(sess, server)
        for v in sess.scalars(
            select(LeadershipVote).where(
                LeadershipVote.server_number == server, LeadershipVote.status.in_(OPEN)
            )
        ):
            if (
                v.status == "executing"
                or v.round_id != round_id
                or now >= v.payload["ends_at"]
            ):
                continue
            if not target_current(v, players, observations, now):
                continue
            p = deepcopy(v.payload)
            if v.status == "confirming" and player_id == v.reporter_id:
                invitation = p.get("confirm_invited_at")
                if invitation is None or stamp < invitation:
                    continue
                if not yes:
                    finish(
                        sess, v, "cancelled", "Melder lehnt ab / Reporter declined", now
                    )
                elif not start(sess, v, players, now):
                    finish(
                        sess,
                        v,
                        "cancelled",
                        "Berechtigung geändert / Eligibility changed",
                        now,
                    )
                return True
            if v.status not in {"inviting", "active"}:
                continue
            validate_participants(v, players, observations, now)
            p = deepcopy(v.payload)
            member = p["electorate"].get(player_id, {})
            invitation = member.get("invited_at")
            previous = p["ballots"].get(player_id)
            if (
                not member.get("valid")
                or invitation is None
                or not invitation <= stamp < p["ends_at"]
                or (previous and stamp <= previous["time"])
            ):
                continue
            p["ballots"][player_id] = {"yes": yes, "time": stamp}
            recount(p)
            v.payload = p
            publish(sess, v, "ballot", actor=f"player:{player_id}")
            notify(sess, server, player_id, message(v, "ballot", yes), now, v, "ballot")
            return True
    return False


def cancel_linked(sess, incident, actor, now=None):
    if not incident.leadership_vote_id:
        return
    v = sess.get(LeadershipVote, incident.leadership_vote_id)
    if not v:
        return
    if (
        v.status == "executing"
        and v.payload.get("execution", {}).get("send_started_at") is not None
    ):
        from rcon.admin_incidents import IncidentConflict

        raise IncidentConflict("Kick send already started; wait for its result")
    if v.status in OPEN:
        finish(
            sess,
            v,
            "cancelled",
            "Von Admin übernommen / Taken over by admin",
            time.time() if now is None else now,
            actor,
        )


def lock_incident(sess, incident_id):
    server = sess.scalar(
        select(AdminIncident.server_number).where(AdminIncident.id == incident_id)
    )
    if server is not None:
        lock(sess, server)


def before_manual_action(player_id, actor="admin", *, all_targets=False):
    """Also protect direct web/RCON moderation, not only Discord report actions."""
    if _automatic_action.get() or not Config.load_from_db().enabled:
        return
    from rcon.utils import get_server_number

    server = int(get_server_number())
    with enter_session() as sess:
        lock(sess, server)
        for v in sess.scalars(
            select(LeadershipVote).where(
                LeadershipVote.server_number == server,
                True if all_targets else LeadershipVote.target_id == str(player_id),
                LeadershipVote.status.in_(OPEN),
            )
        ):
            if v.payload.get("execution", {}).get("send_started_at") is not None:
                from rcon.admin_incidents import IncidentConflict

                raise IncidentConflict(
                    "Leadership kick send already started; wait for its result"
                )
            finish(
                sess,
                v,
                "cancelled",
                "Manuelle Maßnahme / Manual action",
                time.time(),
                actor or "admin",
            )


def guard_command_config(sess, key, value):
    server, _, name = key.partition("_")
    if not server.isdigit() or name not in {
        "ChatCommandsUserConfig",
        "RConChatCommandsUserConfig",
        "AutobalancerUserConfig",
    }:
        return
    lock(sess, int(server))
    if not config(sess, int(server)).enabled or not value.get("enabled", False):
        return
    words = list(value.get("describe_words") or []) + [
        value.get("volunteer_command", "")
    ]
    for command in value.get("command_words") or []:
        if command.get("enabled", True):
            words.extend(command.get("words") or [])
    if any(str(word).strip().casefold() in {"!yes", "!no"} for word in words):
        raise ValueError(
            "!yes / !no sind für Führungsabstimmungen reserviert / reserved for leadership voting"
        )


def configure(server, cfg, actor):
    with enter_session() as sess:
        lock(sess, server)
        if cfg.enabled and (conflicts := command_conflicts(sess, server)):
            raise ValueError(
                "Chatbefehls-Konflikt / Command conflict: " + ", ".join(conflicts)
            )
        if cfg.enabled and not discord_ready(sess):
            raise ValueError(
                "Discord-Report-Bot muss verbunden und aktiviert sein / Connect and enable the Discord report bot first"
            )
        previous = config(sess, server)
        row = sess.scalar(
            select(UserConfig).where(UserConfig.key == config_key(server))
        )
        if row:
            row.value = cfg.model_dump()
        else:
            sess.add(UserConfig(key=config_key(server), value=cfg.model_dump()))
        if previous != cfg:
            for v in sess.scalars(
                select(LeadershipVote).where(
                    LeadershipVote.server_number == server,
                    LeadershipVote.status.in_(OPEN),
                )
            ):
                if v.payload.get("execution", {}).get("send_started_at") is not None:
                    from rcon.admin_incidents import IncidentConflict

                    raise IncidentConflict(
                        "Kick send already started; wait for its result"
                    )
                finish(
                    sess,
                    v,
                    "cancelled",
                    "Konfiguration geändert / Configuration changed",
                    time.time(),
                    actor,
                )
            if not previous.enabled or not cfg.enabled:
                sess.execute(
                    delete(LeadershipPresence).where(
                        LeadershipPresence.server_number == server
                    )
                )
    _invalidate_user_config_cache(config_key(server))


def cancel(server, vote_id, actor):
    with enter_session() as sess:
        lock(sess, server)
        v = sess.get(LeadershipVote, vote_id)
        if not v or v.server_number != server:
            raise LookupError("Vote not found on this server")
        incident = sess.scalar(
            select(AdminIncident).where(AdminIncident.leadership_vote_id == v.id)
        )
        if incident:
            cancel_linked(sess, incident, actor)
        return summary(v)


def end_for_event(server, stamp, player_id=None):
    if stamp is None:
        return
    with enter_session() as sess:
        lock(sess, server)
        rows = sess.scalars(
            select(LeadershipPresence).where(LeadershipPresence.server_number == server)
        )
        for row in list(rows):
            if (
                player_id is None or row.player_id == player_id
            ) and stamp >= math.floor(row.payload["since"]):
                sess.delete(row)
        for v in sess.scalars(
            select(LeadershipVote).where(
                LeadershipVote.server_number == server, LeadershipVote.status.in_(OPEN)
            )
        ):
            if (
                stamp < math.floor(v.created_at)
                or v.payload.get("execution", {}).get("send_started_at") is not None
            ):
                continue
            if player_id is None or v.target_id == player_id:
                finish(
                    sess,
                    v,
                    "cancelled",
                    "Runde/Verbindung geändert / Round or connection changed",
                    time.time(),
                )
            elif player_id in v.payload["electorate"]:
                p = deepcopy(v.payload)
                p["electorate"][player_id]["valid"] = False
                recount(p)
                v.payload = p
                publish(sess, v, "ballot")


def recover(server, now=None):
    now = time.time() if now is None else now
    with enter_session() as sess:
        lock(sess, server)
        sess.execute(
            delete(LeadershipPresence).where(LeadershipPresence.server_number == server)
        )
        for v in sess.scalars(
            select(LeadershipVote).where(
                LeadershipVote.server_number == server, LeadershipVote.status.in_(OPEN)
            )
        ):
            unknown = v.payload.get("execution", {}).get("send_started_at") is not None
            if unknown and confirmed_audit(sess, v):
                finish(
                    sess,
                    v,
                    "kicked",
                    "Kick-Audit bestätigt / Kick audit confirmed",
                    now,
                )
            else:
                finish(
                    sess,
                    v,
                    "unknown" if unknown else "cancelled",
                    "Neustart: manuell prüfen, keine Wiederholung / Restart: manual review, no retry",
                    now,
                )
        for m in sess.scalars(
            select(LeadershipMessage).where(
                LeadershipMessage.server_number == server,
                LeadershipMessage.status == "sending",
            )
        ):
            m.status = "unknown"


def confirmed_audit(sess, vote):
    from rcon.models import PlayerID, PlayersAction

    return (
        sess.scalar(
            select(PlayersAction.id)
            .join(PlayerID, PlayerID.id == PlayersAction.player_id_id)
            .where(
                PlayerID.player_id == vote.target_id,
                PlayersAction.action_type == "KICK",
                PlayersAction.by == "system:leadership-vote",
                PlayersAction.reason.contains(f"[Vote {vote.id}]"),
                PlayersAction.time
                >= datetime.fromtimestamp(
                    vote.payload["execution"]["reserved_at"], timezone.utc
                ).replace(tzinfo=None),
            )
            .limit(1)
        )
        is not None
    )


def advance(server, context=None, now=None):
    now = time.time() if now is None else now
    executions = []
    with enter_session() as sess:
        lock(sess, server)
        cfg = config(sess, server)
        observations = presence(sess, server)
        for v in sess.scalars(
            select(LeadershipVote).where(
                LeadershipVote.server_number == server, LeadershipVote.status.in_(OPEN)
            )
        ):
            if v.status == "executing":
                continue
            if (
                not cfg.enabled
                or command_conflicts(sess, server)
                or not discord_ready(sess)
                or not valid_context(context, now)
                or context["round_id"] != v.round_id
                or not target_current(v, context["players"], observations, now)
            ):
                finish(
                    sess,
                    v,
                    "cancelled",
                    "Ziel oder Live-Daten nicht mehr gültig / Target or live data no longer valid",
                    now,
                )
                continue
            if v.status == "confirming":
                if now >= v.payload["ends_at"]:
                    finish(
                        sess,
                        v,
                        "cancelled",
                        "Bestätigung abgelaufen / Confirmation expired",
                        now,
                    )
                continue
            if validate_participants(v, context["players"], observations, now):
                publish(sess, v, "ballot")
            p = deepcopy(v.payload)
            if (
                sum(e["valid"] for e in p["electorate"].values())
                < p["rules"]["minimum_participants"]
            ):
                finish(
                    sess,
                    v,
                    "cancelled",
                    "Zu wenige Berechtigte / Too few eligible leaders",
                    now,
                )
                continue
            reports = list(
                sess.scalars(
                    select(AdminIncident).where(
                        AdminIncident.leadership_vote_id == v.id
                    )
                )
            )
            if not reports or any(
                i.status != "new" or i.assigned_to or i.target_id != v.target_id
                for i in reports
            ):
                finish(
                    sess,
                    v,
                    "cancelled",
                    "Admin-Bearbeitung oder Zieländerung / Admin handling or target changed",
                    now,
                )
                continue
            if v.status == "warning":
                # Do not resume a procedure created under the old warning rules.
                finish(
                    sess,
                    v,
                    "cancelled",
                    "Ablauf aktualisiert; Admin-Prüfung nötig / Workflow updated; admin review required",
                    now,
                )
                continue
            if v.status == "inviting":
                # Admins must receive the original report before invitations.
                if not report_delivered(sess, v):
                    if now >= p["ends_at"]:
                        finish(
                            sess,
                            v,
                            "cancelled",
                            "Admin-Report nicht zugestellt / Admin report not delivered",
                            now,
                        )
                    continue
                pending = sess.scalar(
                    select(LeadershipMessage.id)
                    .where(
                        LeadershipMessage.vote_id == v.id,
                        LeadershipMessage.purpose.in_(INVITATIONS),
                        LeadershipMessage.status.in_({"pending", "sending"}),
                    )
                    .limit(1)
                )
                if not pending:
                    delivered = sum(
                        m["valid"] and m.get("invited_at") is not None
                        for m in p["electorate"].values()
                    )
                    if delivered < max(
                        p["required"], p["rules"]["minimum_participants"]
                    ):
                        finish(
                            sess,
                            v,
                            "cancelled",
                            "Einladungen nicht ausreichend zugestellt / Insufficient invitation delivery",
                            now,
                        )
                        continue
                    v.status = "active"
                    # Every invitee gets a full voting period after delivery.
                    p["ends_at"] = (
                        max(
                            m.get("last_invited_at") or m["invited_at"]
                            for m in p["electorate"].values()
                            if m.get("invited_at") is not None
                        )
                        + p["rules"]["duration_seconds"]
                    )
                    v.payload = p
                    publish(sess, v, "active")
            if now < p["ends_at"]:
                continue
            if v.status != "active":
                finish(
                    sess,
                    v,
                    "cancelled",
                    "Zustellung unvollständig / Delivery incomplete",
                    now,
                )
            elif p["yes"] < p["required"]:
                finish(
                    sess,
                    v,
                    "rejected",
                    "Mehrheit fehlt – Admins übernehmen / No majority – admins take over",
                    now,
                )
            elif p["rules"]["mode"] == "dry_run":
                finish(
                    sess,
                    v,
                    "dry_run",
                    "Probelauf: Mehrheit erreicht, kein Kick / Dry run: majority reached, no kick",
                    now,
                )
            else:
                p["execution"] = {"reserved_at": now, "confirmed": False}
                v.payload, v.status = p, "executing"
                publish(sess, v, "executing")
                executions.append(summary(v))
    return executions


def abort_before_send(server, vote_id):
    with enter_session() as sess:
        lock(sess, server)
        v = sess.get(LeadershipVote, vote_id)
        if (
            v
            and v.server_number == server
            and v.status == "executing"
            and v.payload["execution"].get("send_started_at") is None
        ):
            finish(
                sess,
                v,
                "cancelled",
                "Letzte Prüfung fehlgeschlagen – kein Kick / Final check failed – no kick",
                time.time(),
            )


def begin_send(server, vote_id, context=None):
    now = time.time()
    with enter_session() as sess:
        lock(sess, server)
        v = sess.get(LeadershipVote, vote_id)
        cfg = config(sess, server)
        if (
            not v
            or v.server_number != server
            or v.status != "executing"
            or v.payload["execution"].get("send_started_at") is not None
            or not cfg.enabled
            or command_conflicts(sess, server)
            or not discord_ready(sess)
            or cfg.mode != "active"
            or v.payload["rules"]["mode"] != "active"
            or not valid_context(context, now)
            or v.round_id != context["round_id"]
        ):
            return False
        observations = presence(sess, server)
        if not target_current(v, context["players"], observations, now):
            return False
        validate_participants(v, context["players"], observations, now)
        p = deepcopy(v.payload)
        if (
            p["yes"] < p["required"]
            or sum(m["valid"] for m in p["electorate"].values())
            < p["rules"]["minimum_participants"]
        ):
            return False
        reports = list(
            sess.scalars(
                select(AdminIncident).where(AdminIncident.leadership_vote_id == v.id)
            )
        )
        if not reports or any(
            i.status != "new" or i.assigned_to or i.target_id != v.target_id
            for i in reports
        ):
            return False
        p["execution"]["send_started_at"] = now
        v.payload = p
    return True


def complete(server, vote_id, confirmed, now=None):
    with enter_session() as sess:
        lock(sess, server)
        v = sess.get(LeadershipVote, vote_id)
        if not v or v.server_number != server or v.status != "executing":
            return
        p = deepcopy(v.payload)
        p["execution"]["confirmed"] = confirmed is True
        v.payload = p
        finish(
            sess,
            v,
            "kicked" if confirmed is True else "unknown",
            (
                "Kick bestätigt / Kick confirmed"
                if confirmed is True
                else "Kick unbestätigt – manuell prüfen, keine Wiederholung / Kick unconfirmed – manual review, no retry"
            ),
            time.time() if now is None else now,
        )


def cleanup(server, days, now=None):
    cutoff = (time.time() if now is None else now) - days * 86400
    with enter_session() as sess:
        lock(sess, server)
        sess.execute(
            delete(LeadershipMessage).where(
                LeadershipMessage.server_number == server,
                LeadershipMessage.created_at < cutoff,
            )
        )
        sess.execute(
            delete(LeadershipVote).where(
                LeadershipVote.server_number == server, LeadershipVote.ended_at < cutoff
            )
        )
