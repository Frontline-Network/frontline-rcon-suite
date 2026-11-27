"""Recipient-specific templates. No translation service or extra RCON send occurs here."""
from datetime import datetime, timezone
import hashlib
import json
import logging
import re
from string import Formatter
from sqlalchemy import select
from rcon.models import (enter_session, MessageTemplate, PlayerMessageTranslation,
                         PlayerMessageLocalizationAudit)
from rcon.player_language import preferred_language, game_identity
from rcon.user_config.player_language import PlayerLanguageUserConfig
from rcon.voice_language import normalize_language
from rcon.utils import get_server_number

logger = logging.getLogger(__name__)


class LocalizedText(str):
    def __new__(cls, text, *, original, key, language, variants=None):
        value = super().__new__(cls, text)
        value.original, value.template_key, value.language = original, key, language
        value.variants = variants or {}
        return value


def source_hash(source):
    return hashlib.sha256(source.encode()).hexdigest()


def fields(text):
    values = set()
    for _, name, spec, conversion in Formatter().parse(text):
        if name is not None:
            if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", name) or "{" in spec:
                raise ValueError("Only named, flat placeholders are supported")
            values.add((name, spec, conversion))
    return values


def validate_translations(source, translations):
    if not isinstance(translations, dict) or len(translations) > 32:
        raise ValueError("Expected at most 32 language variants")
    required = fields(source)
    clean = {}
    for locale, text in translations.items():
        language = normalize_language(locale)
        if not language or language == "de+en" or language != locale:
            raise ValueError("Expected a normalized language code")
        if not isinstance(text, str) or not text.strip() or len(text) > 4000:
            raise ValueError("Language variants must contain 1 to 4000 characters")
        if fields(text) != required:
            raise ValueError("Every translation must preserve all placeholders and formats")
        clean[language] = text
    return clean


def routing_enabled():
    try:
        return PlayerLanguageUserConfig.load_from_db().enabled
    except Exception:
        logger.warning('Language routing settings unavailable; retaining module settings')
        return False


def stored_key(key):
    return key if key.startswith("manual:") else f"{get_server_number()}:{key}"


def _format(text, variables):
    try:
        return text.format(**variables)
    except (KeyError, ValueError, IndexError):
        return text


def render(key, source, *, player_id, variables=None, defaults=None, enabled=None, binding_hash=None, locale_variables=None, draft=None):
    variables = variables or {}
    original = _format(source, {k:getattr(v, "original", v) for k,v in variables.items()})
    try:
        if not (routing_enabled() if enabled is None else enabled):
            return original
        variants = dict(defaults or {})
        with enter_session() as sess:
            row = sess.get(PlayerMessageTranslation, stored_key(key))
            if row and row.source_hash == (binding_hash or source_hash(source)) and row.source_content == source:
                variants.update(row.translations)
        if draft is not None:
            variants = {**(defaults or {}), **validate_translations(source,draft)}
        language = preferred_language(player_id)
        formatted = {locale:_format(text, {k:(v.variants.get(locale, v.original) if isinstance(v, LocalizedText) else v)
                                                   for k,v in {**variables, **(locale_variables or {}).get(locale,{})}.items()})
                     for locale,text in variants.items()}
        if language in formatted:
            selected = formatted[language]
            resolved = language
        else:
            selected = " / ".join(dict.fromkeys(formatted[l] for l in ("de", "en") if l in formatted)) or original
            resolved = "de+en" if "de" in formatted and "en" in formatted else next((l for l in ("de", "en") if l in formatted), "legacy")
        return LocalizedText(selected, original=original, key=key, language=resolved, variants=formatted)
    except Exception:
        # Language routing must not turn a working moderation command into an
        # error or change its action/duration. Keep customized legacy content.
        logger.warning("Player template unavailable; retaining existing text")
        return original


def localize_manual(player_id, text, category, player_name=None):
    if isinstance(text, LocalizedText) or not isinstance(text, str) or not text:
        return text
    try:
        if not routing_enabled():
            return text
        with enter_session() as sess:
            rows = list(sess.scalars(select(MessageTemplate.id).where(
                MessageTemplate.category.in_(category), MessageTemplate.content == text)))
        if len(rows) != 1:
            return text
        return render(f"manual:{rows[0]}", text, player_id=player_id,
                      variables={"player_id":player_id,"player_name":player_name or ""}, enabled=True)
    except Exception:
        logger.warning("Moderation template lookup unavailable; retaining original")
        return text


def audit_delivery(player_id, action, localized, delivered, result):
    if not isinstance(localized, LocalizedText):
        return
    try:
        with enter_session() as sess:
            sess.add(PlayerMessageLocalizationAudit(server_number=int(get_server_number()),
                player_id=game_identity(player_id), action=action, template_key=localized.template_key,
                language=localized.language, original=localized.original, delivered=str(delivered),
                outcome="confirmed" if result is True else "rejected" if result is False else "uncertain"))
    except Exception:
        # A missing audit acknowledgement must never replay the game command.
        logger.exception("Could not record localized message outcome")


def dispatch(player_id,action,localized,delivered,send):
    try:
        result=send()
    except BaseException:
        audit_delivery(player_id,action,localized,delivered,None)
        raise
    audit_delivery(player_id,action,localized,delivered,result)
    return result


def save_translation(*, key, source, translations, expected_revision, by):
    if not isinstance(key, str) or not re.fullmatch(r"(?:manual:\d+|[a-z][a-z0-9_.]{1,120})", key):
        raise ValueError("Invalid template key")
    clean = validate_translations(source, translations)
    from rcon.player_message_catalog import catalog
    current = next((t for t in catalog() if t["key"] == key), None)
    if not current or current["source"] != source or current["revision"] != expected_revision:
        raise ValueError("Template changed; reload before saving translations")
    with enter_session() as sess:
        row = sess.get(PlayerMessageTranslation, stored_key(key), with_for_update=True)
        # Check the stored revision again under the row lock (including variants).
        revision = template_revision(source, row, current['source_hash'])
        if revision != expected_revision:
            raise ValueError("Template changed; reload before saving translations")
        if row is None:
            row = PlayerMessageTranslation(key=stored_key(key))
            sess.add(row)
        row.source_content, row.source_hash = source, current['source_hash']
        row.translations, row.updated_by = clean, by
        row.updated_at = datetime.now(timezone.utc)
    return True


def template_revision(source, row, binding_hash=None):
    record = {"source":source,"saved_source":row.source_content if row else None,
              "translations":row.translations if row else {}, "binding_hash":binding_hash or source_hash(source)}
    return source_hash(json.dumps(record, sort_keys=True, ensure_ascii=False))


def _match(source, text):
    """Reverse only the module's own flat placeholders, never arbitrary format code."""
    # Deterministic delimiter scans keep customized templates from introducing
    # regex backtracking into a moderation tick. Ambiguous captures fall back.
    if len(source)>4000 or len(text)>8000: return None
    try:
        tokens=list(Formatter().parse(source))
        values, position = {}, 0
        for index,(literal, name, spec, conversion) in enumerate(tokens):
            if not text.startswith(literal,position): return None
            position+=len(literal)
            if name is not None:
                if spec or conversion or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]*',name):
                    return None
                if index+1<len(tokens):
                    delimiter=tokens[index+1][0]
                    if not delimiter: return None
                    end=text.find(delimiter,position)
                    if end<0: return None
                else: end=len(text)
                value=text[position:end]
                if name in values and values[name]!=value: return None
                values[name]=value
                position=end
        return values if position==len(text) else None
    except ValueError:
        return None


