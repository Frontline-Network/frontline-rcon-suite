"""Recipient copy and delivery gates for personal VIP offers."""
from datetime import datetime, timedelta, timezone
import logging
import re
from urllib.parse import urlsplit

from sqlalchemy import and_, func, or_, select

from rcon.models import (
    AdminIncident, AdminIncidentEvent, LogLine, PlayerID, PlayerOptins,
    PlayersAction, enter_session,
)
from rcon.player_language import game_identity, preferred_language
from rcon.user_config.auto_broadcast import VIP_LIFECYCLE_DEFAULT_MESSAGES
from rcon.user_config.end_match_stats import EndMatchStatsUserConfig

logger = logging.getLogger(__name__)
PREFERENCE = "vip_marketing"
EOS = re.compile(r"[0-9a-fA-F]{32}")
IDENTITIES = "https://fln.gg/mein-konto/spielidentitaeten/"
SHOP = "https://fln.gg/community/vip/"
COPY = {
    "unverified": {
        "de": f"Teste Vietnam-VIP 7 Tage gratis. Öffne am Handy {IDENTITIES} und verknüpfe deinen Spieler. Kein Abo.",
        "en": f"Try Vietnam VIP free for 7 days. Open {IDENTITIES} on your phone and link your player. No subscription.",
        "fr": f"Essaye le VIP Vietnam gratuitement pendant 7 jours. Sur ton téléphone, ouvre {IDENTITIES} et associe ton compte de jeu. Sans abonnement.",
    },
    "reminder": {
        "de": f"Bei hoher Auslastung hast du mit Vietnam-VIP bevorzugten Zugang. Deine kostenlose Probewoche findest du unter {IDENTITIES}",
        "en": f"Vietnam VIP gives you priority access when the server is busy. Start your free trial week at {IDENTITIES}",
        "fr": f"Le VIP Vietnam te donne un accès prioritaire quand le serveur est très fréquenté. Active tes 7 jours d’essai sur {IDENTITIES}",
    },
    "trial_active": {
        "de": "Dein Probe-VIP ist aktiv. Die Laufzeit findest du unter fln.gg/mein-konto.",
        "en": "Your VIP trial is active. Check its end date at fln.gg/mein-konto.",
        "fr": "Ton essai VIP est actif. Sa date de fin est indiquée sur fln.gg/mein-konto.",
    },
    "trial_expiring": {
        "de": f"Dein Probe-VIP endet am {{expires_at}}. Wenn du VIP weiter nutzen möchtest: {SHOP}",
        "en": f"Your VIP trial ends on {{expires_at}}. To keep using VIP, visit {SHOP}",
        "fr": f"Ton essai VIP prend fin le {{expires_at}}. Pour continuer à profiter du VIP : {SHOP}",
    },
    "trial_expired": {
        "de": f"Dein Probe-VIP ist am {{expires_at}} abgelaufen. Hier kannst du VIP kaufen: {SHOP}",
        "en": f"Your VIP trial ended on {{expires_at}}. You can buy VIP at {SHOP}",
        "fr": f"Ton essai VIP a pris fin le {{expires_at}}. Tu peux acheter le VIP sur {SHOP}",
    },
}
PREF_COPY = {
    "de": ("VIP-Angebote einschalten", "VIP-Angebote ausschalten", "Persönliche VIP-Angebote sind eingeschaltet.", "Persönliche VIP-Angebote sind ausgeschaltet.", "Verknüpfe zuerst dein Spielkonto."),
    "en": ("Enable VIP offers", "Turn off VIP offers", "Personal VIP offers are on.", "Personal VIP offers are off.", "Link your game account first."),
    "fr": ("Activer les offres VIP", "Désactiver les offres VIP", "Les offres VIP personnelles sont activées.", "Les offres VIP personnelles sont désactivées.", "Associe d’abord ton compte de jeu."),
}


def preference_copy(locale):
    return PREF_COPY.get(locale, PREF_COPY["en"])


