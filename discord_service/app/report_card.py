"""Summarize the current moderation decision above the evidence on a Discord card."""

from math import isfinite
from .report_admin_display import safe


TEXT = {
    "review": ("Adminprüfung nötig", "Admin review needed", "Examen par un admin requis"),
    "watch": ("Aktuell kein Eingriff nötig", "No admin action needed now", "Aucune intervention requise pour le moment"),
    "owner": ("In Bearbeitung bei {name}", "Being handled by {name}", "Pris en charge par {name}"),
    "closed": ("Abgeschlossen", "Closed", "Terminé"),
    "dismissed": ("Meldung abgelehnt", "Report dismissed", "Signalement rejeté"),
    "new": ("Neue Spielermeldung", "New player report", "Nouveau signalement"),
    "ai_chat": ("Chatnachricht zur Prüfung markiert", "Chat message flagged for review", "Message du chat à examiner"),
    "ai_player_name": ("Spielername zur Prüfung markiert", "Player name flagged for review", "Nom de joueur à examiner"),
    "unclear": ("Zielspieler klären", "Identify the reported player", "Identifier le joueur signalé"),
    "classifying": ("Bot prüft den Meldegrund", "Bot is reading the report", "Analyse du motif en cours"),
    "queued": ("Automatische Prüfung ausstehend", "Automatic checks pending", "Vérifications automatiques en attente"),
    "waiting": ("Beobachtungsfrist läuft", "Observation period in progress", "Période d’observation en cours"),
    "sending": ("Kick angefordert, Bestätigung steht aus", "Kick requested, awaiting confirmation", "Expulsion demandée, en attente de confirmation"),
    "kicked": ("Spielserver hat den Kick bestätigt", "Game server confirmed the kick", "Expulsion confirmée par le serveur de jeu"),
    "dry_run": ("Probelauf beendet, kein Kick ausgeführt", "Dry run completed without a kick", "Simulation terminée sans expulsion"),
    "unknown": ("Ergebnis des Eingriffs ungewiss", "Action outcome unconfirmed", "Résultat de l’intervention incertain"),
    "manual": ("An die Moderation übergeben", "Referred to moderation", "Transmis à la modération"),
    "clarify": ("Rückfrage zum Zielspieler läuft", "Waiting for the reporter to identify the player", "En attente de la précision du signaleur"),
    "notice_pending": ("Privater Voice-Hinweis vorgemerkt", "Private voice reminder queued", "Rappel vocal privé en attente"),
    "notice_sending": ("Privater Voice-Hinweis wird versendet", "Sending the private voice reminder", "Envoi du rappel vocal privé"),
    "notice_sent": ("Spielserver hat den Versand des Hinweises bestätigt", "Game server confirmed the reminder was sent", "Envoi du rappel confirmé par le serveur de jeu"),
    "question_sending": ("Rückfrage wird vorbereitet", "Preparing the follow-up question", "Préparation de la question de suivi"),
    "awaiting_answer": ("Antwort aus dem Sprachkanal steht aus", "Waiting for a reply from the voice channel", "En attente d’une réponse du canal vocal"),
    "kick_ready": ("Weiterhin keine Antwort gemeldet, Kick wird geprüft", "Continued silence reported, checking kick eligibility", "Silence toujours signalé, vérification avant expulsion"),
    "working": ("Kommunikation klappt laut Rückmeldung wieder", "Communication restored according to the reply", "Communication rétablie d’après la réponse"),
    "expired": ("Antwortfrist abgelaufen", "Reply deadline expired", "Délai de réponse expiré"),
    "notice_failed": ("Versand des Hinweises unbestätigt", "Reminder delivery unconfirmed", "Envoi du rappel non confirmé"),
    "duplicate": ("Weiterer Bericht zum selben Vorfall", "Another report covers this incident", "Autre signalement pour le même incident"),
    "vote": ("Führungsabstimmung läuft", "Leadership vote in progress", "Vote de commandement en cours"),
    "vote_stop": ("Abstimmung beendet, Ergebnis prüfen", "Vote ended, review the outcome", "Vote terminé, vérifier le résultat"),
    "notice": ("Versand des Hinweises bestätigt", "Reminder sent by the server", "Envoi du rappel confirmé"),
    "squad": ("Rückfrage an ein Squadmitglied", "Follow-up for a squad member", "Question à un membre de l’escouade"),
    "command": ("Rückfrage an einen Teilnehmer des Führungskanals", "Follow-up for a command channel participant", "Question à un participant du canal de commandement"),
    "reply": ("Rückfrage an Kanalteilnehmer", "Follow-up for channel participant", "Question à un participant du canal"),
    "yes": ("Rückmeldung · Ja", "Reply · Yes", "Réponse · Oui"),
    "no": ("Rückmeldung · Nein", "Reply · No", "Réponse · Non"),
    "by": ("Gemeldet von", "Reported by", "Signalé par"),
    "voice": ("Voice-Meldung", "Voice report", "Signalement vocal"),
    "claimed": ("Meldung übernommen", "Report claimed", "Signalement pris en charge"),
    "teamkills": ("Teamkill gemeldet", "Teamkill reported", "Teamkill signalé"),
    "cheating": ("Cheatverdacht gemeldet", "Suspected cheating reported", "Soupçon de triche signalé"),
    "communication": ("Fehlende Kommunikation gemeldet", "Voice communication issue reported", "Problème de communication vocale signalé"),
    "vote_rejected": ("Abstimmung ohne Mehrheit", "Vote ended without a majority", "Vote terminé sans majorité"),
    "vote_cancelled": ("Abstimmung abgebrochen", "Vote cancelled", "Vote annulé"),
}