def _fragment(player_id, text, definitions, allow_split=True):
    # Nested rule explanations must use the same locale as their outer warning.
    if allow_split and '\n' in text:
        parts=[]
        for line in text.splitlines(keepends=True):
            body=line.rstrip('\r\n')
            parts.extend((_fragment(player_id,body,definitions,False),line[len(body):]))
        locales=set().union(*(p.variants for p in parts if isinstance(p,LocalizedText)))
        variants={locale:''.join(p.variants.get(locale,p.original) if isinstance(p,LocalizedText) else p for p in parts)
                  for locale in locales}
        return LocalizedText(text,original=text,key='fragment',language='legacy',variants=variants)
    if allow_split and ', ' in text:
        parts=[_fragment(player_id,part,definitions,False) for part in text.split(', ')]
        if all(isinstance(part,LocalizedText) for part in parts):
            locales=set().union(*(part.variants for part in parts))
            variants={locale:', '.join(part.variants.get(locale,part.original) for part in parts) for locale in locales}
            return LocalizedText(text,original=text,key='fragment',language='legacy',variants=variants)
    candidates = [(d,_match(d['source'],text)) for d in definitions
                  if d['group']=='automod' and d['action'] in ('violation','min_level','max_level')]
    candidates = [(d,v) for d,v in candidates if v is not None]
    if candidates:
        rendered=[render(d['key'],d['source'],player_id=player_id,variables=values,
                         defaults=d['defaults'],enabled=True) for d,values in candidates]
        # Stock role/weapon fragments share wording. Use them only when every
        # matching binding produces exactly the same language variants.
        first=rendered[0]
        if len(rendered)==1 or all(isinstance(value,LocalizedText) and isinstance(first,LocalizedText)
                                  and value.variants==first.variants and str(value)==str(first) for value in rendered):
            return first
    if allow_split and ', ' in text:
        parts = [_fragment(player_id, part, definitions, False) for part in text.split(', ')]
        variants={locale:', '.join(p.variants.get(locale,p.original) if isinstance(p,LocalizedText) else p for p in parts)
                  for locale in ('de','en','fr')}
        return LocalizedText(text,original=text,key='fragment',language='legacy',variants=variants)
    return text