def _frontline_offer():
    from rcon.vip_lifecycle import _local_server_family, _status_url
    provider = urlsplit(_status_url())
    return (_local_server_family() == "hll_vietnam" and provider.scheme == "https"
            and provider.hostname in {"fln.gg", "www.fln.gg"})


def render_activity_message(*, rule, player_id, source, translations=None, reminder=False, expires_at=None):
    locale = preferred_language(player_id)
    frontline = _frontline_offer()
    if frontline and reminder and rule == "unverified":
        variants = COPY["reminder"]
    elif frontline and source.strip() == VIP_LIFECYCLE_DEFAULT_MESSAGES.get(rule):
        variants = {**COPY[rule], **(translations or {})}
    else:
        variants = dict(translations or {})
    # A community's customized source has no declared language. Only variants
    # explicitly made available by the operator may be sent in adaptive mode.
    if locale == "de+en":
        text = "\n".join(dict.fromkeys(v for v in (variants.get("de"), variants.get("en")) if v))
    else:
        text = variants.get(locale) or variants.get("en", "")
    if not text.strip():
        return ""
    if rule in {"trial_expiring", "trial_expired"} or "{expires_at}" in text:
        try:
            end = datetime.fromisoformat(expires_at.replace("Z", "+00:00")) if isinstance(expires_at, str) else expires_at
            if not isinstance(end, datetime) or end.tzinfo is None:
                return ""
            date = end.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        except (ValueError, OverflowError):
            return ""
        text = text.replace("{expires_at}", date) if "{expires_at}" in text else f"{text} ({date})"
    footer = {
        "de": "Angebote aus: !vipads off oder Discord → Meine Meldungen.",
        "en": "Turn off offers: !vipads off or Discord → My reports.",
        "fr": "Désactiver les offres : !vipads off ou Discord → Mes signalements.",
    }
    return text.strip() + "\n" + footer.get(locale, footer["en"])


def opted_out_player_ids(sess, player_ids):
    if not player_ids:
        return set()
    canonical = {game_identity(pid) for pid in player_ids}
    eos = {pid for pid in canonical if EOS.fullmatch(pid)}
    selector = PlayerID.player_id.in_(canonical - eos)
    if eos:
        selector = or_(selector, func.lower(PlayerID.player_id).in_(eos))
    opted_out = sess.scalars(select(PlayerID.player_id).join(
        PlayerOptins, PlayerOptins.player_id_id == PlayerID.id
    ).where(PlayerOptins.optin_name == PREFERENCE, PlayerOptins.optin_value == "false", selector))
    denied = {game_identity(pid) for pid in opted_out}
    return {pid for pid in player_ids if game_identity(pid) in denied}


def activity_opted_out(sess, *, player_db_id, player_id):
    return bool(opted_out_player_ids(sess, {player_id}))


def set_activity_consent(sess, player_id, enabled, *, chosen_at=None):
    """Serialize changes with delivery claims and respect out-of-order Discord replies."""
    pid = game_identity(player_id)
    if not pid or type(enabled) is not bool:
        raise ValueError("Invalid game account or VIP offer preference")
    match = func.lower(PlayerID.player_id) == pid if EOS.fullmatch(pid) else PlayerID.player_id == pid
    ids = sess.scalars(select(PlayerID.id).where(match).order_by(PlayerID.id).with_for_update()).all()
    if not ids:
        raise ValueError("Game account not found")
    prefs = sess.scalars(select(PlayerOptins).where(
        PlayerOptins.player_id_id.in_(ids), PlayerOptins.optin_name == PREFERENCE
    )).all()
    when = (chosen_at or datetime.now(timezone.utc)).astimezone(timezone.utc).replace(tzinfo=None)
    if any(pref.modified is not None and pref.modified >= when for pref in prefs):
        return not any(pref.optin_value == "false" for pref in prefs)
    by_id = {pref.player_id_id: pref for pref in prefs}
    for db_id in ids:
        pref = by_id.get(db_id)
        if pref is None:
            pref = PlayerOptins(player_id_id=db_id, optin_name=PREFERENCE)
            sess.add(pref)
        pref.optin_value = "true" if enabled else "false"
        pref.modified = when
    sess.flush()
    return enabled


