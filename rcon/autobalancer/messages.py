"""Separate DE/EN packets; server settings, never inferred player language."""

from .feedback import send_private

SYSTEM = {
    "manual": (
        "Manueller Modus: Ein Admin muss den Wechsel freigeben. Der Befehl löst keinen sofortigen Teamwechsel aus.",
        "Manual mode: an admin must approve the switch. This command does not switch your team immediately.",
    ),
    "disabled": (
        "Der Autobalancer ist ausgeschaltet. Es ist kein Wechsel vorgemerkt.",
        "Autobalancing is disabled. No team switch is queued.",
    ),
    "shadow": (
        "Der Autobalancer beobachtet nur (Shadow-Modus). Es erfolgt kein Teamwechsel.",
        "Autobalancing is in observation mode only. No team switch will take place.",
    ),
    "waiting_admin": (
        "Die Freiwilligenphase ist beendet. Der Vorschlag wartet auf einen Admin.",
        "The volunteer window is closed. The proposal is waiting for an admin.",
    ),
    "preparing": (
        "Die Freiwilligenphase ist beendet. Ein Wechsel wird bereits vorbereitet oder geprüft.",
        "The volunteer window is closed. A switch is already being prepared or verified.",
    ),
    "closed": (
        "Aktuell ist kein Aufruf für Freiwillige offen. Bitte warte auf eine neue Einladung zum Teamausgleich.",
        "No volunteer call is open right now. Please wait for a new team-balance invitation.",
    ),
    "unavailable": (
        "Der Autobalancer ist gerade nicht erreichbar. Bitte versuche es später erneut.",
        "Autobalancing is currently unavailable. Please try again later.",
    ),
    "expired": (
        "Deine Meldung liegt außerhalb der Freiwilligenfrist. Bitte warte auf eine neue Einladung.",
        "Your reply is outside the volunteer window. Please wait for a new invitation.",
    ),
    "blocked": (
        "Deine Meldung konnte nicht angenommen werden: Der Teamausgleich ist momentan aus Sicherheitsgründen blockiert.",
        "Your request could not be accepted: team balancing is temporarily blocked for safety.",
    ),
    "seeding": (
        "Während des Seedings ist der Teamausgleich pausiert. Es wird kein Wechsel vorgemerkt.",
        "Team balancing is paused during seeding. No team switch will be queued.",
    ),
    "wrong_team": (
        "Nicht vorgemerkt: Der Aufruf gilt nur für Spieler des ursprünglich größeren Teams.",
        "Not registered: this call is only for players on the originally larger team.",
    ),
    "commander": (
        "Nicht vorgemerkt: Commander sind vom automatischen Teamwechsel ausgeschlossen.",
        "Not registered: Commanders are protected from automatic team switches.",
    ),
    "connection": (
        "Nicht vorgemerkt: Du bist noch durch die Schonzeit nach dem Verbinden geschützt.",
        "Not registered: you are still protected after connecting to the server.",
    ),
    "squad": (
        "Nicht vorgemerkt: Dein Squad soll zusammenbleiben; einzelne Mitglieder können sich nicht melden.",
        "Not registered: your squad must stay together; individual members cannot volunteer.",
    ),
    "cooldown": (
        "Nicht vorgemerkt: Du bist nach einem früheren Teamwechsel noch geschützt.",
        "Not registered: you are still protected after a previous team switch.",
    ),
    "registered": (
        "Du bist für diesen Aufruf bereits vorgemerkt.",
        "You are already registered for this call.",
    ),
    "ended": (
        "Der Teamausgleich wurde abgebrochen. Du bleibst in deinem Team.",
        "Team balancing was cancelled. You stay on your current team.",
    ),
    "uncertain": (
        "Der Teamausgleich ist beendet. Bitte lass deinen Teamwechsel von einem Admin prüfen.",
        "Team balancing has ended. Please ask an admin to check your team switch.",
    ),
}


def closed_key(mode, state):
    if mode in {"disabled", "shadow"}:
        return mode
    if state.get("phase") in {"proposed", "armed", "verifying"}:
        return (
            "waiting_admin"
            if mode == "manual" and state["phase"] == "proposed"
            else "preparing"
        )
    return "closed"


def render(config, key, *, manual=False, **values):
    languages = (
        ("de", "en")
        if config.message_language == "de+en"
        else (config.message_language,)
    )
    result = []
    for language in languages:
        index = 0 if language == "de" else 1
        pack = config.messages if language == "de" else config.messages_en
        text = SYSTEM[key][index] if key in SYSTEM else getattr(pack, key)
        # Faction labels US/NVA/etc remain unchanged; translate HLL team labels.
        localized = dict(values)
        if "target_team" in localized:
            labels = (
                {"Allies": "Alliierte", "Axis": "Achsenmächte"}
                if language == "de"
                else {"Alliierte": "Allies", "Achsenmächte": "Axis"}
            )
            localized["target_team"] = labels.get(
                localized["target_team"], localized["target_team"]
            )
        text = text.format(**localized)
        if key == "volunteer_request":
            text = text.replace("!balance", config.volunteer_command)
        if manual and config.mode == "manual":
            text += "\n" + SYSTEM["manual"][index]
        result.append(text)
    return result


def send(rcon, player_id, config, key, **values):
    # Do not short-circuit: failure of one language must not suppress the other.
    results = [
        send_private(rcon, player_id, text) for text in render(config, key, **values)
    ]
    return all(results)
