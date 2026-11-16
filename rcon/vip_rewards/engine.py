"""Pure reward policy; all timestamps are UTC epoch seconds, all state is JSON."""

from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from hllrcon import HLLVWeapon, WeaponType as ReferenceWeaponType

MELEE = {"m3 knife", "feldspaten", "fairbairn-sykes", "mpl-50 spade", "mpl-50 spaten"}


def weapon(value):
    return (
        str(value)
        .casefold()
        .strip()
        .strip("\"'")
        .translate(str.maketrans({"–": "-", "—": "-", "‑": "-", "_": "-"}))
    )


VIETNAM_MELEE = frozenset(weapon(item.id) for item in HLLVWeapon.all()
                          if item.type == ReferenceWeaponType.MELEE)


def periods(ts, zone):
    date = datetime.fromtimestamp(ts, ZoneInfo(zone)).date()
    return date.isoformat(), (date - timedelta(days=date.weekday())).isoformat()


def day_segments(start, end, zone):
    """Split real elapsed seconds at local midnights, including DST transitions."""
    tz = ZoneInfo(zone)
    while start < end:
        date = datetime.fromtimestamp(start, tz).date()
        midnight = datetime.combine(
            date + timedelta(days=1), datetime.min.time(), tz
        ).timestamp()
        stop = min(end, midnight)
        yield date.isoformat(), stop - start
        start = stop


def retained_challenge_progress(progress, challenges, now, zone):
    """Keep active and recently ended periods; completed grants are separate."""
    known_ids = {challenge.id for challenge in challenges}
    cutoff = datetime.fromtimestamp(now, ZoneInfo(zone)).date() - timedelta(days=14)
    retained = {}
    for key, value in progress.items():
        challenge_id, separator, period = key.rpartition(":")
        if not separator:
            # Preserve unknown formats rather than guessing how to migrate them.
            retained[key] = value
        elif challenge_id not in known_ids:
            continue
        elif period == "fixed":
            retained[key] = value
        else:
            try:
                period_date = date.fromisoformat(period)
            except ValueError:
                retained[key] = value
            else:
                if period_date >= cutoff:
                    retained[key] = value
    return retained


def gate(state, cfg, now):
    if not cfg.enabled:
        return "disabled"
    if state.get("config") is not None and state["config"] != cfg.policy_signature():
        return "unknown"
    if (
        not state.get("observed")
        or now - state["observed"] > 60
        or not state.get("healthy")
    ):
        return "unknown"
    if cfg.pause_during_seeding and not state.get("released"):
        return "seeding"
    return "active"


