"""Reviewed game and Discord copy. A message key represents one factual state."""

import hashlib
import json
import re
from string import Formatter
from rcon.voice_player_text import PLAYER_TEXT

# Templates never contain user input until after language selection/translation.
TEXT = {
    "notice_squad": (
        "Dein Squad versucht dich zu erreichen. Bitte melde dich im Squad-Voice.",
        "Your squad is trying to reach you. Please respond in squad voice.",
        "Ton escouade essaie de te joindre. Réponds sur le canal vocal de l’escouade.",
        "Twój oddział próbuje się z tobą skontaktować. Odezwij się na kanale głosowym oddziału.",
        "Je squad probeert je te bereiken. Reageer in het spraakkanaal van je squad.",
    ),
    "notice_command": (
        "Deine Teamführung versucht dich zu erreichen. Bitte melde dich im Führungsfunk.",
        "Your team leaders are trying to reach you. Please respond in command voice.",
        "Ton commandement essaie de te joindre. Réponds sur le canal vocal de commandement.",
        "Dowództwo próbuje się z tobą skontaktować. Odezwij się na kanale głosowym dowództwa.",
        "De teamleiding probeert je te bereiken. Reageer in het commandokanaal.",
    ),
    "notice_sent": (
        "{target} wurde informiert. Wir fragen in etwa einer Minute nach, ob die Kommunikation wieder klappt.",
        "{target} was notified. In about a minute we’ll ask if voice communication is working again.",
        "Un message a été envoyé à {target}. Dans une minute environ, nous te demanderons si la communication a repris.",
        "Wysłaliśmy wiadomość do {target}. Za około minutę zapytamy, czy komunikacja głosowa już działa.",
        "{target} heeft een bericht gekregen. Over ongeveer een minuut vragen we of het spraakcontact is hersteld.",
    ),
    "notice_external": (
        "{target} wurde informiert. Wir holen eine Rückmeldung aus dem betroffenen Sprachkanal ein.",
        "{target} was notified. We're asking someone in the affected voice channel to confirm.",
        "Un message a été envoyé à {target}. Nous demandons confirmation dans le canal vocal concerné.",
        "Wysłaliśmy wiadomość do {target}. Poprosimy o potwierdzenie osobę z tego kanału głosowego.",
        "{target} heeft een bericht gekregen. We vragen iemand uit het betreffende spraakkanaal om bevestiging.",
    ),
    "notice_failed": (
        "Wir konnten den Versand des Hinweises nicht bestätigen. Ein Admin muss den Fall prüfen.",
        "We could not confirm that the notice was sent. An admin needs to review the report.",
        "L’envoi du message n’a pas pu être confirmé. Un admin doit examiner le signalement.",
        "Nie udało się potwierdzić wysłania wiadomości. Zgłoszenie wymaga sprawdzenia przez administratora.",
        "De verzending van het bericht kon niet worden bevestigd. Een beheerder moet de melding bekijken.",
    ),
    "question": (
        "Klappt die Sprachkommunikation mit {target} jetzt?",
        "Is voice communication with {target} working now?",
        "La communication vocale avec {target} fonctionne-t-elle maintenant ?",
        "Czy komunikacja głosowa z {target} już działa?",
        "Werkt het spraakcontact met {target} nu?",
    ),
    "fixed": (
        "Klappt wieder",
        "Working again",
        "Ça fonctionne",
        "Już działa",
        "Werkt weer",
    ),
    "still_silent": (
        "Weiterhin keine Antwort",
        "Still no response",
        "Toujours sans réponse",
        "Nadal brak odpowiedzi",
        "Nog geen antwoord",
    ),
    "resolved": (
        "Die Kommunikation klappt wieder. Deine Meldung ist abgeschlossen.",
        "Voice communication is working again. Your report is closed.",
        "La communication vocale a repris. Ton signalement est clos.",
        "Komunikacja głosowa znów działa. Zgłoszenie jest zamknięte.",
        "Het spraakcontact is hersteld. Je melding is gesloten.",
    ),
    "manual": (
        "Deine Meldung liegt zur manuellen Prüfung vor.",
        "Your report is awaiting admin review.",
        "Ton signalement est en attente d’examen par un admin.",
        "Zgłoszenie oczekuje na sprawdzenie przez administratora.",
        "Je melding wacht op beoordeling door een beheerder.",
    ),
    "dry_run": (
        "Probelauf abgeschlossen. Es wurde kein Kick gesendet. Admins können den Fall prüfen.",
        "Dry run completed. No kick was sent. Admins can review the report.",
        "Simulation terminée. Aucune expulsion n’a été demandée. Les admins peuvent examiner le signalement.",
        "Zakończono próbę. Nie wysłano polecenia wyrzucenia. Administratorzy mogą sprawdzić zgłoszenie.",
        "Proef afgerond. Er is geen kickopdracht verstuurd. Beheerders kunnen de melding beoordelen.",
    ),
    "expired": (
        "Die Rückfrage blieb unbeantwortet. Ein Admin muss den Fall prüfen.",
        "The follow-up received no answer. An admin needs to review the report.",
        "La demande est restée sans réponse. Un admin doit examiner le signalement.",
        "Nie otrzymaliśmy odpowiedzi. Zgłoszenie wymaga sprawdzenia przez administratora.",
        "De vervolgvraag is onbeantwoord. Een beheerder moet de melding bekijken.",
    ),
    "kicked": (
        "Der Spielserver hat den Kick von {target} bestätigt.",
        "The game server confirmed that {target} was kicked.",
        "Le serveur de jeu a confirmé l’expulsion de {target}.",
        "Serwer gry potwierdził wyrzucenie gracza {target}.",
        "De spelserver heeft bevestigd dat {target} is verwijderd.",
    ),
    "unconfirmed": (
        "Der Spielserver hat den Kick nicht bestätigt. Ein Admin muss den Fall prüfen.",
        "The game server did not confirm the kick. An admin needs to review the report.",
        "Le serveur de jeu n’a pas confirmé l’expulsion. Un admin doit examiner le signalement.",
        "Serwer gry nie potwierdził wyrzucenia gracza. Zgłoszenie wymaga sprawdzenia przez administratora.",
        "De spelserver heeft de verwijdering niet bevestigd. Een beheerder moet de melding bekijken.",
    ),
    "duplicate": (
        "Zu diesem Vorfall liegt bereits eine Meldung vor.",
        "There is already a report about this incident.",
        "Un signalement existe déjà pour cet incident.",
        "Ten incydent jest już zgłoszony.",
        "Er is al een melding over dit incident.",
    ),
    "clarify": (
        "Welchen Spieler meinst du? Bitte gib den genauen Spielernamen an.",
        "Which player do you mean? Please give the exact in-game name.",
        "De quel joueur s’agit-il ? Précise son nom exact en jeu.",
        "Którego gracza dotyczy zgłoszenie? Podaj dokładną nazwę z gry.",
        "Welke speler bedoel je? Geef de exacte naam uit het spel op.",
    ),
    "pc_reply": (
        "Antwort im Chat: !voice {case} ok / !voice {case} still",
        "Reply in chat: !voice {case} ok / !voice {case} still",
        "Réponds dans le chat : !voice {case} ok / !voice {case} still",
        "Odpowiedz na czacie: !voice {case} ok / !voice {case} still",
        "Antwoord in de chat: !voice {case} ok / !voice {case} still",
    ),
    "pc_clarify": (
        "Antworte mit !voice {case} target <Spielername>. Deine Antwort im Chat kann sichtbar sein.",
        "Reply with !voice {case} target <player name>. Your chat reply may be visible.",
        "Réponds avec !voice {case} target <nom du joueur>. Ta réponse dans le chat peut être visible.",
        "Odpowiedz: !voice {case} target <nazwa gracza>. Inni mogą zobaczyć twoją odpowiedź na czacie.",
        "Antwoord met !voice {case} target <spelersnaam>. Je chatantwoord kan zichtbaar zijn.",
    ),
    "discord_reply": (
        "Konsole: Öffne im Community-Discord „Meine Meldungen“. Verknüpfe bei Bedarf zuerst dein Spielkonto.",
        "Console: open My reports in the community Discord. Link your game account first if needed.",
        "Console : ouvre Mes signalements sur le Discord de la communauté. Lie d’abord ton compte de jeu si nécessaire.",
        "Konsola: otwórz Moje zgłoszenia na Discordzie społeczności. W razie potrzeby najpierw połącz konto gry.",
        "Console: open Mijn meldingen op de community-Discord. Koppel zo nodig eerst je spelaccount.",
    ),
    "link": (
        "Spielkonto verknüpfen",
        "Link game account",
        "Lier le compte de jeu",
        "Połącz konto gry",
        "Spelaccount koppelen",
    ),
    "lang_button": (
        "Meine Sprache",
        "My language",
        "Ma langue",
        "Mój język",
        "Mijn taal",
    ),
    "dm_on": (
        "Direktnachrichten einschalten",
        "Enable direct messages",
        "Activer les messages privés",
        "Włącz wiadomości prywatne",
        "Privéberichten inschakelen",
    ),
    "dm_off": (
        "Direktnachrichten ausschalten",
        "Disable direct messages",
        "Désactiver les messages privés",
        "Wyłącz wiadomości prywatne",
        "Privéberichten uitschakelen",
    ),
    "received": (
        "Meldung eingegangen.",
        "Report received.",
        "Signalement reçu.",
        "Zgłoszenie przyjęte.",
        "Melding ontvangen.",
    ),
    **PLAYER_TEXT,
}