def voice_state(incident):
    # Older RCON envelopes expose the current mutable report record in events only.
    report = incident.get("report_admin") or {}
    if isinstance(report.get("voice"), dict):
        return report["voice"]
    for event in incident.get("events") or []:
        if event.get("event_type") == "report_admin":
            return (event.get("payload") or {}).get("voice") or {}
    return {}


def _state(incident, voice, automatic_kick, unresolved):
    report = incident.get("report_admin") or {}
    status = incident.get("status")
    state = report.get("status")
    phase = voice.get("phase")
    vote = incident.get("leadership_vote") or {}
    voting = vote.get("status")
    if status == "dismissed":
        return "dismissed", None
    if status == "resolved":
        if automatic_kick or (voting == "kicked" and vote.get("mode") == "active"):
            return "kicked", "closed"
        if phase == "resolved" and voice.get("answer") == "working":
            return "working", "closed"
        return "closed", None

    if voting in {"confirming", "warning", "inviting", "active", "executing"}:
        return "vote", "watch"
    if voting:
        result = {"rejected": "vote_rejected", "cancelled": "vote_cancelled",
                  "unknown": "unknown", "dry_run": "dry_run"}.get(voting, "vote_stop")
        return result, "review"
    if state == "voice":
        if phase in {"clarify", "notice_pending", "notice_sending", "notice_sent", "question_sending", "awaiting_answer"}:
            return phase, "watch"
        return "manual", "review"
    if state == "queued" and phase == "kick_ready":
        return "kick_ready", "watch"
    if state in {"classifying", "queued", "waiting", "sending"}:
        return state, "watch"
    if state in {"unknown", "dry_run"}:
        return state, "review"
    if phase == "duplicate":
        return "duplicate", "review"
    if state == "manual":
        key = voice.get("message_key")
        if key in {"expired", "notice_failed"}:
            return key, "review"
        if unresolved:
            return "unclear", "review"
        rule = report.get("rule")
        return rule if rule in {"cheating", "teamkills", "communication"} else "manual", "review"
    if unresolved:
        return "unclear", "review"
    if status == "claimed":
        return "claimed", "review"
    source = incident.get("source")
    return source if source in {"ai_chat", "ai_player_name"} else "new", "review"


def summary(incident, language, voice, *, automatic_kick, unresolved, assignee):
    index = {"de": 0, "en": 1, "fr": 2}[language]

    def label(key):
        return TEXT[key][index]

    event, action = _state(incident, voice, automatic_kick, unresolved)
    heading = label(event)
    if action:
        heading += " · " + label(action)
    lines = ["**" + heading + "**"]
    if incident.get("status") == "claimed" and assignee and not str(incident.get("assigned_to")).startswith("system:"):
        lines.append(label("owner").format(name=safe(assignee, 70)))
    if incident.get("reporter_name") and incident.get("source") in {"chat", "manual"}:
        lines.append(label("by") + " " + safe(incident["reporter_name"], 80))
    milestones = [
        ("notice_sent_at", "notice"),
        ("question_at", voice.get("channel") if voice.get("channel") in {"command", "squad"} else "reply"),
    ]
    if voice.get("answer") in {"working", "still_silent"}:
        milestones.append(("answer_at", "yes" if voice["answer"] == "working" else "no"))
    for field, key in milestones:
        at = voice.get(field)
        if type(at) in (float, int) and 0 < at < 253402300800 and isfinite(at):
            lines.append(f"<t:{int(at)}:T> · {label(key)}")
    return "\n".join(lines)
