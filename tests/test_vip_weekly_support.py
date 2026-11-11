"""Weekly support credits and private configurable progress replies, offline only."""
from copy import deepcopy
from datetime import datetime, timezone
from unittest.mock import Mock

import pytest
from pydantic import ValidationError
from rcon.user_config.vip_rewards import VipRewardsUserConfig
from rcon.vip_rewards.engine import Engine

NOW = datetime(2026, 11, 9, 12, tzinfo=timezone.utc).timestamp()
COUNTS = {'allies': 25, 'axis': 25}
THRESHOLDS = {'allies': 20, 'axis': 20}

def setup(**kwargs):
    cfg = VipRewardsUserConfig(enabled=True, pause_during_seeding=False,
        weekly_support={'enabled': True, 'points': 100, 'hours': 7}, **kwargs)
    return Engine({}, cfg)

def sample(e, time, score, **kwargs):
    e.snapshot(time, {'a': {'name':'A','team':'allies','support':score}},
               COUNTS, THRESHOLDS, **kwargs)

def total(e):
    return e.player('a')['weekly_support']['points']

def test_baseline_positive_gains_once_per_week_and_persistence():
    e = setup(); sample(e, NOW, 1000); sample(e, NOW+30, 1050)
    assert total(e) == 50
    e = Engine(deepcopy(e.s), e.c)
    sample(e, NOW+60, 1100); sample(e, NOW+90, 1200)
    assert total(e) == 200
    assert len(e.claims) == 1
    assert e.claims[0]['hours'] == 7
    assert e.claims[0]['trigger'] == '2026-11-09'

def test_reconnect_and_score_rebound_do_not_duplicate():
    e=setup(); sample(e,NOW,100); sample(e,NOW+10,140)
    e.event({'kind':'disconnect','player_id':'a','time':NOW+11},NOW+11)
    sample(e,NOW+20,170)  # reconnect is a baseline, not a gain
    sample(e,NOW+30,0); sample(e,NOW+40,170)
    assert total(e)==40
    sample(e,NOW+50,180)
    assert total(e)==50

def test_round_boundary_keeps_week_but_resets_score():
    e=setup(); sample(e,NOW,100); sample(e,NOW+10,140)
    e.event({'kind':'round_start','time':NOW+11,'key':'new','allowed':True},NOW+11)
    sample(e,NOW+20,10); sample(e,NOW+30,50)
    assert total(e)==80

@pytest.mark.parametrize('bad', [None, -1, '50', True])
def test_invalid_scores_never_credit(bad):
    e=setup(); sample(e,NOW,100); sample(e,NOW+10,bad); sample(e,NOW+20,150)
    assert total(e)==0
    sample(e,NOW+30,160)
    assert total(e)==10

def test_stale_unhealthy_and_unknown_round_do_not_credit():
    e=setup(); sample(e,NOW,100); sample(e,NOW+90,200)
    sample(e,NOW+100,300,healthy=False); sample(e,NOW+110,400)
    e.s['round_known']=False; sample(e,NOW+120,500)
    assert total(e)==0

def test_seeding_pause_and_release_do_not_credit_hidden_gains():
    e=Engine({}, VipRewardsUserConfig(enabled=True,
        weekly_support={'enabled':True,'points':100,'hours':7}))
    for seconds in range(0,331,30): sample(e,NOW+seconds,100+seconds)
    assert total(e)==30

def test_disabled_rule_and_configuration_change_do_not_backfill():
    e=setup(); sample(e,NOW,100)
    cfg=e.c.model_copy(deep=True);cfg.weekly_support.enabled=False
    e=Engine(e.s,cfg);sample(e,NOW+10,200)
    cfg=cfg.model_copy(deep=True);cfg.weekly_support.enabled=True
    e=Engine(e.s,cfg);sample(e,NOW+20,300);sample(e,NOW+30,310)
    assert total(e)==10

def test_local_week_boundary_discards_ambiguous_interval():
    # Sunday 23:59:50 in Berlin; Monday is still Sunday in UTC.
    t=datetime(2026,11,15,22,59,50,tzinfo=timezone.utc).timestamp()
    e=setup();sample(e,t-10,100);sample(e,t,150)
    sample(e,t+20,250)
    assert total(e)==0
    sample(e,t+30,350)
    assert e.claims[0]['trigger']=='2026-11-16'