class Engine:
    def __init__(self, state, cfg, *, game="hll"):
        self.s, self.c = state, cfg
        self.melee_weapons = VIETNAM_MELEE if game == "hllv" else MELEE
        self.claims = []
        state.setdefault("players", {})
        state.setdefault("opponents", {})
        state.setdefault("round_seconds", 0)
        # No interval crosses a configuration change or disabled period.
        signature = cfg.policy_signature()
        if state.get("config") != signature:
            old_rules = state.get("active_rules", [])
            state["config"] = signature
            state["baseline"] = None
            state["active_rules"] = self.rule_keys()
            if "round" not in old_rules and cfg.round.enabled:
                state["round_seconds"] = 0
                for player in state["players"].values():
                    player["round"] = 0
            for player in state["players"].values():
                player.pop("balance", None)

    def rule_keys(self):
        keys = [
            k
            for k in ("melee", "round", "weekly", "weekly_support", "milestones", "balance")
            if getattr(self.c, k).enabled
        ]
        return (
            keys
            + ["event:" + r.id for r in self.c.events if r.enabled]
            + ["challenge:" + r.id for r in self.c.challenges if r.enabled]
        )

    def player(self, pid):
        return self.s["players"].setdefault(
            pid,
            {
                "days": {},
                "total": 0,
                "round": 0,
                "events": {},
                "challenges": {},
                "completed": {},
            },
        )

    def eligible(self, pid):
        return bool(pid) and pid not in self.c.excluded_player_ids

    def claim(self, pid, rule, key, hours, now, limit=0):
        player = self.player(pid)
        unique = rule + ":" + str(key)
        if unique in player["completed"]:
            return
        player["completed"][unique] = now
        self.claims.append(
            dict(
                player_id=pid,
                rule=rule,
                trigger=str(key),
                hours=hours,
                occurred=now,
                limit=limit,
            )
        )

    def snapshot(self, now, players, counts, thresholds, healthy=True, blocked_balances=frozenset()):
        s, c = self.s, self.c
        previous_status = gate(s, c, now)
        previous_time = s.get("baseline")
        previous_players = s.get("online", {})
        fresh = s.get("observed") and 0 <= now - s["observed"] <= 60
        above = healthy and all(counts[t] >= thresholds[t] for t in ("allies", "axis"))
        if not above or not fresh or s.get("thresholds") != thresholds:
            s["above_since"] = now if above else None
        elif s.get("above_since") is None:
            s["above_since"] = now
        s.update(
            observed=now,
            healthy=healthy,
            counts=counts,
            thresholds=thresholds,
            released=bool(above and now - s["above_since"] >= 300),
        )
        online = {
            pid: p for pid, p in players.items() if p.get("team") in ("allies", "axis")
        }
        active = gate(s, c, now) == "active"
        delta = now - previous_time if previous_time is not None else 0
        valid_interval = active and previous_status == "active" and 0 < delta <= 60
        s["baseline"] = now if active else None
        s["online"] = online
        if valid_interval and s.get("round_known", True):
            s["round_seconds"] += delta
        for pid, p in s["players"].items():
            p["challenges"] = retained_challenge_progress(
                p.get("challenges", {}), c.challenges, now, c.timezone
            )
            p["completed"] = {
                k: t
                for k, t in p["completed"].items()
                if t > now - 8 * 86400
                or k.startswith(("milestones:", "event:"))
                or k.endswith(":fixed")
            }
            if not active or pid not in online or not self.eligible(pid):
                p.pop("balance", None)
        self.support_snapshot(now, online, previous_players, previous_time, valid_interval)
        if not active:
            return
        _, week = periods(now, c.timezone)
        for pid, info in online.items():
            if not self.eligible(pid):
                continue
            p = self.player(pid)
            p["name"] = info.get("name", pid)
            same_team = (
                pid in previous_players
                and previous_players[pid]["team"] == info["team"]
            )
            if valid_interval and same_team:
                if c.round.enabled and s.get("round_known", True):
                    p["round"] += delta
                if c.weekly.enabled:
                    for day, seconds in day_segments(previous_time, now, c.timezone):
                        p["days"][day] = p["days"].get(day, 0) + seconds
                    # Only this and previous week are needed for progress inspection.
                    cutoff = (
                        datetime.fromtimestamp(now, ZoneInfo(c.timezone)).date()
                        - timedelta(days=14)
                    ).isoformat()
                    p["days"] = {d: v for d, v in p["days"].items() if d >= cutoff}
                    days = sum(
                        1
                        for d, v in p["days"].items()
                        if d >= week and v >= c.weekly.minutes * 60
                    )
                    if days >= c.weekly.days:
                        self.claim(pid, "weekly", week, c.weekly.hours, now)
                if c.milestones.enabled:
                    p["total"] += delta
                    for m in sorted(
                        c.milestones.milestones, key=lambda m: m.play_hours
                    ):
                        if p["total"] >= m.play_hours * 3600:
                            self.claim(pid, "milestones", m.play_hours, m.hours, now)
                for event in c.events:
                    if not event.enabled:
                        continue
                    seconds = max(
                        0,
                        min(now, event.end.timestamp())
                        - max(previous_time, event.start.timestamp()),
                    )
                    p["events"][event.id] = p["events"].get(event.id, 0) + seconds
                    if seconds and p["events"][event.id] >= event.minutes * 60:
                        self.claim(pid, "event:" + event.id, event.id, event.hours, now, event.limit)
            balance = p.get("balance")
            if balance:
                if balance.get("switched"):
                    if info["team"] != balance["target"]:
                        p.pop("balance", None)
                    elif valid_interval and same_team and pid not in blocked_balances:
                        balance["seconds"] += delta
                        if balance["seconds"] >= c.balance.minutes * 60:
                            self.claim(
                                pid,
                                "balance",
                                balance["signup"],
                                c.balance.hours,
                                now,
                                c.balance.limit,
                            )
                            p.pop("balance", None)
                elif now > balance["deadline"]:
                    p.pop("balance", None)
                elif info["team"] != balance["source"]:
                    # A snapshot alone cannot prove a voluntary switch.
                    p.pop("balance", None)
        cutoff = now - c.opponent_cooldown_minutes * 60
        s["opponents"] = {k: t for k, t in s["opponents"].items() if t > cutoff}

    def support_snapshot(self, now, online, previous_players, previous_time, valid_interval):
        """Count only observed positive gains, never an existing match total.

        Keep a match high-water mark across reconnects and temporary score drops.
        Paused observations advance it too. Round boundaries explicitly clear it.
        Intervals crossing local Monday are discarded rather than guessed.
        """
        c = self.c
        if not c.weekly_support.enabled:
            return
        _, week = periods(now, c.timezone)
        for pid, info in online.items():
            if not self.eligible(pid):
                continue
            p = self.player(pid)
            progress = p.get("weekly_support", {})
            if progress.get("week") != week:
                progress = p["weekly_support"] = {"week": week, "points": 0}
            score = info.get("support")
            if type(score) is not int or score < 0:
                continue
            previous = previous_players.get(pid, {})
            old = p.get("support_highwater")
            p["support_highwater"] = max(score, old) if old is not None else score
            if not (c.weekly_support.enabled and valid_interval
                    and self.s.get("round_known", True)
                    and previous.get("team") == info.get("team")
                    and type(previous.get("support")) is int
                    and previous["support"] >= 0 and old is not None
                    and periods(previous_time, c.timezone)[1] == week):
                continue
            gained = max(0, score - old)
            progress["points"] += gained
            if gained and progress["points"] >= c.weekly_support.points:
                self.claim(pid, "weekly_support", week, c.weekly_support.hours, now)

    def event(self, event, now):
        s, c = self.s, self.c
        kind, pid = event["kind"], event.get("player_id")
        # Never replay stale events or events observed before the current baseline.
        ts = event["time"]
        if kind == "forced":
            if pid in s["players"]:
                balance = s["players"][pid].get("balance")
                if balance and balance.get("signup", ts) <= event.get("switch_started", ts):
                    s["players"][pid].pop("balance", None)
            return
        if kind == "disconnect":
            s.get("online", {}).pop(pid, None)
            if pid in s["players"]:
                s["players"][pid].pop("balance", None)
            return
        active = (
            gate(s, c, now) == "active"
            and 0 <= now - ts <= 60
            and event.get("allowed", False)
            and event.get("config", s["config"]) == s["config"]
        )
        if kind in ("round_start", "round_end"):
            if (
                kind == "round_end"
                and active
                and c.round.enabled
                and s.get("round_known", True)
                and s["round_seconds"] > 0
            ):
                for player_id in s.get("online", {}):
                    p = self.player(player_id)
                    if (
                        self.eligible(player_id)
                        and p["round"] >= c.round.minutes * 60
                        and p["round"] >= c.round.fraction * s["round_seconds"]
                    ):
                        self.claim(
                            player_id,
                            "round",
                            event["key"],
                            c.round.hours,
                            now,
                            c.round.limit,
                        )
            s["round_seconds"] = 0
            s["baseline"] = None
            for p in s["players"].values():
                p["round"] = 0
                p.pop("support_highwater", None)
                p.pop("balance", None)
            return
        if not active or not self.eligible(pid):
            return
        p = self.player(pid)
        if kind == "signup" and c.balance.enabled:
            info = s.get("online", {}).get(pid)
            if not info:
                return
            source = info["team"]
            target = "axis" if source == "allies" else "allies"
            if s["counts"][source] - s["counts"][target] >= c.balance.difference:
                p["balance"] = dict(
                    source=source,
                    target=target,
                    signup=ts,
                    deadline=ts + c.balance.signup_minutes * 60,
                    seconds=0,
                )
        elif kind == "switch" and c.balance.enabled:
            b = p.get("balance")
            if not b:
                return
            if b.get("switched") or ts > b["deadline"] or event.get("forced"):
                p.pop("balance", None)
            elif event.get("source") == b["source"] and event.get("target") == "none":
                b["left"] = ts
            elif event.get("target") == b["target"] and (
                event.get("source") == b["source"]
                or (
                    event.get("source") == "none"
                    and b.get("left")
                    and ts - b["left"] <= 60
                )
            ):
                if (
                    s["counts"][b["source"]] - s["counts"][b["target"]]
                    >= c.balance.difference
                ):
                    b["switched"] = ts
                else:
                    p.pop("balance", None)
            else:
                p.pop("balance", None)
        elif kind == "kill":
            victim = event.get("victim")
            if not victim or victim == pid:
                return
            w = weapon(event.get("weapon", ""))
            matching = [
                r
                for r in c.challenges
                if r.enabled
                and w in {weapon(x) for x in r.weapons}
                and (
                    r.period != "fixed" or r.start.timestamp() <= ts < r.end.timestamp()
                )
            ]
            if not (c.melee.enabled and w in self.melee_weapons) and not matching:
                return
            pair = pid + ":" + victim
            if (
                ts - s["opponents"].get(pair, float("-inf"))
                < c.opponent_cooldown_minutes * 60
            ):
                return
            s["opponents"][pair] = ts
            if c.melee.enabled and w in self.melee_weapons:
                self.claim(
                    pid, "melee", event["key"], c.melee.hours, now, c.melee.limit
                )
            day, week = periods(ts, c.timezone)
            for challenge in matching:
                period = (
                    day
                    if challenge.period == "day"
                    else week if challenge.period == "week" else "fixed"
                )
                key = challenge.id + ":" + period
                p["challenges"][key] = p["challenges"].get(key, 0) + 1
                if p["challenges"][key] >= challenge.kills:
                    self.claim(
                        pid, "challenge:" + challenge.id, period, challenge.hours, now, challenge.limit
                    )


def budget(requested, used, cap):
    return max(0, min(requested, cap - used))