def _level_announcement_values(definition,text,definitions):
    """Recover only independently identifiable rule lines in the adjacent block."""
    block='{min_level_msg}{max_level_msg}{level_thresholds_msg}'
    source=definition['source']
    if definition['key']!='automod.level.announcement' or source.count(block)!=1:
        return None
    try:
        prefix,suffix=(part.format() for part in source.split(block))
    except (ValueError,KeyError,IndexError):
        return None
    if not text.startswith(prefix) or not text.endswith(suffix): return None
    body=text[len(prefix):len(text)-len(suffix) if suffix else None]
    values={'min_level_msg':'','max_level_msg':'','level_thresholds_msg':''}
    for line in body.splitlines(keepends=True):
        matches=[d for d in definitions if d['action'] in ('min_level','max_level','violation')
                 and _match(d['source'],line.rstrip('\r\n')) is not None]
        if len(matches)!=1: return None
        name={'min_level':'min_level_msg','max_level':'max_level_msg','violation':'level_thresholds_msg'}[matches[0]['action']]
        values[name]+=line
    # Reject reordered/ambiguous custom blocks instead of guessing their meaning.
    return values if _format(source,values)==text else None


def localize_automated(player_id, text, *, group='automod', prefix=None):
    if isinstance(text,LocalizedText) or not isinstance(text,str):
        return text
    try:
        if not routing_enabled(): return text
        from rcon.player_message_catalog import bindings
        definitions=[d for d in bindings() if d['group']==group and (prefix is None or d['key'].startswith(prefix))]
        candidates=[(d,_level_announcement_values(d,text,definitions) if d['key']=='automod.level.announcement' else _match(d['source'],text)) for d in definitions
                    if d['source'] and d['group'] in ('automod','autobalancer')
                    and d['action'] not in ('violation','min_level','max_level')]
        candidates=[(d,v) for d,v in candidates if v is not None]
        if len(candidates)!=1: return text
        d,values=candidates[0]
        if 'violation' in values:
            values['violation']=_fragment(player_id,values['violation'],definitions)
        for name in ('min_level_msg','max_level_msg','level_thresholds_msg'):
            if name in values:
                values[name]=_fragment(player_id,values[name],definitions)
        return render(d['key'],d['source'],player_id=player_id,variables=values,defaults=d['defaults'],enabled=True,
                      binding_hash=d.get('source_hash'))
    except Exception:
        logger.warning('Automated message localization unavailable; retaining existing text')
        return text


def localize_payload(player_id,text,category,player_name=None,by=''):
    origins={'AutoMod_NoLeaderWatch':'no_leader','AutoMod_NoSoloTank':'solo_tank',
             'AutoMod_LevelThresholds':'level','AutoMod_SeedingRules':'seeding',
             'NAME_KICK':'name','VAC BOT':'vac','HATERS GONNA HATE':'teamkill'}
    origin=origins.get(str(by).removesuffix('-DryRun'))
    if origin:
        return localize_automated(player_id,text,prefix='automod.'+origin+'.')
    if str(by).startswith(('BLACKLIST:','BLACKLIST #')):
        localized=localize_automated(player_id,text)
        if isinstance(localized,LocalizedText): return localized
    return localize_manual(player_id,text,category,player_name)