BUILTIN = ("de", "en", "fr", "pl", "nl")
ENGLISH = {key: row[1] for key, row in TEXT.items()}
VERSION = hashlib.sha256(json.dumps(ENGLISH, sort_keys=True).encode()).hexdigest()[:16]


def valid_templates(texts):
    """Reject malformed bundles, unexpected data, substitutions and chat commands."""
    if not isinstance(texts, dict) or texts.keys() != ENGLISH.keys():
        return False
    for key, source in ENGLISH.items():
        value = texts[key]
        button = key in {
            "fixed",
            "still_silent",
            "link",
            "lang_button",
            "dm_on",
            "dm_off",
            "enter_name",
            "verify_code",
        }
        if (
            not isinstance(value, str)
            or not value.strip()
            or len(value) > (65 if button else 380)
        ):
            return False
        if any(ord(c) < 32 or ord(c) == 127 for c in value) or re.search(
            r"https?://|@(?:everyone|here)|<[@#]", value, re.I
        ):
            return False
        try:
            fields = [
                (field, spec, conversion)
                for _, field, spec, conversion in Formatter().parse(value)
                if field is not None
            ]
            expected = [
                (field, spec, conversion)
                for _, field, spec, conversion in Formatter().parse(source)
                if field is not None
            ]
        except ValueError:
            return False
        if sorted(fields) != sorted(expected) or re.findall(
            r"!\w+", value
        ) != re.findall(r"!\w+", source):
            return False
        if key == "pc_reply" and any(
            part not in value for part in ("!voice {case} ok", "!voice {case} still")
        ):
            return False
        if key == "pc_clarify" and "!voice {case} target " not in value:
            return False
    return True
