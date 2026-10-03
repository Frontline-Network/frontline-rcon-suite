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
    german = (get_language() or "en").startswith("de")
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
            "wardogsStyle": color_style,
            "wardogsStyles": WARDOGS_STYLES,
        },
        "crcon_admin_text": {
            "title": "Administration",
            "subtitle": "Konten, Berechtigungen und Zugänge zentral verwalten." if german else "Manage accounts, permissions and access in one place.",
            "back": "Zum CRCON" if german else "Back to CRCON",
            "accounts": "Benutzer & Berechtigungen" if german else "Users & permissions",
            "connections": "Schnittstellen & Geräte" if german else "Integrations & devices",
            "open": "Verwalten" if german else "Manage",
            "add": "Hinzufügen" if german else "Add",
            "empty": "Keine Verwaltungsbereiche verfügbar." if german else "No administration areas available.",
            "recent": "Letzte Änderungen" if german else "Recent changes",
            "no_recent": "Deine Änderungen erscheinen hier, sobald du einen Eintrag bearbeitest." if german else "Your changes appear here after you edit an entry.",
            "overview": "Verwaltungsübersicht" if german else "Administration overview",
        },
    }