def test_excluded_player_gets_no_support_credit():
    e=setup(excluded_player_ids=['76561198000000000'])
    e.c.excluded_player_ids=['a']
    sample(e,NOW,0);sample(e,NOW+10,1000)
    assert not e.claims

@pytest.mark.parametrize('values',[{'points':0},{'points':1.5},{'hours':0}])
def test_weekly_support_validation(values):
    with pytest.raises(ValidationError): VipRewardsUserConfig(weekly_support=values)

def test_status_command_validation():
    assert VipRewardsUserConfig(status_command=' !TEAMVIP ').status_command=='!teamvip'
    assert VipRewardsUserConfig(status_command='').status_command==''
    for word in ('!balance','!admin','!vip','!foo bar','rewards'):
        with pytest.raises(ValidationError): VipRewardsUserConfig(status_command=word)

def test_private_status_and_preview_suppression(monkeypatch):
    from rcon.vip_rewards import hooks, service
    e=setup(status_command='!teamvip',dry_run=False);sample(e,NOW,100);sample(e,NOW+10,150)
    monkeypatch.setattr(hooks.VipRewardsUserConfig,'load_from_db',lambda:e.c)
    monkeypatch.setattr(hooks,'read_state',lambda _:e.s)
    monkeypatch.setattr(hooks.time,'time',lambda:NOW+10)
    monkeypatch.setattr(service,'status_command_conflict',lambda _:False)
    red=Mock(); red.set.return_value=True
    monkeypatch.setattr(hooks,'get_redis_client',lambda:red)
    rcon=Mock();log={'sub_content':' !TEAMVIP ','timestamp_ms':(NOW+10)*1000,'player_id_1':'a'}
    hooks.reward_status(rcon,log)
    assert rcon.message_player.call_args.kwargs['player_id']=='a'
    assert '50 / 100' in rcon.message_player.call_args.kwargs['message']
    red.set.return_value=False;hooks.reward_status(rcon,log)
    assert rcon.message_player.call_count==1
    e.c.dry_run=True;hooks.reward_status(rcon,log)
    assert rcon.message_player.call_count==1

def test_status_resets_display_at_week_boundary():
    from rcon.vip_rewards.service import status_message
    e=setup();sample(e,NOW,0);sample(e,NOW+10,50)
    assert '0 / 100' in status_message(e.c,e.s,'a',NOW+7*86400)

def test_status_command_conflict_checks_other_features(monkeypatch):
    from types import SimpleNamespace
    from rcon.vip_rewards import service
    from rcon.user_config.autobalancer import AutobalancerUserConfig
    from rcon.user_config.chat_commands import ChatCommandsUserConfig
    from rcon.user_config.rcon_chat_commands import RConChatCommandsUserConfig
    from rcon.user_config.vote_map import VoteMapUserConfig
    monkeypatch.setattr(AutobalancerUserConfig,'load_from_db',lambda:SimpleNamespace(volunteer_command='!helpteam'))
    data={'enabled':True,'command_words':[{'words':['!teamvip'],'enabled':True}]}
    monkeypatch.setattr(ChatCommandsUserConfig,'load_from_db',lambda:SimpleNamespace(model_dump=lambda:data))
    for model in (RConChatCommandsUserConfig,VoteMapUserConfig):
        monkeypatch.setattr(model,'load_from_db',lambda:SimpleNamespace(model_dump=lambda:{'enabled':False}))
    assert service.status_command_conflict('!teamvip')
    assert service.status_command_conflict('!helpteam')
    assert not service.status_command_conflict('!rewards')
    data['enabled']=False
    assert not service.status_command_conflict('!teamvip')

@pytest.mark.parametrize('game',['hll','hllv'])
def test_observe_passes_canonical_support_scores_for_both_games(game):
    from rcon.vip_rewards.service import observe
    rcon=Mock()
    rcon.config.game=game
    rcon.get_gamestate.return_value={'num_allied_players':1,'num_axis_players':0}
    rcon.get_detailed_players.return_value={'players':{'a':{'name':'A','team':'allies','support':123}},'fail_count':0}
    players,counts,healthy=observe(rcon,setup().c)
    assert healthy and players['a']['support']==123
