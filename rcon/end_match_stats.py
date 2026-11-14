"""Automatic, opt-in end-of-match leaderboard for in-game admin messages."""

import logging
import time
from datetime import timedelta

from rcon.cache_utils import get_redis_client
from rcon.logs.loop import on_match_end
from rcon.user_config.end_match_stats import EndMatchStatsUserConfig
from rcon.utils import MapsHistory, get_server_number, layer_matches_match_log

logger = logging.getLogger(__name__)

TRANSLATIONS = {
    "en": ("MATCH TOP PLAYERS", "Kills", "Defense", "Support", "Combat", "Offense", "Vehicles destroyed"),
    "de": ("BESTE SPIELER DER RUNDE", "Kills", "Verteidigung", "Unterstützung", "Kampf", "Angriff", "Fahrzeuge zerstört"),
    "fr": ("MEILLEURS JOUEURS", "Éliminations", "Défense", "Soutien", "Combat", "Attaque", "Véhicules détruits"),
    "es": ("MEJORES JUGADORES", "Bajas", "Defensa", "Apoyo", "Combate", "Ataque", "Vehículos destruidos"),
    "ru": ("ЛУЧШИЕ ИГРОКИ", "Убийства", "Защита", "Поддержка", "Бой", "Атака", "Уничтожено техники"),
    "pt": ("MELHORES JOGADORES", "Abates", "Defesa", "Apoio", "Combate", "Ataque", "Veículos destruídos"),
    "pl": ("NAJLEPSI GRACZE", "Zabójstwa", "Obrona", "Wsparcie", "Walka", "Atak", "Zniszczone pojazdy"),
    "zh": ("本局最佳玩家", "击杀", "防御", "支援", "战斗", "进攻", "摧毁载具"),
}
EXTRA_LABELS = {
    "en": ("Teamplay", "Offense/Defense", "K/D", "Kills/min", "TOP SQUADS"),
    "de": ("Teamspiel", "Angriff/Verteidigung", "K/D", "Kills/Min", "BESTE SQUADS"),
    "fr": ("Jeu d'équipe", "Attaque/Défense", "É/M", "Élim./min", "MEILLEURES ESCOUADES"),
    "es": ("Juego en equipo", "Ataque/Defensa", "B/M", "Bajas/min", "MEJORES ESCUADRAS"),
    "ru": ("Командная игра", "Атака/Защита", "У/С", "Убийств/мин", "ЛУЧШИЕ ОТРЯДЫ"),
    "pt": ("Trabalho em equipe", "Ataque/Defesa", "A/M", "Abates/min", "MELHORES ESQUADRÕES"),
    "pl": ("Gra zespołowa", "Atak/Obrona", "Z/Ś", "Zabójstwa/min", "NAJLEPSZE DRUŻYNY"),
    "zh": ("团队配合", "进攻/防御", "击杀/死亡", "击杀/分钟", "最佳小队"),
}
SCORE_KEYS = ("kills", "defense", "support", "combat", "offense", "vehicles_destroyed", "teamplay", "offdef", "kd", "kpm")

# Team identifiers come from RCON in English. Localize them for the squad
# ranking as well as the headings, while retaining the existing representation
# for languages without a reviewed translation.
TEAM_LABELS = {
    "de": {"allies": "Alliierte", "axis": "Achsenmächte"},
    "fr": {"allies": "Alliés", "axis": "Axe"},
}


def score(entity, key, config):
    def number(field):
        value = entity.get(field, 0)
        return value if isinstance(value, (int, float)) and not isinstance(value, bool) else 0
    if key == "teamplay":
        return round(number("combat") + number("support") * config.support_multiplier)
    if key == "offdef":
        return round(number("offense") + number("defense") * config.defense_multiplier)
    if key == "kd":
        return round(number("kills") / max(number("deaths"), 1), 2)
    if key == "kpm":
        seconds = number("map_playtime_seconds")
        return round(number("kills") * 60 / seconds, 2) if seconds >= 300 else 0
    return number(key)


