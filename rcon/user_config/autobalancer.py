from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from rcon.user_config.utils import BaseUserConfig, set_user_config


class AutobalancerMessages(BaseModel):
    volunteer_request: str = Field(
        default=(
            "Die Teams sind unausgeglichen. Freiwilliger Wechsel zu {target_team}: "
            "Schreibe innerhalb von {seconds} Sekunden !balance."
        ),
        title="Aufruf für Freiwillige",
        description=(
            "Direktnachricht an geeignete Spieler des größeren Teams. "
            "Erlaubte Platzhalter: {target_team} und {seconds}. Im Shadow-Modus "
            "werden keine Nachrichten gesendet."
        ),
    )
    volunteer_registered: str = Field(
        default="Danke! Deine freiwillige Meldung gilt für diesen Balance-Vorfall.",
        title="Bestätigung für Freiwillige",
        description="Antwort an einen Spieler, nachdem !balance akzeptiert wurde.",
    )
    candidate_selected: str = Field(
        default=(
            "Du wurdest für den Teamausgleich zu {target_team} ausgewählt. "
            "Der Wechsel erfolgt nach deinem nächsten Tod; danach bist du "
            "{cooldown_maps} Karten geschützt."
        ),
        title="Ankündigung der Auswahl",
        description=(
            "Nachricht an den ausgewählten Spieler. Erlaubte Platzhalter: "
            "{target_team} und {cooldown_maps}."
        ),
    )
    switch_completed: str = Field(
        default=(
            "Danke für deine Mithilfe. Du wurdest zu {target_team} verschoben und "
            "bist nun {cooldown_maps} Karten vor einem weiteren "
            "Autobalance-Wechsel geschützt."
        ),
        title="Bestätigung nach dem Wechsel",
        description=(
            "Nachricht nach einem bestätigten Wechsel. Erlaubte Platzhalter: "
            "{target_team} und {cooldown_maps}."
        ),
    )
    squad_switch_selected: str = Field(
        default=(
            "Euer Squad {squad_name} wird jetzt gemeinsam zu {target_team} "
            "verschoben. Bitte bildet den Squad dort anschließend neu."
        ),
        title="Ankündigung eines Squad-Wechsels",
        description=(
            "Direktnachricht an jedes aktuelle Mitglied vor einem manuell "
            "freigegebenen Squad-Wechsel. Erlaubte Platzhalter: {squad_name} "
            "und {target_team}."
        ),
    )
    squad_switch_completed: str = Field(
        default=(
            "Der gemeinsame Wechsel zu {target_team} ist abgeschlossen. "
            "Bitte bildet Squad {squad_name} in diesem Team neu."
        ),
        title="Bestätigung eines Squad-Wechsels",
        description=(
            "Direktnachricht nach dem erfolgreichen Wechsel eines Mitglieds. "
            "Erlaubte Platzhalter: {squad_name} und {target_team}."
        ),
    )
    squad_switch_aborted: str = Field(
        default=(
            "Der gemeinsame Wechsel von Squad {squad_name} konnte nicht vollständig "
            "ausgeführt werden. Bitte wartet auf eine Anweisung der Moderation."
        ),
        title="Abbruchmeldung eines Squad-Wechsels",
        description=(
            "Direktnachricht, falls sich die Squad-Zusammensetzung geändert hat "
            "oder der Gameserver einen Teil des Wechsels ablehnt. Erlaubter "
            "Platzhalter: {squad_name}."
        ),
    )

    @model_validator(mode="after")
    def validate_templates(self):
        try:
            self.volunteer_request.format(target_team="Axis", seconds=30)
            self.volunteer_registered.format()
            self.candidate_selected.format(target_team="Axis", cooldown_maps=3)
            self.switch_completed.format(target_team="Axis", cooldown_maps=3)
            self.squad_switch_selected.format(squad_name="Able", target_team="Axis")
            self.squad_switch_completed.format(squad_name="Able", target_team="Axis")
            self.squad_switch_aborted.format(squad_name="Able")
        except (KeyError, IndexError, ValueError) as exc:
            raise ValueError(f"Ungültiger Platzhalter in Nachrichtenvorlage: {exc}")
        return self


class AutobalancerEnglishMessages(AutobalancerMessages):
    volunteer_request: str = (
        "The teams are uneven. Volunteer to join {target_team}: type !balance within {seconds} seconds."
    )
    volunteer_registered: str = "Thank you! You have volunteered for this balance call."
    candidate_selected: str = (
        "You have been selected to join {target_team}. You will switch after your next death, then be protected for {cooldown_maps} maps."
    )
    switch_completed: str = (
        "Thank you for helping! You have joined {target_team} and are protected from another automatic switch for {cooldown_maps} maps."
    )
    squad_switch_selected: str = (
        "Your squad {squad_name} will now move together to {target_team}. Please recreate the squad there afterwards."
    )
    squad_switch_completed: str = (
        "The move to {target_team} is complete. Please recreate squad {squad_name} on that team."
    )
    squad_switch_aborted: str = (
        "Squad {squad_name} could not be moved completely. Please wait for instructions from an admin."
    )