def handle_chat_vip_ads(rcon, event):
    match = re.fullmatch(r"!vipads(?:\s+(on|off))?", str(event.get("sub_content") or "").strip(), re.I)
    if not match:
        return False
    pid = event.get("player_id_1")
    if not pid:
        return True
    labels = preference_copy(preferred_language(pid))
    try:
        with enter_session() as sess:
            if match[1]:
                enabled = set_activity_consent(sess, pid, match[1].lower() == "on")
            else:
                enabled = not opted_out_player_ids(sess, {pid})
        body = labels[2 if enabled else 3] + "  !vipads off / !vipads on"
    except Exception:
        logger.exception("Could not read or save the VIP offer preference")
        body = "VIP preference unavailable. Please try again."
    rcon.message_player(player_id=pid, message=body, save_message=False)
    return True


def activity_window_open(sess, *, server_number, now):
    """Only confirmed intermissions are suitable; stop early if a new round starts."""
    wall_now = datetime.fromtimestamp(now.timestamp())  # log_lines stores host-local wall time
    latest = sess.execute(select(LogLine.type, LogLine.event_time).where(
        LogLine.server == str(server_number),
        LogLine.type.in_(("MATCH START", "MATCH ENDED")),
        LogLine.event_time >= wall_now - timedelta(seconds=120),
        LogLine.event_time <= wall_now,
    ).order_by(LogLine.event_time.desc(), LogLine.id.desc()).limit(1)).first()
    if latest is None or latest.type != "MATCH ENDED":
        return False
    age = (wall_now - latest.event_time).total_seconds()
    if age < 20:
        return False
    stats = EndMatchStatsUserConfig.load_from_db(default_on_validation_error=False)
    # First stats packets can be generated until +30s; a delayed squad job
    # expires at +90s. Leave a further 10s to read the final scoreboard.
    if stats.enabled:
        delay = 100 if stats.include_players and stats.include_squads else 40
        return age >= delay
    return True


def activity_message_allowed(sess, *, player_db_id, player_id, server_number, now):
    if not activity_window_open(sess, server_number=server_number, now=now):
        return False
    cutoff = now.astimezone(timezone.utc) - timedelta(minutes=3)
    incident = select(AdminIncident.id).where(
        AdminIncident.server_number == server_number,
        AdminIncident.status.in_(("new", "claimed")), AdminIncident.updated_at >= cutoff,
        or_(AdminIncident.reporter_id == player_id, AdminIncident.target_id == player_id),
    ).exists()
    event = AdminIncidentEvent.payload
    voice = select(AdminIncidentEvent.id).join(AdminIncident).where(
        AdminIncident.server_number == server_number, AdminIncident.status == "new",
        AdminIncidentEvent.created_at >= cutoff - timedelta(minutes=7),
        or_(
            and_(AdminIncidentEvent.event_type == "report_admin", event["status"].as_string() == "voice",
                 or_(AdminIncident.reporter_id == player_id, event["target_id"].as_string() == player_id,
                     event["voice"]["witness_id"].as_string() == player_id)),
            and_(AdminIncidentEvent.event_type == "voice_game_message",
                 event["recipient"].as_string() == player_id,
                 event["status"].as_string().in_(("pending", "sending")),
                 event["expires"].as_float() >= now.timestamp()),
        )
    ).exists()
    recent_action = select(PlayersAction.id).where(
        PlayersAction.player_id_id == player_db_id, PlayersAction.time >= cutoff.replace(tzinfo=None)
    ).exists()
    return not (activity_opted_out(sess, player_db_id=player_db_id, player_id=player_id)
                or sess.scalar(select(or_(incident, voice, recent_action))))
