"""Opt-in PostgreSQL staging checks. Never connects to a real game server.

Run in an isolated container with TEST_VIP_REWARDS_DB pointing to the disposable
database named viprewards_staging. All RCON writes terminate in RecordingRcon.
"""
import copy
import importlib.util
import os
from pathlib import Path
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from unittest.mock import patch

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from alembic.migration import MigrationContext
from alembic.operations import Operations

from rcon import models
from rcon.models import UserConfig, VipRewardEvent, VipRewardGrant, VipRewardState
from rcon.user_config.seed_vip import SeedVIPUserConfig
from rcon.user_config.vip_rewards import VipRewardsUserConfig
from rcon.vip_rewards import service
from rcon.vip_rewards.locking import serialized_vip

NOW = 1794225600.0
PLAYER = "76561198000000001"
VICTIM = "76561198000000002"


class RecordingRcon:
    def __init__(self):
        self.counts = {"allies": 14, "axis": 18}
        self.writes, self.messages, self.vips = [], [], {}
        self.healthy = True

    def get_gamestate(self):
        if not self.healthy:
            raise OSError("Synthetic status outage")
        return {"num_allied_players": self.counts["allies"], "num_axis_players": self.counts["axis"]}

    def get_detailed_players(self):
        players = {}
        for team, count in self.counts.items():
            for i in range(count):
                pid = (PLAYER if team == "allies" else VICTIM) if i == 0 else f"{76561198000100000 + i + (100 if team == 'axis' else 0)}"
                players[pid] = {"name": "Synthetic " + pid, "team": team}
        return {"players": players, "fail_count": 0}

    @serialized_vip
    def add_vip(self, player_id, description, expiration):
        self.writes.append((player_id, expiration))
        self.vips[player_id] = {"player_id": player_id, "name": description, "vip_expiration": expiration}
        return True

    def message_player(self, **kwargs):
        self.messages.append(kwargs)


