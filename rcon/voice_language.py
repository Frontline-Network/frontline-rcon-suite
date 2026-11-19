"""Per-installation preferences, verified identities and immediate localized voice copy."""

import re
import time
import unicodedata
from functools import lru_cache

from sqlalchemy import Boolean, Float, JSON, String, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Mapped, mapped_column

from rcon.models import Base
from rcon.voice_language_text import BUILTIN, TEXT, VERSION, valid_templates

DEFAULT = "de+en"

# Accept only known ISO 639-1 language identifiers plus the common additional
# locale tags below. This bounds cache entries and prevents invented language
# names from generating customer-funded model jobs.
LANGUAGES = frozenset("""
aa ab ae af ak am an ar as av ay az ba be bg bh bi bm bn bo br bs ca ce
ch co cr cs cu cv cy da de dv dz ee el en eo es et eu fa ff fi fj fo fr fy
ga gd gl gn gu gv ha he hi ho hr ht hu hy hz ia id ie ig ii ik io is it iu
ja jv ka kg ki kj kk kl km kn ko kr ks ku kv kw ky la lb lg li ln lo lt lu
lv mg mh mi mk ml mn mr ms mt my na nb nd ne ng nl nn no nr nv ny oc oj om
or os pa pi pl ps pt qu rm rn ro ru rw sa sc sd se sg si sk sl sm sn so sq
sr ss st su sv sw ta te tg th ti tk tl tn to tr ts tt tw ty ug uk ur uz ve
vi vo wa wo xh yi yo za zh zu fil ceb cmn gsw haw hmn kur yue
""".split())


class VoiceLanguagePreference(Base):
    __tablename__ = "voice_language_preference"
    identity: Mapped[str] = mapped_column(String(120), primary_key=True)
    language: Mapped[str] = mapped_column(String(16))
    explicit: Mapped[bool] = mapped_column(Boolean)
    updated: Mapped[float] = mapped_column(Float)


class VoiceVerifiedIdentity(Base):
    __tablename__ = "voice_verified_identity"
    discord_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    game_id: Mapped[str] = mapped_column(String(100), unique=True)


class VoiceTranslationCache(Base):
    __tablename__ = "voice_translation_cache"
    language: Mapped[str] = mapped_column(String(16), primary_key=True)
    version: Mapped[str] = mapped_column(String(24), primary_key=True)
    texts: Mapped[dict] = mapped_column(JSON)
    next_attempt: Mapped[float] = mapped_column(Float)


def normalize_language(value):
    if not isinstance(value, str):
        return None
    value = value.strip().lower().replace("_", "-")
    if value == DEFAULT:
        return value
    if not re.fullmatch(r"[a-z]{2,3}(?:-[a-z]{2,4})?", value):
        return None
    base = value.split("-")[0]
    if base not in LANGUAGES:
        return None
    if value in {"zh-cn", "zh-sg", "zh-hans"}:
        return "zh-hans"
    if value in {"zh-tw", "zh-hk", "zh-mo", "zh-hant"}:
        return "zh-hant"
    return base


def _insert(sess, model):
    dialect = sess.get_bind().dialect.name
    if dialect == "postgresql":
        return pg_insert(model)
    if dialect == "sqlite":
        return sqlite_insert(model)
    raise ValueError("Unsupported voice language database")


def linked_game_id(sess, discord_id):
    return sess.scalar(
        select(VoiceVerifiedIdentity.game_id).where(
            VoiceVerifiedIdentity.discord_id == str(discord_id)
        )
    )


def linked_discord_id(sess, game_id):
    return sess.scalar(
        select(VoiceVerifiedIdentity.discord_id).where(
            VoiceVerifiedIdentity.game_id == str(game_id)
        )
    )


def link_verified(sess, *, game_id, discord_id):
    """Caller has already consumed a challenge for BOTH identities in this transaction."""
    game, discord = str(game_id or "").strip(), str(discord_id or "").strip()
    if not (0 < len(game) <= 100 and re.fullmatch(r"[0-9]{1,32}", discord)):
        raise ValueError("Invalid voice account identity")
    statement = _insert(sess, VoiceVerifiedIdentity).values(
        discord_id=discord, game_id=game
    )
    sess.execute(statement.on_conflict_do_nothing())
    if linked_game_id(sess, discord) != game:
        raise ValueError("Voice account already linked to a different identity")


def _identities(sess, game_id, discord_id):
    game = str(game_id or "").strip()
    discord = str(discord_id or "").strip()
    if game and discord:
        if linked_game_id(sess, discord) != game:
            raise ValueError("Unverified voice identity pair")
    elif game:
        discord = linked_discord_id(sess, game)
    elif discord:
        game = linked_game_id(sess, discord)
    return [
        k
        for k in (
            f"game:{game}" if game else None,
            f"discord:{discord}" if discord else None,
        )
        if k
    ]


def preferred_language(sess, *, game_id=None, discord_id=None):
    ids = _identities(sess, game_id, discord_id)
    row = sess.scalar(
        select(VoiceLanguagePreference.language)
        .where(VoiceLanguagePreference.identity.in_(ids))
        .order_by(
            VoiceLanguagePreference.explicit.desc(),
            VoiceLanguagePreference.updated.desc(),
            VoiceLanguagePreference.identity,
        )
        .limit(1)
    )
    return row or DEFAULT


