"""Locale resolution and private voice identity links; no external calls."""

import hashlib
import json
import os
from pathlib import Path
import re

os.environ.setdefault("SERVER_NUMBER", "1")
os.environ.setdefault("HLL_MAINTENANCE_CONTAINER", "1")

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from rcon import voice_language as lang
from rcon.voice_language_text import BUILTIN, ENGLISH, TEXT, VERSION, valid_templates


@pytest.fixture()
def db():
    engine = create_engine("sqlite://")
    for item in (
        lang.VoiceVerifiedIdentity,
        lang.VoiceLanguagePreference,
        lang.VoiceTranslationCache,
    ):
        item.__table__.create(engine)
    with Session(engine) as session:
        yield session


def test_polish_report_unknown_target_then_explicit_french(db):
    message = "!admin Alex nie odpowiada na kanale głosowym naszej drużyny"
    locale = lang.report_language(db, message, discord_id="101", handles=["Alex"])
    assert locale == "pl"
    assert lang.preferred_language(db, discord_id="101") == "pl"
    assert lang.preferred_language(db, game_id="target-eos") == "en"
    assert lang.render(db, "notice_squad", "de+en").count(" / ") == 1
    assert lang.render(db, "notice_sent", locale, target="Alex").startswith(
        "Wysłaliśmy"
    )
    assert lang.render(db, "fixed", locale) == "Tak"
    lang.set_language(db, "fr-FR", discord_id="202")
    with pytest.raises(ValueError, match="Unverified"):
        lang.preferred_language(db, game_id="target-eos", discord_id="202")
    lang.link_verified(db, game_id="target-eos", discord_id="202")
    assert lang.preferred_language(db, game_id="target-eos") == "fr"
    assert lang.linked_discord_id(db, "target-eos") == "202"
    assert lang.render(db, "notice_squad", "fr").startswith("Ton escouade")


def test_explicit_preference_and_different_language_for_one_report(db):
    lang.set_language(db, "fr", game_id="target")
    lang.link_verified(db, game_id="target", discord_id="44")
    assert (
        lang.report_language(
            db, "Our squad leader does not reply in the squad channel.", discord_id="44"
        )
        == "en"
    )
    assert lang.report_language(db, "SL no mic", discord_id="44") == "fr"
    assert lang.preferred_language(db, discord_id="44") == "fr"
    lang.set_language(db, "nl", discord_id="44")
    assert lang.preferred_language(db, game_id="target") == "nl"


@pytest.mark.parametrize('locale',[None,'','not-a-language'])
def test_missing_or_invalid_voice_language_renders_english(db,locale):
    assert lang.render(db,'notice_squad',locale)==lang.render(db,'notice_squad','en')


def test_conflicting_links_never_move_preference(db):
    lang.link_verified(db, game_id="one", discord_id="1")
    lang.link_verified(db, game_id="one", discord_id="1")
    for game, discord in [("two", "1"), ("one", "2")]:
        with pytest.raises(ValueError, match="already linked"):
            lang.link_verified(db, game_id=game, discord_id=discord)
    assert lang.linked_game_id(db, "1") == "one"
    assert lang.linked_game_id(db, "2") is None


@pytest.mark.parametrize(
    "text",
    [
        "SL no mic",
        "Our squad has no microphone",
        "Onze squadleider ne répond pas on the radio",
    ],
)
def test_short_handle_or_mixed_text_does_not_change_preference(db, text):
    assert (
        lang.report_language(
            db, text, discord_id="1", handles=["Our squad has no microphone"]
        )
        == "en"
    )
    assert db.query(lang.VoiceLanguagePreference).count() == 0


def test_new_language_is_queued_once_and_render_never_calls_service(db):
    assert (
        lang.report_language(
            db, "El líder de nuestra escuadra nunca contesta por radio.", game_id="42"
        )
        == "es"
    )
    lang.set_language(db, "es", game_id="42")
    assert db.query(lang.VoiceTranslationCache).count() == 1
    assert lang.render(db, "question", "es", target="Alex") == lang.render(
        db, "question", "de+en", target="Alex"
    )
    cache = db.get(lang.VoiceTranslationCache, ("es", VERSION))
    cache.texts = {
        **ENGLISH,
        "question": "¿Funciona ahora la comunicación con {target}?",
    }
    assert (
        lang.render(db, "question", "es", target="Alex")
        == "¿Funciona ahora la comunicación con Alex?"
    )