@unittest.skipUnless(os.environ.get("TEST_VIP_REWARDS_DB"), "Requires disposable PostgreSQL staging database")
class PostgreSQLSeedingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        url = make_url(os.environ["TEST_VIP_REWARDS_DB"])
        if url.database != "viprewards_staging" or url.host != "viprewards-staging-db":
            raise RuntimeError("Refusing non-staging database")
        cls.db = create_engine(url, pool_size=12, max_overflow=12)
        models._ENGINE = cls.db
        os.environ["HLL_DB_URL"] = str(url.render_as_string(hide_password=False))
        os.environ["SERVER_NUMBER"] = "3"
        UserConfig.__table__.create(cls.db)
        path = Path(__file__).parents[1] / "alembic/versions/c8e2a4f61009_vip_rewards.py"
        spec = importlib.util.spec_from_file_location("staging_migration", path)
        migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration)
        with cls.db.begin() as connection:
            migration.op = Operations(MigrationContext.configure(connection))
            migration.upgrade()
        cls.migration = migration

    @classmethod
    def tearDownClass(cls):
        with cls.db.begin() as connection:
            cls.migration.op = Operations(MigrationContext.configure(connection))
            cls.migration.downgrade()
        UserConfig.__table__.drop(cls.db)
        cls.db.dispose()
        models._ENGINE = None

    def setUp(self):
        with self.db.begin() as connection:
            for table in (VipRewardGrant, VipRewardEvent, VipRewardState, UserConfig):
                connection.execute(table.__table__.delete())
        self.clock = [NOW]
        self.rcon = RecordingRcon()
        self.cfg = VipRewardsUserConfig(enabled=True, dry_run=False,
            melee={"enabled": True}, round={"enabled": True, "minutes": 1},
            weekly={"enabled": True, "days": 1, "minutes": 1},
            milestones={"enabled": True, "milestones": [{"play_hours": 1, "hours": 4}]},
            balance={"enabled": True, "minutes": 1},
            events=[{"id": "test", "name": "Test", "enabled": True, "minutes": 1,
                "start": datetime.fromtimestamp(NOW - 1, timezone.utc),
                "end": datetime.fromtimestamp(NOW + 86400, timezone.utc)}],
            challenges=[{"id": "knife", "name": "Knife", "enabled": True, "weapons": ["M3 KNIFE"], "kills": 1}])
        self.save_config()
        # Gate must work even though Seed-VIP awards are disabled.
        seed = SeedVIPUserConfig(enabled=False)
        with models.enter_session() as session:
            session.add(UserConfig(key=seed.KEY(), value=seed.model_dump(mode="json")))
        self.patches = [patch.object(service.time, "time", lambda: self.clock[0]),
                        patch.object(service, "current_round", lambda: "synthetic-round"),
                        patch.object(service, "current_vip", lambda rcon, pid: copy.deepcopy(rcon.vips.get(pid)))]
        for p in self.patches:
            p.start()
        self.addCleanup(lambda: [p.stop() for p in reversed(self.patches)])

    def save_config(self):
        VipRewardsUserConfig.save_to_db(self.cfg.model_dump(mode="json"))
        self.cfg = VipRewardsUserConfig.load_from_db()

    def tick(self, seconds=0):
        self.clock[0] += seconds
        service.tick(self.rcon)

    def enqueue(self, kind="kill", **kwargs):
        service.enqueue(dict(kind=kind, player_id=PLAYER, victim=VICTIM, weapon="M3 KNIFE",
            time=self.clock[0], key=f"{kind}:{self.clock[0]}", **kwargs))

    def release(self):
        self.rcon.counts = {"allies": 24, "axis": 20}
        self.tick()
        for _ in range(10):
            self.tick(30)
        self.assertEqual(service.status()["status"], "active")

    def queue_grant(self, key="queued"):
        with models.enter_session() as session:
            row = VipRewardGrant(server_number=3, preview=False, player_id=PLAYER,
                rule="melee", trigger=key, occurred=self.clock[0], requested_seconds=7200,
                credited_seconds=0, limit=3, status="queued", reason="", description="")
            session.add(row)
            session.flush()
            return row.id

    def assert_no_grants(self):
        self.assertEqual(self.rcon.writes, [])
        self.assertEqual(self.rcon.messages, [])
        with models.enter_session() as session:
            self.assertEqual(session.query(VipRewardGrant).count(), 0)

    def test_all_rules_blocked_during_ten_minutes_seeding(self):
        self.tick()
        for _ in range(20):
            self.enqueue()
            self.enqueue("signup")
            self.tick(30)
        self.enqueue("round_end")
        self.tick()
        self.assertEqual(service.status()["status"], "seeding")
        self.assert_no_grants()
        self.assertFalse(SeedVIPUserConfig.load_from_db().enabled)
        for player in service.read_state(False).get("players", {}).values():
            self.assertEqual(player["total"], 0)
            self.assertEqual(player["round"], 0)
            self.assertFalse(player["days"] or player["events"] or player["challenges"])

    def test_release_waits_five_minutes_and_does_not_backfill_kills(self):
        self.tick()
        self.enqueue()
        self.release()
        self.assert_no_grants()
        self.clock[0] += 1
        self.enqueue()
        self.tick()
        # One new kill may satisfy both melee and challenge, unlike the seeding kill.
        self.assertEqual(len(self.rcon.writes), 2)

    def test_kill_queued_before_population_drop_is_discarded(self):
        self.release()
        self.enqueue()
        self.rcon.counts["axis"] = 19
        self.tick(1)
        self.assertEqual(service.status()["status"], "seeding")
        self.assert_no_grants()
        self.release()
        self.assert_no_grants()

    def test_existing_queued_award_is_blocked_while_seeding(self):
        self.tick()
        grant_id = self.queue_grant()
        service.deliver(self.rcon, grant_id)
        self.assertEqual(self.rcon.writes, [])
        with models.enter_session() as session:
            row = session.get(VipRewardGrant, grant_id)
            self.assertEqual((row.status, row.credited_seconds), ("skipped", 0))

    def test_failed_status_stops_existing_progress_and_awards(self):
        self.release()
        self.enqueue()
        self.rcon.healthy = False
        self.tick(1)
        self.assertEqual(service.status()["status"], "unknown")
        self.assert_no_grants()

    def test_stale_status_blocks_direct_delivery(self):
        self.release()
        grant_id = self.queue_grant()
        self.clock[0] += 61
        service.deliver(self.rcon, grant_id)
        self.assertEqual(self.rcon.writes, [])

    def test_opt_out_of_seeding_pause_is_explicit(self):
        self.cfg.pause_during_seeding = False
        self.save_config()
        self.tick()
        self.enqueue()
        self.tick()
        self.assertEqual(len(self.rcon.writes), 2)

    def test_two_delivery_workers_use_real_postgres_lock(self):
        self.release()
        first, second = self.queue_grant("one"), self.queue_grant("two")
        barrier = threading.Barrier(2)
        def deliver(grant_id):
            barrier.wait(timeout=10)
            service.deliver(self.rcon, grant_id)
        with ThreadPoolExecutor(max_workers=2) as pool:
            list(pool.map(deliver, (first, second)))
        self.assertEqual(len(self.rcon.writes), 2)
        target = datetime.fromisoformat(self.rcon.vips[PLAYER]["vip_expiration"]).timestamp()
        self.assertEqual(target, self.clock[0] + 14400)
        with models.enter_session() as session:
            self.assertEqual(session.query(VipRewardGrant).filter_by(status="awarded").count(), 2)

    def test_no_awards_before_full_five_minute_release(self):
        self.tick()
        self.rcon.counts = {"allies": 24, "axis": 20}
        self.tick()
        for _ in range(9):
            self.tick(30)
            self.enqueue()
        self.tick(29)
        self.assertEqual(service.status()["status"], "seeding")
        self.assert_no_grants()
        self.tick(1)
        self.assertEqual(service.status()["status"], "active")
        self.assert_no_grants()

    def test_changed_seed_thresholds_do_not_consume_queued_kills(self):
        self.release()
        self.enqueue()
        seed = SeedVIPUserConfig.load_from_db()
        seed.requirements.max_allies = 21
        with models.enter_session() as session:
            session.query(UserConfig).filter_by(key=seed.KEY()).one().value = seed.model_dump(mode="json")
        self.tick(1)
        self.assertEqual(service.status()["status"], "seeding")
        self.assert_no_grants()
        self.assertFalse(service.read_state(False)["players"][PLAYER]["challenges"])

    def test_seed_vip_reward_still_works_while_new_rewards_are_paused(self):
        from collections import defaultdict
        from rcon.seed_vip.utils import reward_players
        self.tick()
        self.assertEqual(service.status()["status"], "seeding")
        seed = SeedVIPUserConfig(enabled=True, dry_run=False)
        before = seed.model_dump(mode="json")
        times = defaultdict(lambda: datetime.fromtimestamp(NOW + 86400, timezone.utc))
        reward_players(self.rcon, seed, {PLAYER}, {}, {PLAYER: "Synthetic"}, times,
                       reward_time=datetime.fromtimestamp(NOW, timezone.utc))
        self.assertEqual(len(self.rcon.writes), 1)
        self.assertEqual(seed.model_dump(mode="json"), before)
        with models.enter_session() as session:
            self.assertEqual(session.query(VipRewardGrant).count(), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
