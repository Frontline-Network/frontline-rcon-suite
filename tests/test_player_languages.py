"""Shared preference and localized dispatch contracts without external messages."""
import os
os.environ.setdefault('SERVER_NUMBER','1')
os.environ.setdefault('HLL_MAINTENANCE_CONTAINER','1')
from contextlib import contextmanager
from contextlib import nullcontext
from unittest.mock import Mock
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from rcon import player_language as languages, player_messages as messages, player_message_catalog as catalog
from rcon import voice_language as voice
from rcon.models import MessageTemplate, PlayerMessageTranslation, PlayerMessageLocalizationAudit
from rcon.user_config.player_language import PlayerLanguageUserConfig

EOS='0002abcdefabcdefabcdefabcdefabcd'


@pytest.fixture
def database(monkeypatch):
    engine=create_engine('sqlite://')
    for cls in (MessageTemplate,PlayerMessageTranslation,PlayerMessageLocalizationAudit,
                voice.VoiceLanguagePreference,voice.VoiceVerifiedIdentity,voice.VoiceTranslationCache):
        cls.__table__.create(engine)
    @contextmanager
    def session():
        with Session(engine) as sess:
            yield sess
            sess.commit()
    for module in (languages,messages,catalog):
        monkeypatch.setattr(module,'enter_session',session)
    monkeypatch.setattr(PlayerLanguageUserConfig,'load_from_db',classmethod(lambda cls,**kw:cls(enabled=True)))
    from rcon.user_config.auto_mod_no_leader import AutoModNoLeaderUserConfig
    from rcon.user_config.auto_mod_solo_tank import AutoModNoSoloTankUserConfig
    from rcon.user_config.auto_mod_level import AutoModLevelUserConfig
    from rcon.user_config.auto_mod_seeding import AutoModSeedingUserConfig
    from rcon.user_config.autobalancer import AutobalancerUserConfig
    from rcon.user_config.rcon_server_settings import RconServerSettingsUserConfig
    from rcon.user_config.name_kicks import NameKickUserConfig
    from rcon.user_config.vac_game_bans import VacGameBansUserConfig
    from rcon.user_config.ban_tk_on_connect import BanTeamKillOnConnectUserConfig
    for cls in (AutoModNoLeaderUserConfig,AutoModNoSoloTankUserConfig,AutoModLevelUserConfig,
                AutoModSeedingUserConfig,AutobalancerUserConfig,RconServerSettingsUserConfig,
                NameKickUserConfig,VacGameBansUserConfig,BanTeamKillOnConnectUserConfig):
        monkeypatch.setattr(cls,'load_from_db',classmethod(lambda cls,**kw:cls()))
    return session


def test_chat_and_verified_discord_share_preference_without_attributing_reporter_language(database):
    with database() as s:
        voice.link_verified(s,game_id=EOS,discord_id='123')
        voice.set_language(s,'fr',discord_id='123')
    assert languages.get_profile(EOS.upper())['language']=='fr'
    api=Mock()
    assert languages.handle_chat_language(api,{'sub_content':'!lang en','player_id_1':EOS.upper()})
    api.message_player.assert_called_once()
    assert 'saved' in api.message_player.call_args.kwargs['message']
    with database() as s:
        assert voice.preferred_language(s,discord_id='123')=='en'
        assert voice.preferred_language(s,game_id='unlinked-target')=='de+en'
        voice.report_language(s,'Unser Squadleader antwortet seit mehreren Minuten nicht im Sprachkanal.',game_id=EOS)
    assert languages.get_profile(EOS)['language']=='en'


def test_uppercase_legacy_preference_survives_and_explicit_stays_first(database):
    with database() as s:
        s.add(voice.VoiceLanguagePreference(identity='game:'+EOS.upper(),language='fr',explicit=True,updated=1))
        s.add(voice.VoiceLanguagePreference(identity='game:'+EOS,language='en',explicit=False,updated=2))
    assert languages.get_profile(EOS)['language']=='fr'


def test_unverified_discord_cannot_set_target_preference(database):
    with database() as s:
        voice.set_language(s,'de',discord_id='123')
        with pytest.raises(ValueError,match='Unverified'):
            voice.preferred_language(s,game_id=EOS,discord_id='123')
    assert languages.get_profile(EOS)['language']=='de+en'


