"""Country hints are provisional, account-bound and never change ban identity."""
import datetime
import json
from types import SimpleNamespace
from unittest.mock import Mock
import pytest
from sqlalchemy import text
from tests.test_player_languages import database, EOS
from rcon import player_language as languages, voice_language as voice, steam_utils
from rcon.user_config.player_language import PlayerLanguageUserConfig

STEAM = "76561198000000001"


def cached_country(database, country="DE", *, returned_id=STEAM, native=False):
    with database() as session:
        session.execute(text('INSERT INTO steam_id_64 VALUES (1,:identity,:steam)'),
                        {"identity": STEAM if native else EOS, "steam": None if native else STEAM})
        if not native:
            session.execute(text('INSERT INTO steam_id_64 VALUES (2,:steam,NULL)'), {"steam": STEAM})
        session.execute(text('INSERT INTO steam_info VALUES (1,:account,:profile,:country,:updated)'),
                        {"account": 1 if native else 2,
                         "profile": json.dumps({"steamid": returned_id, **({"loccountrycode": country} if country else {})}),
                         "country": country, "updated": datetime.datetime(2026, 11, 27, 12)})


@pytest.mark.parametrize("country,expected", [("DE","de"),("AT","de"),("FR","fr"),("GB","en"),("US","en"),("PL","pl")])
def test_linked_steam_country_is_used_for_eos_without_an_existing_preference(database,country,expected):
    cached_country(database,country)
    value=languages.get_profile(EOS.upper())
    assert value["language"]==expected and value["source"]=="steam_country"
    assert value["country"]==country and value["explicit"] is False
    with database() as session:
        assert session.query(voice.VoiceLanguagePreference).count()==0


@pytest.mark.parametrize("country", ["CH","BE","CA",None,"private","ZZ"])
def test_ambiguous_or_unavailable_country_keeps_bilingual_fallback(database,country):
    cached_country(database,country)
    assert languages.get_profile(EOS)["language"]=="de+en"


def test_manual_and_own_report_preferences_beat_country(database):
    cached_country(database,"FR")
    with database() as session:
        session.add(voice.VoiceLanguagePreference(identity="game:"+EOS,language="de",explicit=False,updated=1))
    assert languages.get_profile(EOS)["source"]=="detected"
    assert languages.get_profile(EOS)["language"]=="de"
    languages.set_language(EOS,"en")
    assert languages.get_profile(EOS)["language"]=="en" and languages.get_profile(EOS)["explicit"]


def test_wrong_steam_profile_cannot_supply_an_eos_country(database):
    cached_country(database,"FR",returned_id="76561198000000002")
    assert languages.get_profile(EOS)["language"]=="de+en"


def test_native_steam_country_and_disabled_routing(database,monkeypatch):
    cached_country(database,"DE",native=True)
    assert languages.get_profile(STEAM)["language"]=="de"
    monkeypatch.setattr(PlayerLanguageUserConfig,"load_from_db",classmethod(lambda cls:cls(enabled=False)))
    assert languages.get_profile(STEAM)["language"]=="de+en"


def test_new_missing_country_does_not_resurrect_an_older_country(database):
    cached_country(database,"DE")
    with database() as session:
        session.execute(text('INSERT INTO steam_info VALUES (2,1,:profile,:country,:updated)'),
                        {"profile":json.dumps({"steamid":STEAM}),"country":"FR",
                         "updated":datetime.datetime(2026,11,27,14)})
    assert languages.get_profile(EOS)["language"]=="de+en"


def test_eos_refresh_uses_steam_for_profile_but_preserves_native_ban_lookup(monkeypatch):
    profile={"steamid":STEAM,"loccountrycode":"FR"}
    fetch=Mock(return_value=profile); bans=Mock(return_value=None)
    monkeypatch.setattr(steam_utils,"fetch_steam_player_summary_player",fetch)
    monkeypatch.setattr(steam_utils,"fetch_steam_bans_player",bans)
    existing=SimpleNamespace(profile=None,country=None,bans=None,updated=None)
    player=SimpleNamespace(player_id=EOS,steam_id=STEAM,steaminfo=existing)
    steam_utils.update_missing_old_steam_info_single_player(Mock(),player)
    fetch.assert_called_once_with(STEAM)
    bans.assert_called_once_with(EOS)
    assert player.player_id==EOS and existing.profile==profile and existing.country=="FR"


def test_steam_refresh_clears_removed_public_country_and_rejects_wrong_identity(monkeypatch):
    fetch=Mock(return_value={"steamid":STEAM,"communityvisibilitystate":3})
    monkeypatch.setattr(steam_utils,"fetch_steam_player_summary_player",fetch)
    monkeypatch.setattr(steam_utils,"fetch_steam_bans_player",lambda *a:None)
    info=SimpleNamespace(profile={},country="DE",bans={},updated=None)
    player=SimpleNamespace(player_id=EOS,steam_id=STEAM,steaminfo=info)
    steam_utils.update_missing_old_steam_info_single_player(Mock(),player)
    assert info.country is None
    fetch.return_value={"steamid":"76561198000000002","loccountrycode":"FR"}
    assert steam_utils._fetch_linked_player_summary(player) is None


@pytest.mark.parametrize("identity", ["557026465853991309","25332748000000000",None])
def test_console_or_missing_platform_id_is_not_sent_to_steam(monkeypatch,identity):
    fetch=Mock()
    monkeypatch.setattr(steam_utils,"fetch_steam_player_summary_player",fetch)
    assert steam_utils._fetch_linked_player_summary(SimpleNamespace(player_id=EOS,steam_id=identity)) is None
    fetch.assert_not_called()