def _warm(sess, locale):
    if locale not in (*BUILTIN, DEFAULT):
        statement = _insert(sess, VoiceTranslationCache).values(
            language=locale, version=VERSION, texts={}, next_attempt=0
        )
        sess.execute(statement.on_conflict_do_nothing())


def _remember(sess, locale, game_id, discord_id, *, explicit):
    # Record each observation on its actual identity. A verified link resolves both
    # preferences on read (explicit wins, then most recent), without copying history.
    _identities(sess, game_id, discord_id)
    identity = (
        f"discord:{discord_id}"
        if discord_id
        else f"game:{game_id}" if game_id else None
    )
    if identity:
        values = {"language": locale, "updated": time.time(), "explicit": explicit}
        statement = _insert(sess, VoiceLanguagePreference).values(
            identity=identity, **values
        )
        sess.execute(
            statement.on_conflict_do_update(
                index_elements=["identity"],
                set_=values,
                where=None if explicit else VoiceLanguagePreference.explicit.is_(False),
            )
        )
    _warm(sess, locale)


def set_language(sess, locale, *, game_id=None, discord_id=None):
    locale = normalize_language(locale)
    if not locale:
        raise ValueError("Expected a language code")
    if not (game_id or discord_id):
        raise ValueError("Missing voice identity")
    _remember(sess, locale, game_id, discord_id, explicit=True)
    return locale


@lru_cache(maxsize=1)
def _detector():
    from langdetect.detector_factory import DetectorFactory, PROFILES_DIRECTORY

    factory = DetectorFactory()
    factory.load_profile(PROFILES_DIRECTORY)
    factory.seed = 0
    return factory


def _classify_words(words):
    from langdetect.lang_detect_exception import LangDetectException

    # Short roster labels and mixed gaming shorthand are unreliable. CJK
    # languages are not space-delimited, so count meaningful characters there.
    letters = "".join(words)
    continuous = re.findall(
        r"[\u3040-\u30ff\u3400-\u9fff\uac00-\ud7af\u0e00-\u0e7f]", letters
    )
    if len(continuous) < 8 and (len(words) < 4 or len(letters) < 16):
        return None
    try:
        detector = _detector().create()
        detector.append(" ".join(words))
        scores = detector.get_probabilities()
    except LangDetectException:
        return None
    if not scores or scores[0].prob < 0.93:
        return None
    return normalize_language(scores[0].lang)


def detect_language(text, handles=()):
    clean = unicodedata.normalize("NFKC", str(text or "")[:4000])
    for name in sorted({str(h) for h in handles if h}, key=len, reverse=True):
        clean = re.sub(r"(?<!\w)" + re.escape(name) + r"(?!\w)", " ", clean, flags=re.I)
    clean = re.sub(
        r"^\s*!admin\b|https?://\S+|<@!?\d+>|\b(?:sl|voip|mic|comms?|cmdr|squadleader)\b",
        " ",
        clean,
        flags=re.I,
    )
    chunks = re.split(r"[.!?;。！？/\n]+", clean)
    words = [re.findall(r"[^\W\d_]+", part) for part in chunks if part.strip()]
    all_words = [word for chunk in words for word in chunk]
    detected = _classify_words(all_words)
    if detected and len(words) > 1:
        if any(
            language and language != detected
            for language in map(_classify_words, words)
        ):
            return None
    return detected


def report_language(sess, text, *, game_id=None, discord_id=None, handles=()):
    locale = detect_language(text, handles)
    if locale:
        _remember(sess, locale, game_id, discord_id, explicit=False)
        return locale
    return preferred_language(sess, game_id=game_id, discord_id=discord_id)


def render(sess, key, locale, *, target="", case=""):
    """Instant only: no network or model call in an RCON tick or Discord interaction."""
    if key not in TEXT:
        raise ValueError("Unknown voice message key")
    locale = normalize_language(locale) or DEFAULT
    if locale in BUILTIN:
        template = TEXT[key][BUILTIN.index(locale)]
    else:
        template = None
        if locale != DEFAULT:
            cache = sess.get(VoiceTranslationCache, (locale, VERSION))
            if cache is None:
                # A deployment may have updated the catalog since the recipient
                # last wrote a report. Warm the new version without delaying them.
                _warm(sess, locale)
            elif valid_templates(cache.texts):
                template = cache.texts[key]
        if template is None:
            template = " / ".join(TEXT[key][:2])
            if locale != DEFAULT and key in {"received", "updated"}:
                template += "\nÜbersetzung derzeit nicht verfügbar. / Translation currently unavailable."
    # Prevent handles from inserting extra lines, game commands or Discord mentions.
    name = " ".join(str(target or "").split())[:100]
    name = "".join(
        c for c in name if unicodedata.category(c) not in {"Cc", "Cf"}
    ).replace("@", "@\u200b")
    result = template.format(
        target=name, case=re.sub(r"[^a-zA-Z0-9_-]", "", str(case or ""))[:48]
    )
    if locale == DEFAULT and key in {"notice_sent", "notice_external"}:
        result += "\nSprache / Language → Discord: Meine Sprache / My language"
    return result