def test_catalog_variants_preserve_every_placeholder(database):
    templates=catalog.catalog()
    assert len(templates)>35
    for item in templates:
        messages.validate_translations(item['source'],item['translations'])


def test_save_preview_stale_edit_and_original_change(database):
    with database() as s:
        s.add(MessageTemplate(title='Voice rule',content='Please use squad voice.',category='REASON',updated_by='test'))
    item=next(t for t in catalog.catalog() if t['key'].startswith('manual:'))
    translations={'de':'Bitte nutze den Squad-Sprachkanal.','en':item['source'],'fr':'Veuillez utiliser le canal vocal de l’escouade.'}
    messages.save_translation(key=item['key'],source=item['source'],translations=translations,expected_revision=item['revision'],by='test')
    with pytest.raises(ValueError,match='changed'):
        messages.save_translation(key=item['key'],source=item['source'],translations=translations,expected_revision=item['revision'],by='test')
    languages.set_language(EOS,'fr')
    result=messages.localize_payload(EOS,item['source'],['REASON'])
    assert result==translations['fr'] and result.original==item['source']
    with database() as s:
        s.get(MessageTemplate,1).content='Updated custom rule.'
    updated=next(t for t in catalog.catalog() if t['key']==item['key'])
    assert updated['needs_review'] and updated['saved_translations']==translations
    assert messages.localize_payload(EOS,'Updated custom rule.',['REASON'])=='Updated custom rule.'


@pytest.mark.parametrize('translations',[{'en':'Missing variable'},{'en':'{player.__class__}'},{'de+en':'{player}'},{'zz':'{player}'}])
def test_bad_variants_are_rejected(translations):
    with pytest.raises(ValueError): messages.validate_translations('Hello {player}',translations)


def test_autobalancer_single_packet_for_known_and_unknown_language(database):
    from rcon.user_config.autobalancer import AutobalancerUserConfig
    from rcon.autobalancer.messages import send
    cfg=AutobalancerUserConfig(message_language='de+en')
    api=Mock(); api.message_player.return_value=True
    send(api,EOS,cfg,'disabled')
    api.message_player.assert_called_once()
    assert 'ausgeschaltet' in api.message_player.call_args.kwargs['message']
    assert 'disabled' in api.message_player.call_args.kwargs['message']
    api.reset_mock()
    languages.set_language(EOS,'en')
    send(api,EOS,cfg,'disabled')
    api.message_player.assert_called_once()
    assert 'disabled' in api.message_player.call_args.kwargs['message']
    assert 'ausgeschaltet' not in api.message_player.call_args.kwargs['message']


def test_automod_nested_reason_localizes_and_free_text_stays_untouched(database):
    from rcon.user_config.auto_mod_level import AutoModLevelUserConfig
    cfg=AutoModLevelUserConfig()
    languages.set_language(EOS,'fr')
    violation=cfg.min_level_message.format(level=20)
    original=cfg.force_kick_message.format(violation=violation)
    localized=messages.localize_payload(EOS,original,['REASON'],by='AutoMod_LevelThresholds')
    assert 'niveau 20' in localized and 'Access to' not in localized
    assert localized.original==original
    # Unrelated admin input is never guessed to be an automated template.
    assert messages.localize_payload(EOS,original,['REASON'],by='Admin')==original
    messages.audit_delivery(EOS,'kick',localized,localized,True)
    with database() as s:
        audit=s.scalar(select(PlayerMessageLocalizationAudit))
        assert audit.original==original and audit.delivered==localized and audit.outcome=='confirmed'


def test_custom_automod_source_is_preserved_without_stale_builtin_translation(database,monkeypatch):
    from rcon.user_config.auto_mod_no_leader import AutoModNoLeaderUserConfig
    cfg=AutoModNoLeaderUserConfig(warning_message='My custom rule {player_name}')
    monkeypatch.setattr(AutoModNoLeaderUserConfig,'load_from_db',classmethod(lambda cls,**kw:cfg))
    item=next(t for t in catalog.catalog() if t['key']=='automod.no_leader.warning')
    assert item['source']==cfg.warning_message and item['translations']=={}
    languages.set_language(EOS,'fr')
    assert messages.localize_payload(EOS,'My custom rule Alex',['MESSAGE'],by='AutoMod_NoLeaderWatch')=='My custom rule Alex'