class AutobalancerUserConfig(BaseUserConfig):
    mode: Literal["disabled", "shadow", "manual", "auto"] = Field(
        default="disabled",
        title="Betriebsart",
        description=(
            "disabled = aus; shadow = nur beobachten und protokollieren; "
            "manual = Vorschlag muss von einem Admin freigegeben werden; "
            "auto = nach der Freiwilligenphase automatisch auswählen. "
            "Auch auto wechselt ausschließlich nach dem Tod."
        ),
    )
    poll_interval_seconds: int = Field(
        default=5,
        ge=2,
        le=60,
        title="Prüfintervall (Sekunden)",
        description="Wie oft Teamzahlen und Kandidatenbedingungen neu geprüft werden.",
    )
    target_difference: int = Field(
        default=2,
        ge=0,
        le=10,
        title="Erlaubte Teamdifferenz",
        description=(
            "Bis zu dieser Differenz greift der Balancer nicht ein. Bei 2 sind "
            "beispielsweise 50:48 und 49:47 noch zulässig."
        ),
    )
    minimum_players: int = Field(
        default=40,
        ge=0,
        le=100,
        title="Mindestanzahl Spieler",
        description=(
            "Unterhalb dieser Gesamtspielerzahl beginnt kein Balance-Vorfall. "
            "Zusätzlich sperren aktive Seeding-Grenzen automatische Wechsel."
        ),
    )
    stable_difference_seconds: int = Field(
        default=45,
        ge=5,
        le=600,
        title="Ungleichgewicht muss bestehen (Sekunden)",
        description=(
            "Die Teamdifferenz muss so lange ohne Richtungswechsel über dem "
            "Grenzwert liegen, bevor ein Vorfall beginnt."
        ),
    )
    volunteer_phase_seconds: int = Field(
        default=30,
        ge=0,
        le=300,
        title="Freiwilligenphase (Sekunden)",
        description=(
            "Zeit für !balance, bevor ein Kandidat gewählt wird. Gilt nur in "
            "manual und auto; shadow sendet keine Nachrichten."
        ),
    )
    map_start_grace_minutes: int = Field(
        default=5,
        ge=0,
        le=60,
        title="Schutz nach Kartenstart (Minuten)",
        description="In den ersten Minuten einer Karte wird niemand ausgewählt.",
    )
    map_end_guard_minutes: int = Field(
        default=10,
        ge=0,
        le=60,
        title="Schutz vor Kartenende (Minuten)",
        description=(
            "In den letzten Minuten der Runde wird kein neuer Wechsel geplant."
        ),
    )
    candidate_timeout_seconds: int = Field(
        default=180,
        ge=15,
        le=900,
        title="Timeout für ausgewählten Spieler (Sekunden)",
        description=(
            "Wartezeit auf den nächsten Tod. Danach wird die Auswahl verworfen "
            "und vollständig neu geplant."
        ),
    )
    manual_proposal_timeout_seconds: int = Field(
        default=120,
        ge=15,
        le=900,
        title="Timeout für Admin-Freigabe (Sekunden)",
        description=(
            "So lange bleibt ein Vorschlag im Modus manual zur Freigabe offen."
        ),
    )
    connection_grace_seconds: int = Field(
        default=120,
        ge=0,
        le=1800,
        title="Schutz nach Verbindung (Sekunden)",
        description=(
            "Neu verbundene Spieler sind für diese Zeit von der Auswahl ausgeschlossen."
        ),
    )
    cooldown_maps: int = Field(
        default=3,
        ge=0,
        le=20,
        title="Schutz nach Wechsel (Karten)",
        description=(
            "Ein bereits automatisch verschobener Spieler wird so viele Karten "
            "lang nicht erneut ausgewählt."
        ),
    )
    max_switches_per_incident: int = Field(
        default=3,
        ge=1,
        le=10,
        title="Maximale Wechsel pro Vorfall",
        description=(
            "Sicherheitsgrenze. Nach jedem einzelnen Wechsel werden alle Daten "
            "neu geprüft und der übrige Plan verworfen."
        ),
    )
    coordinated_squad_switches_enabled: bool = Field(
        default=False,
        title="Koordinierte Squad-Wechsel erlauben",
        description=(
            "Erlaubt Administratoren, einen aus den Live-Daten geprüften "
            "Infanterie-Squad gemeinsam zu verschieben. Die Aktion wird niemals "
            "automatisch ausgeführt und benötigt eine gesonderte Bestätigung."
        ),
    )
    allow_individual_squad_fallback: bool = Field(
        default=True,
        title="Einzelspieler aus Squads als Rückfall zulassen",
        description=(
            "Wenn deaktiviert, darf der automatische Einzelspieler-Plan nur "
            "unzugewiesene Spieler oder alleinige Squad-Mitglieder auswählen. "
            "Manuelle vollständige Squad-Wechsel bleiben davon unberührt."
        ),
    )
    death_event_max_age_seconds: int = Field(
        default=5,
        ge=1,
        le=30,
        title="Maximales Alter eines Todesereignisses (Sekunden)",
        description=("Nur ein frischer Tod darf einen vorgemerkten Wechsel auslösen."),
    )
    switch_confirmation_timeout_seconds: int = Field(
        default=15,
        ge=5,
        le=60,
        title="Bestätigung des Teamwechsels (Sekunden)",
        description=(
            "Zeitfenster, in dem Teamwechsel-Log und neuer Snapshot den Wechsel "
            "bestätigen müssen."
        ),
    )
    history_server_numbers: list[int] = Field(
        default_factory=list,
        title="Servernummern für Spielstärke-Historie",
        description=(
            "CRCON-Servernummern, deren abgeschlossene Karten für die sekundäre "
            "Stärkeschätzung verwendet werden dürfen. Für FLN: 1 und 2."
        ),
    )
    skill_strategy: Literal["balanced-v2", "squad-first"] = Field(
        default="balanced-v2",
        title="Shadow-Auswahlstrategie",
        description=(
            "balanced-v2 schützt Squads zuerst, darf bei einer groben "
            "Stärkeschieflage aber höchstens eine Schutzstufe eskalieren. "
            "squad-first bildet die bisherige Referenzstrategie ab."
        ),
    )
    skill_gap_soft_limit: float = Field(
        default=8.0,
        ge=0,
        le=100,
        title="Weiches Stärke-Limit",
        description=(
            "Oberhalb dieser projizierten durchschnittlichen Ratingdifferenz "
            "darf balanced-v2 eine um höchstens eine Stufe stärker geschützte "
            "Alternative prüfen."
        ),
    )
    skill_gap_hard_warning: float = Field(
        default=12.0,
        ge=0,
        le=100,
        title="Warnschwelle für Stärke",
        description=(
            "Ab dieser projizierten Ratingdifferenz erscheint eine deutliche "
            "Adminwarnung. Die Warnung umgeht keine Schutzregel."
        ),
    )
    skill_gap_min_improvement: float = Field(
        default=2.5,
        ge=0,
        le=100,
        title="Mindestverbesserung für Eskalation",
        description=(
            "Eine stärker geschützte Alternative wird nur empfohlen, wenn sie "
            "die projizierte Ratingdifferenz mindestens um diesen Wert senkt."
        ),
    )
    history_half_life_days: int = Field(
        default=30,
        ge=1,
        le=365,
        title="Halbwertszeit historischer Leistung",
        description=(
            "Leistungsdaten verlieren über diesen Zeitraum die Hälfte ihres "
            "Gewichts. Die 90-Tage- und 20-Karten-Grenzen gelten zusätzlich."
        ),
    )
    volunteer_command: str = Field(
        default="!balance",
        min_length=2,
        max_length=32,
        title="Chatbefehl für Freiwillige",
        description=(
            "Gilt nur während der aktuellen Freiwilligenphase und nur für Spieler "
            "im größeren Team."
        ),
    )
    messages: AutobalancerMessages = Field(
        default_factory=AutobalancerMessages,
        title="Spielernachrichten – Deutsch",
        description=(
            "Nachrichten für Freiwillige, Auswahl und bestätigten Wechsel. Im "
            "Shadow-Modus werden keine Nachrichten gesendet."
        ),
    )
    message_language: Literal["de", "en", "de+en"] = Field(
        default="de",
        title="Nachrichtensprache",
        description="de = Deutsch; en = Englisch; de+en = zwei getrennte Nachrichten, zuerst Deutsch, dann Englisch. Bestehende deutsche Vorlagen bleiben erhalten.",
    )
    messages_en: AutobalancerEnglishMessages = Field(
        default_factory=AutobalancerEnglishMessages,
        title="Spielernachrichten – Englisch",
        description="Eigenständige englische Vorlagen mit denselben Platzhaltern. Die Nachrichtensprache bestimmt, welche Pakete gesendet werden.",
    )

    @field_validator("volunteer_command")
    @classmethod
    def validate_volunteer_command(cls, value: str) -> str:
        value = value.strip()
        if not value.startswith("!") or any(character.isspace() for character in value):
            raise ValueError("volunteer_command muss ein einzelner !Chatbefehl sein")
        return value

    @model_validator(mode="after")
    def validate_windows(self):
        if self.target_difference < 0:
            raise ValueError("target_difference must be non-negative")
        if self.max_switches_per_incident < 1:
            raise ValueError("max_switches_per_incident must be at least one")
        if self.skill_gap_hard_warning < self.skill_gap_soft_limit:
            raise ValueError(
                "skill_gap_hard_warning must be greater than or equal to the soft limit"
            )
        return self

    @staticmethod
    def save_to_db(values: dict, dry_run: bool = False):
        validated = AutobalancerUserConfig.model_validate(values)
        if not dry_run:
            set_user_config(AutobalancerUserConfig.KEY(), validated)
        return True
