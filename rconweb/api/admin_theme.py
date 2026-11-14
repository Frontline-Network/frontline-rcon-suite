"""Presentation context for the Django admin; authorization stays with Django."""

from django.core.exceptions import ObjectDoesNotExist
from django.utils.translation import get_language
from .wardogs_styles import DEFAULT_WARDOGS_STYLE, WARDOGS_STYLES, normalize_wardogs_style


def admin_appearance(request):
    authenticated = bool(getattr(request, "user", None) and request.user.is_authenticated)
    preferences = {}
    if authenticated:
        try:
            preferences = request.user.appearance_preference.preferences
        except ObjectDoesNotExist:
            pass
    if not isinstance(preferences, dict):
        preferences = {}
    mode = preferences.get("mode", "dark")
    if mode not in {"dark", "light", "system"}:
        mode = "dark"
    language = (get_language() or "en").split("-")[0]
    def copy(de, en, fr):
        return {"de": de, "fr": fr}.get(language, en)
    try:
        color_style = normalize_wardogs_style(preferences.get("wardogsStyle", DEFAULT_WARDOGS_STYLE))
    except ValueError:
        color_style = DEFAULT_WARDOGS_STYLE
    return {
        "crcon_admin_wardogs": preferences.get("preset") == "wardogs",
        "crcon_admin_appearance": {
            "authenticated": authenticated,
            "preset": preferences.get("preset", "frontline-gold"),
            "mode": mode,
            "customAccent": preferences.get("customAccent", "#c59a4a"),
            "wardogsStyle": color_style,
            "wardogsStyles": WARDOGS_STYLES,
        },
        "crcon_admin_text": {
            "title": "Administration",
            "subtitle": copy("Konten, Berechtigungen und Zugänge zentral verwalten.", "Manage accounts, permissions and access in one place.", "Gérez les comptes, les autorisations et les accès au même endroit."),
            "back": copy("Zum CRCON", "Back to CRCON", "Retour à CRCON"),
            "accounts": copy("Benutzer & Berechtigungen", "Users & permissions", "Utilisateurs et autorisations"),
            "connections": copy("Schnittstellen & Geräte", "Integrations & devices", "Intégrations et appareils"),
            "open": copy("Verwalten", "Manage", "Gérer"),
            "add": copy("Hinzufügen", "Add", "Ajouter"),
            "empty": copy("Keine Verwaltungsbereiche verfügbar.", "No administration areas available.", "Aucune section d'administration disponible."),
            "recent": copy("Letzte Änderungen", "Recent changes", "Modifications récentes"),
            "no_recent": copy("Deine Änderungen erscheinen hier, sobald du einen Eintrag bearbeitest.", "Your changes appear here after you edit an entry.", "Vos modifications apparaîtront ici après la modification d'une entrée."),
            "overview": copy("Verwaltungsübersicht", "Administration overview", "Vue d'ensemble de l'administration"),
        },
    }
