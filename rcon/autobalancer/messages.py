"""Recipient language packets, with legacy server settings when routing is off."""

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

SYSTEM_FR = {
    "manual": "Mode manuel : un administrateur doit approuver le changement. Cette commande ne change pas immédiatement votre équipe.",
    "disabled": "L'équilibrage automatique est désactivé. Aucun changement d'équipe n'est prévu.",
    "shadow": "L'équilibrage automatique est en mode observation. Aucun changement d'équipe n'aura lieu.",
    "waiting_admin": "La période de volontariat est terminée. La proposition attend un administrateur.",
    "preparing": "La période de volontariat est terminée. Un changement est déjà en préparation ou en cours de vérification.",
    "closed": "Aucun appel aux volontaires n'est ouvert actuellement. Veuillez attendre une nouvelle invitation.",
    "unavailable": "L'équilibrage automatique est momentanément indisponible. Veuillez réessayer plus tard.",
    "expired": "Votre réponse est arrivée après la fin de la période de volontariat. Veuillez attendre une nouvelle invitation.",
    "blocked": "Votre demande n'a pas pu être acceptée : l'équilibrage est temporairement bloqué par sécurité.",
    "seeding": "L'équilibrage est suspendu pendant le remplissage du serveur. Aucun changement d'équipe n'est prévu.",
    "wrong_team": "Non enregistré : cet appel concerne uniquement les joueurs de l'équipe initialement la plus nombreuse.",
    "commander": "Non enregistré : les commandants sont protégés contre les changements d'équipe automatiques.",
    "connection": "Non enregistré : vous êtes encore protégé après votre connexion au serveur.",
    "squad": "Non enregistré : votre escouade doit rester ensemble ; ses membres ne peuvent pas se porter volontaires individuellement.",
    "cooldown": "Non enregistré : vous êtes encore protégé après un changement d'équipe précédent.",
    "registered": "Vous êtes déjà inscrit pour cet appel.",
    "ended": "L'équilibrage a été annulé. Vous restez dans votre équipe.",
    "uncertain": "L'équilibrage est terminé. Veuillez demander à un administrateur de vérifier votre changement d'équipe.",
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
    languages = config.message_language.split("+")
    result = []
    for language in languages:
        index = 0 if language == "de" else 1
        pack = {"de": config.messages, "en": config.messages_en, "fr": config.messages_fr}[language]
        text = (SYSTEM_FR[key] if language == "fr" else SYSTEM[key][index]) if key in SYSTEM else getattr(pack, key)
        # Faction labels US/NVA/etc remain unchanged; translate HLL team labels.
        localized = dict(values)
        if "target_team" in localized:
            labels = {
                "de": {"Allies": "Alliierte", "Axis": "Achsenmächte"},
                "en": {"Alliierte": "Allies", "Achsenmächte": "Axis"},
                "fr": {"Allies": "Alliés", "Alliierte": "Alliés", "Axis": "Axe", "Achsenmächte": "Axe"},
            }[language]
            localized["target_team"] = labels.get(
                localized["target_team"], localized["target_team"]
            )
        text = text.format(**localized)
        if key == "volunteer_request":
            text = text.replace("!balance", config.volunteer_command)
        if manual and config.mode == "manual":
            text += "\n" + (SYSTEM_FR["manual"] if language == "fr" else SYSTEM["manual"][index])
        result.append(text)
    return result


def send(rcon, player_id, config, key, **values):
    from rcon.player_messages import routing_enabled, render as render_player, LocalizedText
    if routing_enabled():
        from rcon.player_message_catalog import autobalancer_definition
        definition = autobalancer_definition(config,key)
        manual = values.pop('manual',False)
        locales={}
        for locale in ('de','en','fr'):
            data=dict(values)
            if 'target_team' in data:
                labels={'de':{'Allies':'Alliierte','Axis':'Achsenmächte'},
                        'en':{'Alliierte':'Allies','Achsenmächte':'Axis'},
                        'fr':{'Allies':'Alliés','Alliierte':'Alliés','Axis':'Axe','Achsenmächte':'Axe'}}[locale]
                data['target_team']=labels.get(data['target_team'],data['target_team'])
            locales[locale]=data
        variants=dict(definition['defaults'])
        for locale in variants:
            variants[locale]=variants[locale].replace('!balance',config.volunteer_command)
        packet=render_player(definition['key'],definition['source'],player_id=player_id,variables=values,
                             defaults=variants,enabled=True,binding_hash=definition['source_hash'],locale_variables=locales)
        if key=='volunteer_request':
            packet=LocalizedText(str(packet).replace('!balance',config.volunteer_command),
                                 original=getattr(packet,'original',packet).replace('!balance',config.volunteer_command),
                                 key=definition['key'],language=getattr(packet,'language','legacy'))
        if manual and config.mode=='manual':
            note_definition=autobalancer_definition(config,'manual')
            note=render_player('autobalancer.manual',SYSTEM['manual'][0],player_id=player_id,
                               defaults=note_definition['defaults'],enabled=True,binding_hash=note_definition['source_hash'])
            packet=LocalizedText(str(packet)+'\n'+str(note),original=getattr(packet,'original',packet)+'\n'+getattr(note,'original',note),
                                 key=definition['key'],language=getattr(packet,'language','legacy'))
        return send_private(rcon,player_id,packet)
    # Do not short-circuit: failure of one language must not suppress the other.
    results = [
        send_private(rcon, player_id, text) for text in render(config, key, **values)
    ]
    return all(results)
