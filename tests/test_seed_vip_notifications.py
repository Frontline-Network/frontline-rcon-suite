import unittest
from collections import defaultdict
from contextlib import nullcontext
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock, patch

from rcon.seed_vip import notifications, service, utils
from rcon.seed_vip.models import Player, ServerPopulation
from rcon.user_config.seed_vip import SeedVIPUserConfig


class MemoryRedis:
    def __init__(self):
        self.data = {}

    def pipeline(self, **kwargs):
        return self

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def execute(self):
        return []

    def watch(self, key):
        pass

    def multi(self):
        pass

    def hget(self, key, field):
        return self.data.get(key, {}).get(field)

    def expire(self, *args):
        return True

    def hset(self, key, field=None, value=None, mapping=None):
        self.data.setdefault(key, {}).update(mapping or {field: value})

    def hgetall(self, key):
        return dict(self.data.get(key, {}))

    def hdel(self, key, field):
        self.data.get(key, {}).pop(field, None)

    def hlen(self, key):
        return len(self.data.get(key, {}))

    def delete(self, key):
        self.data.pop(key, None)


class NoticeTests(unittest.TestCase):
    def setUp(self):
        self.clock = 1000
        self.red = MemoryRedis()
        self.queue = notifications.NotificationOutbox(self.red, '1')
        self.api = MagicMock()
        self.api.message_player.return_value = True
        self.api.add_vip.return_value = True
        self.cfg = SeedVIPUserConfig(enabled=True, dry_run=False, language=None)
        for target, replacement in (
            ('rcon.seed_vip.notifications.time.time', lambda: self.clock),
            ('rcon.seed_vip.notifications.time.sleep', Mock()),
        ):
            p = patch(target, replacement)
            p.start()
            self.addCleanup(p.stop)

    def test_sequential_delivery_100_players_no_bulk_or_vip(self):
        self.queue.enqueue({str(i): 'Seed complete' for i in range(100)}, self.api)
        self.assertFalse(self.queue.flush(self.api))
        self.assertEqual(self.api.message_player.call_count, 100)
        self.assertEqual(self.api.without_retries.call_count, 100)
        self.api.bulk_message_players.assert_not_called()
        self.api.add_vip.assert_not_called()

    def test_broken_pipe_is_not_retried_after_restart(self):
        self.queue.enqueue({'a': 'VIP granted', 'b': 'Server live'}, self.api)
        self.api.message_player.side_effect = [BrokenPipeError(), True, True]
        self.assertTrue(self.queue.flush(self.api))
        self.assertEqual(self.api.message_player.call_count, 2)
        restarted = notifications.NotificationOutbox(self.red, '1')
        self.assertTrue(restarted.flush(self.api))
        self.assertEqual(self.api.message_player.call_count, 2)
        self.clock += 30
        self.assertTrue(restarted.flush(self.api))
        self.assertEqual(self.api.message_player.call_count, 2)
        self.api.add_vip.assert_not_called()

    def test_explicit_rejection_retries_bounded(self):
        self.api.message_player.return_value = False
        self.queue.enqueue({'a': 'Done'}, self.api)
        for _ in range(5):
            self.queue.flush(self.api)
            self.clock += 30
        self.assertEqual(self.api.message_player.call_count, 3)
        self.assertFalse(self.queue.flush(self.api))

    def test_timeout_is_never_retried(self):
        self.api.message_player.side_effect = TimeoutError()
        self.queue.enqueue({'a': 'Done'}, self.api)
        for _ in range(5):
            self.queue.flush(self.api)
            self.clock += 30
        self.assertEqual(self.api.message_player.call_count, 1)

    def test_expired_and_corrupt_notices_not_sent(self):
        self.queue.enqueue({'a': 'Done'}, self.api)
        self.red.hset(self.queue.key, 'corrupt', '{')
        self.clock += 601
        self.assertFalse(self.queue.flush(self.api))
        self.api.message_player.assert_not_called()

    def test_server_isolation(self):
        self.queue.enqueue({'a': 'Done'}, self.api)
        other = notifications.NotificationOutbox(self.red, '2')
        self.assertFalse(other.flush(self.api))
        other.clear()
        self.assertEqual(self.red.hlen(self.queue.key), 1)

    def test_redis_enqueue_failure_does_not_risk_double_send(self):
        self.red.pipeline = Mock(side_effect=ConnectionError())
        self.api.message_player.side_effect = [BrokenPipeError(), True]
        self.queue.enqueue({'a': 'Done', 'b': 'Done'}, self.api)
        self.api.message_player.assert_not_called()
        self.api.add_vip.assert_not_called()

    def test_lost_enqueue_reply_does_not_send_directly_or_duplicate(self):
        self.red.execute = Mock(side_effect=ConnectionError("reply lost"))
        self.queue.enqueue({'a': 'Done'}, self.api)
        self.api.message_player.assert_not_called()
        self.red.execute = Mock(return_value=[])
        self.queue.flush(self.api)
        self.api.message_player.assert_called_once()

    def test_redis_read_failure_defers(self):
        self.red.hgetall = Mock(side_effect=ConnectionError())
        self.assertTrue(self.queue.flush(self.api))
        self.api.message_player.assert_not_called()

    def test_failed_attempt_checkpoint_does_not_send(self):
        self.queue.enqueue({'a': 'Done'}, self.api)
        self.red.hset = Mock(side_effect=ConnectionError())
        self.assertTrue(self.queue.flush(self.api))
        self.api.message_player.assert_not_called()

    def test_failed_ack_storage_never_grants_vip(self):
        self.queue.enqueue({'a': 'Done'}, self.api)
        self.red.hdel = Mock(side_effect=ConnectionError())
        for _ in range(5):
            self.queue.flush(self.api)
            self.clock += 30
        self.assertEqual(self.api.message_player.call_count, 1)
        self.api.add_vip.assert_not_called()

    def test_formatter_empty_defaultdict_and_two_recipient_groups(self):
        expiry = datetime(2026, 9, 30, tzinfo=timezone.utc)
        self.cfg.nice_time_delta = self.cfg.nice_expiration_date = False
        utils.message_players(self.api, self.cfg, 'VIP {vip_expiration}', ['a'],
                              defaultdict(lambda: expiry), self.queue)
        utils.message_players(self.api, self.cfg, 'Live without VIP', ['b'], None, self.queue)
        self.queue.flush(self.api)
        sent = {c.kwargs['player_id']: c.kwargs['message'] for c in self.api.message_player.call_args_list}
        self.assertEqual(sent, {'a': 'VIP 2026-09-30T00:00:00+00:00', 'b': 'Live without VIP'})

    def test_invalid_and_empty_templates_do_not_crash_or_send(self):
        for message in (' ', 'VIP {unknown}', 'VIP {'):
            utils.message_players(self.api, self.cfg, message, ['a'],
                                  defaultdict(lambda: datetime.now(timezone.utc)), self.queue)
        self.assertFalse(self.queue.flush(self.api))
        self.api.message_player.assert_not_called()

    def test_dry_run_never_queues_or_sends(self):
        self.cfg.dry_run = True
        utils.message_players(self.api, self.cfg, 'Done', ['a'], None, self.queue)
        self.assertFalse(self.queue.flush(self.api))
        self.api.message_player.assert_not_called()

    def run_service(self, configs, snapshots):
        with patch.object(service.SeedVIPUserConfig, 'load_from_db', side_effect=configs), \
             patch.object(service, 'get_rcon_api', return_value=self.api), \
             patch.object(service, 'NotificationOutbox', return_value=self.queue), \
             patch.object(service, 'get_server_snapshot', side_effect=snapshots), \
             patch.object(service, 'get_vips', return_value={}), \
             patch('rcon.vip_rewards.locking.vip_lock', side_effect=lambda _player_id: nullcontext()), \
             patch('rcon.vip_rewards.service.current_vip', return_value=None), \
             patch.object(service, 'wait', side_effect=lambda _event, seconds: setattr(self, 'clock', self.clock + seconds) or False):
            service.run()

    def test_complete_transition_does_not_retry_uncertain_notice_or_reward(self):
        players = ServerPopulation(players={
            'a': Player(name='Eligible', player_id='a', current_playtime_seconds=600),
            'b': Player(name='New player', player_id='b', current_playtime_seconds=1),
        })
        low = {'num_allied_players': 1, 'num_axis_players': 1}
        full = {'num_allied_players': 22, 'num_axis_players': 22}
        self.api.message_player.side_effect = [BrokenPipeError(), True, True]
        off = self.cfg.model_copy(update={'enabled': False})
        self.run_service([self.cfg]*4 + [off], [(players, low), (players, full), (players, full)])
        self.api.add_vip.assert_called_once()
        self.assertEqual(self.api.add_vip.call_args.kwargs['player_id'], 'a')
        self.assertEqual(self.api.message_player.call_count, 2)
        self.api.bulk_message_players.assert_not_called()

    def test_restart_when_seeded_delivers_pending_without_any_reward(self):
        self.queue.enqueue({'a': 'Already rewarded'}, self.api)
        full = {'num_allied_players': 22, 'num_axis_players': 22}
        off = self.cfg.model_copy(update={'enabled': False})
        self.run_service([self.cfg, self.cfg, off], [(ServerPopulation(players={}), full)])
        self.api.message_player.assert_called_once()
        self.api.add_vip.assert_not_called()

    def test_interrupted_send_is_not_replayed_after_restart(self):
        self.queue.enqueue({'a': 'Done'}, self.api)
        self.api.message_player.side_effect = KeyboardInterrupt()
        with self.assertRaises(KeyboardInterrupt):
            self.queue.flush(self.api)
        self.api.message_player.side_effect = None
        restarted = notifications.NotificationOutbox(self.red, '1')
        self.clock += 60
        self.assertTrue(restarted.flush(self.api))
        self.assertEqual(self.api.message_player.call_count, 1)

    def test_old_snapshot_cannot_claim_the_same_notice_twice(self):
        import json
        self.queue.enqueue({'a': 'Done'}, self.api)
        ident, raw = next(iter(self.red.hgetall(self.queue.key).items()))
        self.assertTrue(self.queue._claim(ident, raw, json.loads(raw)))
        self.assertFalse(self.queue._claim(ident, raw, json.loads(raw)))

    def test_pre_upgrade_attempt_is_uncertain_and_not_replayed(self):
        import json
        self.queue.enqueue({'a': 'Done'}, self.api)
        ident, raw = next(iter(self.red.hgetall(self.queue.key).items()))
        old = json.loads(raw)
        old['attempts'] = 1
        self.red.hset(self.queue.key, ident, json.dumps(old))
        self.queue.flush(self.api)
        self.clock += 30
        self.queue.flush(self.api)
        self.api.message_player.assert_not_called()
        self.assertEqual(json.loads(self.red.hget(self.queue.key, ident))['state'], 'sending')

    def test_webhook_failure_does_not_restart_seed_transition(self):
        players = ServerPopulation(players={
            'a': Player(name='Eligible', player_id='a', current_playtime_seconds=600),
        })
        low = {'num_allied_players': 1, 'num_axis_players': 1}
        full = {'num_allied_players': 22, 'num_axis_players': 22, 'raw_time_remaining': 0}
        cfg = self.cfg.model_copy(update={'hooks': [SimpleNamespace(url='https://example.invalid/secret')]})
        off = self.cfg.model_copy(update={'enabled': False})
        with patch.object(service, 'make_seed_announcement_embed', return_value=object()), \
             patch.object(service.discord.SyncWebhook, 'from_url', side_effect=RuntimeError('webhook secret')):
            self.run_service([cfg]*4 + [off], [(players, low), (players, full), (players, full)])
        self.api.add_vip.assert_called_once()

    def test_disabled_and_dry_run_clear_pending(self):
        for cfg in (self.cfg.model_copy(update={'enabled': False}),
                    self.cfg.model_copy(update={'dry_run': True})):
            self.queue.enqueue({'a': 'Stale notice'}, self.api)
            off = self.cfg.model_copy(update={'enabled': False})
            self.run_service([cfg, cfg, off], [(ServerPopulation(players={}), {'num_allied_players': 22, 'num_axis_players': 22})])
            self.assertEqual(self.red.hlen(self.queue.key), 0)
            self.api.message_player.assert_not_called()


if __name__ == '__main__':
    unittest.main()
