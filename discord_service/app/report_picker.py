"""Discord's report modal uses a single-select with at most 25 live player options."""

import hashlib
import re
from collections import Counter, defaultdict

REF = re.compile(r"[0-9a-f]{32}")
GROUP = re.compile(r"(?:g:[0-9a-f]{20}:\d{1,3}|p:\d{1,3})")
TEXT = {
    "select_player": (
        "Spieler auswählen",
        "Select player",
        "Choisir le joueur",
        "Wybierz gracza",
        "Kies speler",
    ),
    "group": (
        "Team und Squad auswählen",
        "Select team and squad",
        "Choisir l’équipe et l’escouade",
        "Wybierz drużynę i oddział",
        "Kies team en squad",
    ),
    "empty": (
        "Derzeit ist niemand auf dem Server.",
        "No players are online.",
        "Aucun joueur en ligne.",
        "Brak graczy online.",
        "Er zijn geen spelers online.",
    ),
    "gone": (
        "Die Auswahl hat sich geändert. Bitte wähle erneut.",
        "The roster changed. Please choose again.",
        "La liste a changé. Choisis à nouveau.",
        "Lista się zmieniła. Wybierz ponownie.",
        "De lijst is gewijzigd. Kies opnieuw.",
    ),
    "retry": (
        "Spielerliste neu laden",
        "Reload player list",
        "Actualiser la liste",
        "Odśwież listę",
        "Spelerslijst vernieuwen",
    ),
    "unavailable": (
        "Die Spielerliste ist gerade nicht verfügbar.",
        "The roster is temporarily unavailable.",
        "La liste est momentanément indisponible.",
        "Lista graczy jest chwilowo niedostępna.",
        "De spelerslijst is tijdelijk niet beschikbaar.",
    ),
    "unassigned": (
        "Ohne Squad",
        "No squad",
        "Sans escouade",
        "Bez oddziału",
        "Geen squad",
    ),
    "no_team": ("Ohne Team", "No team", "Sans équipe", "Bez drużyny", "Geen team"),
    "commander": ("Commander", "Commander", "Commandant", "Dowódca", "Commandant"),
    "prev": ("Zurück", "Back", "Précédent", "Wstecz", "Vorige"),
    "next": ("Weiter", "Next", "Suivant", "Dalej", "Volgende"),
}


def picker_view(players, selected, label):
    """Return either modal player options, a private squad menu, or actionable feedback."""
    if not players:
        return "empty", []
    groups = defaultdict(list)
    names = Counter(p["name"].casefold() for p in players)
    for p in sorted(players, key=lambda p: (p["name"].casefold(), p["ref"])):
        team = p["team"] or label("no_team")
        squad = p["squad"]
        kind = "squad"
        if p["commander"]:
            kind, squad = "commander", label("commander")
        elif squad.casefold() in {"", "none", "unset", "unassigned", "command"}:
            kind, squad = "unassigned", label("unassigned")
        group = (p["team"], kind, p["squad"] if kind == "squad" else "")
        title = f"{team} · {squad}"
        detail = title + (" · " + p["role"].capitalize() if p["role"] else "")
        opt = {"label": p["name"][:100], "value": p["ref"], "description": detail[:100]}
        if names[p["name"].casefold()] > 1:
            opt["description"] = detail[:89] + " · " + p["ref"][:6]
        groups[(title, group)].append(opt)

    menus, all_players = [], []
    for (title, group), rows in sorted(groups.items()):
        group_id = hashlib.sha256(repr(group).encode()).hexdigest()[:20]
        all_players.extend(rows)
        for offset in range(0, len(rows), 25):
            key = f"g:{group_id}:{offset // 25}"
            if selected == key:
                return "player", rows[offset : offset + 25]
            suffix = (
                f" ({offset + 1}–{min(offset + 25, len(rows))})"
                if len(rows) > 25
                else ""
            )
            menus.append({"label": title[: 100 - len(suffix)] + suffix, "value": key})
    if len(players) <= 25 and not selected:
        return "player", sorted(
            all_players, key=lambda r: (r["label"].casefold(), r["value"])
        )
    if selected and not selected.startswith("p:"):
        return "gone", []
    if len(menus) <= 25:
        return "group", menus
    page = min(int(selected[2:]) if selected else 0, (len(menus) - 1) // 23)
    opts = menus[page * 23 : (page + 1) * 23]
    if page:
        opts.append({"label": label("prev"), "value": f"p:{page-1}"})
    if (page + 1) * 23 < len(menus):
        opts.append({"label": label("next"), "value": f"p:{page+1}"})
    return "group", opts


def player_modal(
    identifier, title, player_label, reason_label, options, *, clarify=False
):
    select = {
        "type": 3,
        "custom_id": "target_ref",
        "min_values": 1,
        "max_values": 1,
        "required": True,
        "options": options,
    }
    components = [{"type": 18, "label": player_label[:45], "component": select}]
    if not clarify:
        components.append(
            {
                "type": 18,
                "label": reason_label[:45],
                "component": {
                    "type": 4,
                    "custom_id": "message",
                    "style": 2,
                    "max_length": 2000,
                    "required": True,
                },
            }
        )
    return {
        "type": 9,
        "data": {
            "custom_id": identifier,
            "title": title[:45],
            "components": components,
        },
    }
