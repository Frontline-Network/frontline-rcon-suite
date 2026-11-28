"""One preference store for chat, Discord, moderation and automation.

The historical voice tables are intentionally retained: upgrading does not copy,
reset or disconnect previously verified identities or explicit preferences.
"""
import logging
import re
from sqlalchemy import select, func, or_
from rcon.models import enter_session
from rcon import voice_language as storage

logger = logging.getLogger(__name__)


def game_identity(player_id):
    value = str(player_id or "").strip()
    if re.fullmatch(r"[0-9a-fA-F]{32}", value):
        return value.lower()
    return value


def profile_in_session(sess, *, player_id=None, discord_id=None):
    ids = storage._identities(sess, game_identity(player_id), discord_id)
    # Read old upper-case EOS preferences as well; never infer Steam/platform
    # identities from EOS or from an unverified Discord account.
    eos_ids=[v for v in ids if v.startswith('game:') and re.fullmatch(r'[0-9a-fA-F]{32}',v[5:])]
    row = sess.scalar(select(storage.VoiceLanguagePreference).where(or_(
        storage.VoiceLanguagePreference.identity.in_(ids),
        func.lower(storage.VoiceLanguagePreference.identity).in_([v.lower() for v in eos_ids])
    )
    ).order_by(storage.VoiceLanguagePreference.explicit.desc(),
               storage.VoiceLanguagePreference.updated.desc(),
               storage.VoiceLanguagePreference.identity).limit(1))
    if row is None:
        from rcon.user_config.player_language import PlayerLanguageUserConfig
        if PlayerLanguageUserConfig.load_from_db().enabled:
            from rcon.player_country_language import country_hint
            game_id = next((v[5:] for v in ids if v.startswith('game:')), None)
            hint = country_hint(sess, game_id)
            if hint:
                return hint
    return {"language": row.language if row else storage.FALLBACK_LANGUAGE,
            "explicit": bool(row.explicit) if row else False,
            "source": ("selected" if row.explicit else "detected") if row else "fallback",
            "updated": row.updated if row else None}


def get_profile(player_id):
    if not game_identity(player_id) or len(str(player_id)) > 100:
        raise ValueError("Invalid player identity")
    with enter_session() as sess:
        return profile_in_session(sess, player_id=player_id)


def preferred_language(player_id):
    try:
        return get_profile(player_id)["language"]
    except Exception:
        logger.warning("Player language unavailable; using English fallback")
        return storage.FALLBACK_LANGUAGE


def set_language(player_id, language):
    player_id = game_identity(player_id)
    if not player_id or len(player_id) > 100:
        raise ValueError("Invalid player identity")
    with enter_session() as sess:
        storage.set_language(sess, language, game_id=player_id)
        return profile_in_session(sess, player_id=player_id)


def handle_chat_language(rcon, event):
    text = str(event.get("sub_content") or "").strip()
    match = re.fullmatch(r"!(?:lang|language)(?:\s+(\S+))?\s*", text, re.I)
    if not match:
        return False
    player_id = event.get("player_id_1")
    if not player_id:
        return True
    try:
        if match[1]:
            language = storage.normalize_language(match[1])
            if not language or language == storage.DEFAULT:
                raise ValueError("Unknown language")
            profile = set_language(player_id, language)
            texts = {"de": "Deine Sprache wurde gespeichert: {language}.",
                     "en": "Your language has been saved: {language}.",
                     "fr": "Votre langue a été enregistrée : {language}."}
            body = texts.get(language, texts["en"]).format(language=profile["language"])
        else:
            profile = get_profile(player_id)
            body = "Sprache / Language: " + profile["language"] + "\n!lang de · !lang en · !lang fr"
    except ValueError:
        body = "Sprache wählen / Choose language: !lang de · !lang en · !lang fr"
    except Exception:
        logger.exception("Could not store player language")
        body = "Sprache konnte nicht gespeichert werden. / Could not save your language."
    rcon.message_player(player_id=player_id, message=body, save_message=False)
    return True