def test_disabled_routing_preserves_old_autobalancer_behavior(database,monkeypatch):
    from rcon.user_config.autobalancer import AutobalancerUserConfig
    from rcon.autobalancer.messages import send
    monkeypatch.setattr(PlayerLanguageUserConfig,'load_from_db',classmethod(lambda cls,**kw:cls(enabled=False)))
    api=Mock(); api.message_player.return_value=True
    send(api,EOS,AutobalancerUserConfig(message_language='de+en'),'disabled')
    assert api.message_player.call_count==2


def test_old_uppercase_verified_link_cannot_be_claimed_by_another_discord(database):
    with database() as s:
        s.add(voice.VoiceVerifiedIdentity(game_id=EOS.upper(),discord_id='123'))
    with database() as s:
        with pytest.raises(ValueError,match='already linked'):
            voice.link_verified(s,game_id=EOS,discord_id='456')
        assert voice.linked_discord_id(s,EOS)=='123'


@pytest.mark.parametrize('action',['message','punish','kick','temp_ban','perma_ban'])
@pytest.mark.parametrize('outcome',['confirmed','rejected','timeout'])
def test_real_dispatch_preserves_action_duration_and_never_repeats(database,monkeypatch,action,outcome):
    from rcon.rcon import Rcon
    from rcon.commands import ServerCtl
    import rcon.rcon as runtime
    import rcon.leadership_vote.storage as guards
    with database() as s:
        row=MessageTemplate(title='Rule',content='Please use squad voice.',category='MESSAGE' if action=='message' else 'REASON',updated_by='test')
        s.add(row); s.flush(); identity=row.id
    item=next(t for t in catalog.catalog() if t['key']==f'manual:{identity}')
    messages.save_translation(key=item['key'],source=item['source'],translations={'en':item['source'],'fr':'Veuillez utiliser le canal vocal de l’escouade.'},expected_revision=item['revision'],by='test')
    languages.set_language(EOS,'fr')
    monkeypatch.setattr(guards,'before_manual_action',lambda *a,**k:None)
    monkeypatch.setattr(runtime,'invalidates',lambda *a,**k:nullcontext())
    monkeypatch.setattr(runtime,'player_ban_lock',lambda *a,**k:nullcontext())
    monkeypatch.setattr(runtime,'safe_save_player_action',Mock())
    calls=[]
    def transport(*args,**kwargs):
        calls.append((args,kwargs))
        if outcome=='timeout': raise TimeoutError('synthetic transport timeout')
        return outcome=='confirmed'
    native='message_player' if action=='message' else action
    monkeypatch.setattr(ServerCtl,native,transport)
    instance=Rcon.__new__(Rcon)
    actor='BLACKLIST #123/20261127T000000000000Z: Test' if action in ('temp_ban','perma_ban') else 'Admin'
    values={'player_id':EOS,'by':actor}
    values['message' if action=='message' else 'reason']=item['source']
    if action=='temp_ban': values['duration_hours']=7
    if outcome=='timeout':
        with pytest.raises(TimeoutError): getattr(instance,native)(**values)
    else:
        assert getattr(instance,native)(**values) is (outcome=='confirmed')
    assert len(calls)==1
    args,kwargs=calls[0]
    assert any('Veuillez utiliser' in str(v) for v in args)
    if action=='temp_ban': assert args[2]==7 and kwargs['admin_name']==actor
    if action=='perma_ban': assert kwargs['admin_name']==actor
    with database() as s:
        audit=s.scalar(select(PlayerMessageLocalizationAudit))
        assert audit.original==item['source'] and 'Veuillez utiliser' in audit.delivered
        assert audit.outcome==('uncertain' if outcome=='timeout' else outcome)


def test_autobalancer_uses_the_passed_config_snapshot(database):
    from rcon.autobalancer.messages import send
    from rcon.user_config.autobalancer import AutobalancerUserConfig
    cfg=AutobalancerUserConfig()
    cfg.messages_en.volunteer_request='Custom invitation: {target_team} within {seconds}s via !balance'
    languages.set_language(EOS,'en')
    api=Mock(); api.message_player.return_value=True
    send(api,EOS,cfg,'volunteer_request',target_team='Axis',seconds=30)
    assert 'Custom invitation' in api.message_player.call_args.kwargs['message']
    assert api.message_player.call_count==1


def test_ambiguous_placeholders_cannot_cause_pattern_backtracking():
    assert messages._match('prefix {a}{b}{c} end','prefix '+'x'*4000+' missing') is None