def test_catalog_integrity_and_service_pin():
    for idx, locale in enumerate(BUILTIN):
        assert valid_templates({key: row[idx] for key, row in TEXT.items()}), locale
    reference = (
        Path(__file__).resolve().parents[1] / "discord_service/app/voice_translation.py"
    )
    pinned = re.search(
        r'CATALOG_HASH = "([a-f0-9]{64})"', reference.read_text(encoding="utf8")
    )[1]
    assert (
        pinned
        == hashlib.sha256(json.dumps(ENGLISH, sort_keys=True).encode()).hexdigest()
    )


def test_console_question_and_buttons_fit_without_case_number_or_chat_commands(db):
    question = lang.render(db, "question", "de+en", target="Mira", case="9876")
    hint = lang.render(db, "discord_reply", "de+en")
    assert question.count("Mira") == 1 and len(question + hint) < 110
    assert "!voice" not in hint and "9876" not in question
    assert lang.render(db, "fixed", "de+en") == "Ja / Yes"
    assert lang.render(db, "still_silent", "de+en") == "Nein / No"


def test_pc_reply_preserves_bare_words_and_polarity_in_translated_catalogs(db):
    for locale, yes, no in (
        ("de", "ja", "nein"),
        ("en", "yes", "no"),
        ("fr", "oui", "non"),
        ("pl", "tak", "nie"),
        ("nl", "ja", "nee"),
    ):
        text = lang.render(db, "pc_reply", locale, case="9876")
        words = text.casefold().split()
        assert yes in words and no + "." in words
        assert "!" not in text and "9876" not in text
    translated = {**ENGLISH, "pc_reply": "Responde con {yes} o {no}."}
    assert valid_templates(translated)
    language = lang.VoiceTranslationCache(
        language="es", version=VERSION, texts=translated, next_attempt=-1
    )
    db.add(language)
    db.flush()
    assert lang.render(db, "pc_reply", "es") == "Responde con Yes o No."
    assert lang.render(db, "pc_reply", "de+en") == "Chat: Ja/Yes · Nein/No"
    for invalid in ["Chat: !voice {yes} / !voice {no}", "Chat: {no} / {yes}", "Chat: sí / no"]:
        assert not valid_templates({**ENGLISH, "pc_reply": invalid})


def test_explicit_language_outside_detector_survives_cold_and_warmed_catalogs(db):
    lang.set_language(db, "eu", discord_id="71")
    locale = lang.report_language(db, "SL no mic", discord_id="71")
    assert locale == "eu"
    assert "Translation currently unavailable" in lang.render(db, "received", locale)
    cache = db.get(lang.VoiceTranslationCache, ("eu", VERSION))
    db.delete(cache)
    db.flush()
    # A status lookup without a new report re-queues a new catalog on upgrade.
    assert "Translation currently unavailable" in lang.render(db, "received", locale)
    cache = db.get(lang.VoiceTranslationCache, ("eu", VERSION))
    cache.texts = {**ENGLISH, "received": "Txostena jaso da."}
    assert lang.render(db, "received", locale) == "Txostena jaso da."
    assert lang.preferred_language(db, discord_id="71") == "eu"


def test_unrelated_short_player_handle_and_unambiguous_mixed_sentences(db):
    report = "Our squad leader does not reply in the squad channel."
    assert (
        lang.report_language(db, report, game_id="1", handles=["a", "A", "lea"]) == "en"
    )
    mixed = report + " Dowódca naszego oddziału nie odpowiada w komunikacji głosowej."
    assert lang.detect_language(mixed) is None
    assert lang.normalize_language("xxx") is None


@pytest.mark.parametrize(
    "bad",
    [
        "kick confirmed",
        "New address https://test.invalid/{target}",
        "{target.__class__}",
        "{target!r}",
        "{target} @everyone",
    ],
)
def test_corrupt_catalog_rejected(db, bad):
    assert not valid_templates({**ENGLISH, "notice_sent": bad})