def extract_team_view(teams, config):
    players, squads = [], []
    for side in ("allies", "axis"):
        team = teams.get(side, {})
        commander = team.get("commander")
        if commander and "commander" in config.unit_types:
            players.append(commander)
        for squad_name, squad in team.get("squads", {}).items():
            if not squad_name or squad.get("type") not in config.unit_types or not squad.get("players"):
                continue
            members = squad["players"]
            players.extend(members)
            combined = dict(squad)
            team_label = TEAM_LABELS.get(config.language, {}).get(side, side)
            combined["name"] = f"{squad_name} ({team_label})"
            combined["vehicles_destroyed"] = sum(p.get("vehicles_destroyed", 0) or 0 for p in members)
            combined["map_playtime_seconds"] = sum(p.get("map_playtime_seconds", 0) or 0 for p in members)
            squads.append(combined)
    return players, squads


def format_sections(players, config=None, squads=()):
    config = config or EndMatchStatsUserConfig()
    title, *labels = TRANSLATIONS[config.language]
    labels += list(EXTRA_LABELS[config.language][:4])
    messages = []
    for enabled, heading, entities in ((config.include_players, config.title.strip() or title, list(players)), (config.include_squads, EXTRA_LABELS[config.language][4], list(squads))):
        if not enabled:
            continue
        section = []
        for label, field in zip(labels, SCORE_KEYS):
            if not getattr(config, field):
                continue
            ranked = [(score(p, field, config), p) for p in entities if p.get("name")]
            ranked = sorted((item for item in ranked if item[0] > 0), key=lambda item: (-item[0], str(item[1]["name"]).casefold()))[:config.top_count]
            if ranked:
                values = [f"{' '.join(str(p['name']).split())[:32]} ({value:g})" for value, p in ranked]
                section.append(f"{label}: {', '.join(values)}")
        if section:
            messages.append("\n".join([heading, *section]))
    return messages


def format_stats(players, config=None, squads=()):
    return "\n".join(format_sections(players, config, squads)) or None


def send_delayed_squad_message(message, event_time):
    """Drop delayed jobs that could otherwise announce a stale match."""
    if time.time() - event_time > 90:
        logger.warning("Skipping stale end-of-match squad message")
        return
    config = EndMatchStatsUserConfig.load_from_db(default_on_validation_error=False)
    if not config.enabled or not config.include_squads:
        return
    from rcon.rcon import get_rcon
    send_message_once(get_rcon(), message, "squad")


def send_message_once(rcon, message, kind):
    """Do not automatically repeat a command whose result may be uncertain."""
    try:
        with rcon.without_retries():
            accepted = rcon.message_all_players(message)
        if accepted:
            logger.info("End-of-match %s message accepted by RCON", kind)
        else:
            logger.warning("End-of-match %s message was rejected by RCON", kind)
        return bool(accepted)
    except Exception:
        logger.exception("End-of-match %s message failed or has an uncertain result", kind)
        return False


def schedule_squad_message(message, event_time, seconds):
    from rcon.workers import get_queue
    get_queue().enqueue_in(timedelta(seconds=seconds), send_delayed_squad_message,
                           message, event_time, ttl=90, result_ttl=300)


@on_match_end
def send_end_match_stats(rcon, log):
    server = str(get_server_number())
    try:
        config = EndMatchStatsUserConfig.load_from_db(default_on_validation_error=False)
        if not config.enabled:
            return
        event_time = log["timestamp_ms"] / 1000
        if abs(time.time() - event_time) > 30:
            return
        history = MapsHistory()
        if not history or not history[0].get("start") or history[0].get("guessed"):
            return
        start = history[0]["start"]
        if start >= event_time:
            return
        layer = rcon.game_profile.parse_layer(history[0]["name"])
        if not layer_matches_match_log(layer, log.get("raw", "")):
            return
        result = rcon.get_team_view()
        if result.get("fail_count"):
            logger.warning("End-of-match stats skipped: incomplete player data")
            return
        players, squads = extract_team_view(result, config)
        messages = format_sections(players, config, squads)
        updated_history = MapsHistory()
        if (not messages or not updated_history or updated_history[0].get("start") != start
                or abs(time.time() - event_time) > 30):
            return
        # Claim before sending: a replayed log event must not spam players.
        key = f"end-match-stats:{server}:{int(start)}"
        if not get_redis_client().set(key, "1", nx=True, ex=86400):
            return
        send_message_once(rcon, messages[0], "first")
        if len(messages) > 1:
            schedule_squad_message(messages[1], event_time, config.message_gap_seconds)
    except Exception:
        logger.exception("Could not send end-of-match stats")
