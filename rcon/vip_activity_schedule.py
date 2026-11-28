"""Activity-based scheduling for the opt-in VIP lifecycle."""

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import String, and_, cast, or_

from rcon.models import LogLine, PlayerSession, VipLifecycleDelivery
from rcon.types import GameIntEnum


PLAY_DAY_ZONE = ZoneInfo("Europe/Berlin")


def utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def play_day(value: datetime) -> date:
    return utc(value).astimezone(PLAY_DAY_ZONE).date()


@dataclass(frozen=True)
class Contact:
    id: int
    session_id: int | None
    rule: str
    fingerprint: str
    at: datetime


def contacts_by_player(sess, player_ids, config):
    """Read compact delivery facts. Real attempts count in both modes."""
    grouped = defaultdict(list)
    if not player_ids:
        return grouped
    delivery = VipLifecycleDelivery
    rows = sess.query(delivery.player_id_id, delivery.id, delivery.player_session_id,
                      delivery.rule, delivery.status_fingerprint, delivery.sent_at,
                      delivery.last_attempt_at, delivery.created_at).filter(
        delivery.player_id_id.in_(player_ids), delivery.server_family == config.server_family,
        delivery.status != "test")
    measured = delivery.test_mode.is_(False)
    if config.test_mode:
        # Old simulations used a different eligibility model and were never seen.
        measured = or_(measured, delivery.status_fingerprint.startswith("a1:sim:"))
    rows = rows.filter(measured)
    for pid, key, session, rule, fingerprint, sent, attempted, created in rows:
        grouped[pid].append(Contact(key, session, rule, fingerprint, utc(sent or attempted or created)))
    return grouped


def prior_playday_players(sess, sessions, contacts, family, now):
    """Only need one day before the current day (and after the last invitation).

    Return at most one id per online player; high-frequency, short sessions
    and lifetime log histories never cross the DB boundary.
    """
    windows = []
    for row in sessions.values():
        if row["start"] is None:
            continue
        pid, start = row["player_db_id"], utc(row["start"])
        previous = contacts[pid]
        age = now - start
        if age < timedelta(minutes=15) or not budget_available(previous, row["session_id"], now):
            continue
        if any(c.rule != "unverified" for c in previous):
            continue
        upper = datetime.combine(play_day(start), time.min, PLAY_DAY_ZONE).astimezone(timezone.utc)
        conditions = [PlayerSession.player_id_id == pid]
        exact = [PlayerSession.start_event_us < int(upper.timestamp() * 1_000_000)]
        legacy = [PlayerSession.start_event_us.is_(None), PlayerSession.created < upper.replace(tzinfo=None)]
        if previous:
            last = max(c.at for c in previous)
            if now - last < timedelta(days=60 if len(previous) >= 2 else 14):
                continue
            lower = datetime.combine(play_day(last) + timedelta(days=1), time.min,
                                     PLAY_DAY_ZONE).astimezone(timezone.utc)
            if lower >= upper:
                continue
            exact.append(PlayerSession.start_event_us >= int(lower.timestamp() * 1_000_000))
            legacy.append(PlayerSession.created >= lower.replace(tzinfo=None))
        elif age >= timedelta(minutes=45):
            continue
        conditions.append(or_(and_(*exact), and_(*legacy)))
        windows.append(and_(*conditions))
    if not windows:
        return set()
    game = GameIntEnum.HLL_VIETNAM if family == "hll_vietnam" else GameIntEnum.HLL_WW2
    matching_connection = sess.query(LogLine.id).filter(
        LogLine.server == cast(PlayerSession.server_number, String),
        LogLine.event_time == PlayerSession.start,
        LogLine.player1_player_id == PlayerSession.player_id_id,
        LogLine.type == "CONNECTED", LogLine.game == game.value,
    ).exists()
    return {pid for pid, in sess.query(PlayerSession.player_id_id).filter(
        or_(*windows), matching_connection).distinct()}


def invitation_key(contacts, had_another_day, start, now):
    """The previous durable contact identifies the next distinct opportunity."""
    invitations = [contact for contact in contacts if contact.rule == "unverified"]
    # A previously activated trial is incompatible with a fresh acquisition offer.
    if any(contact.rule.startswith("trial_") for contact in contacts):
        return None
    if not invitations:
        minimum = 15 if had_another_day else 45
        if now - start >= timedelta(minutes=minimum):
            return "invitation"
        return None
    last = max(invitations, key=lambda contact: (contact.at, contact.id))
    minimum_days = 60 if len(invitations) >= 2 else 14
    if now - last.at < timedelta(days=minimum_days) or now - start < timedelta(minutes=15):
        return None
    if not had_another_day or play_day(start) <= play_day(last.at):
        return None
    return f"after-{last.id}"


def budget_available(contacts, session_id, now):
    return (
        not any(contact.session_id == session_id for contact in contacts)
        and sum(contact.at > now - timedelta(days=28) for contact in contacts) < 2
    )


def separate_visit(sess, row):
    """Require a 30-minute break across servers since the preceding contact.

    A long stay on a different server can bridge two quick reconnects. Physical
    session IDs or the elapsed time since the message alone cannot prove a gap.
    """
    if not row["contacts"]:
        return True
    previous = max(row["contacts"], key=lambda c: (c.at, c.id))
    start = utc(row["start"])
    gap = timedelta(minutes=30)
    if start < previous.at + gap:
        return False
    original = sess.get(PlayerSession, previous.session_id) if previous.session_id else None
    lower = int(previous.at.timestamp() * 1_000_000)
    upper = int(start.timestamp() * 1_000_000)
    seen = sess.query(PlayerSession).filter(
        PlayerSession.player_id_id == row["player_db_id"],
        PlayerSession.id != row["session_id"],
        or_(PlayerSession.start_event_us.between(lower, upper),
            and_(PlayerSession.start_event_us.is_(None),
                 PlayerSession.created.between(previous.at.replace(tzinfo=None), start.replace(tzinfo=None)))),
    ).all()

    def beginning(session):
        if session.start_event_us is not None:
            return datetime.fromtimestamp(session.start_event_us / 1_000_000, timezone.utc)
        return utc(session.created)

    def ending(session):
        if session.end_event_us is not None:
            return datetime.fromtimestamp(session.end_event_us / 1_000_000, timezone.utc)
        if session.start and session.end and session.end >= session.start:
            return beginning(session) + (session.end - session.start)
        return None

    intervals = []
    if original is not None:
        intervals.append((previous.at, ending(original), original.server_number))
    for visit in seen:
        if visit.id != previous.session_id:
            intervals.append((beginning(visit), ending(visit), visit.server_number))
    open_servers = set()
    last_end = None
    for began, end, server in sorted(intervals, key=lambda item: item[0]) + [(start, None, row["server_number"])]:
        if not open_servers and last_end is not None and began >= last_end + gap:
            return True
        open_servers.discard(server)
        if end is None or end < began:
            open_servers.add(server)
        else:
            last_end = max(last_end or end, end)
    return False


def expiry_already_attempted(contacts, fingerprint):
    for contact in contacts:
        if contact.rule not in {"trial_expiring", "trial_expired"}:
            continue
        parts = contact.fingerprint.split(":", 2)
        if len(parts) != 3 or parts[0] not in {"v2", "a1"}:
            return True
        if fingerprint == "single" or parts[2] in {fingerprint, "single"}:
            return True
    return False
