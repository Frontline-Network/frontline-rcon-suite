from django import template
from django.utils.translation import get_language

register = template.Library()


@register.filter
def admin_app_order(apps):
    return sorted(apps, key=lambda app: (app["app_label"] != "auth", app["name"]))


@register.simple_tag
def admin_navigation(apps):
    return [
        {"title": admin_model_presentation(model)["title"], "url": model["admin_url"]}
        for app in admin_app_order(apps or []) for model in app["models"]
        if model.get("admin_url")
    ]


@register.simple_tag
def admin_model_presentation(model):
    german = (get_language() or "en").startswith("de")
    descriptions = {
        "User": ("Benutzer", "Users", "Konten, Anmeldedaten und persönliche Zugriffsrechte.", "Accounts, sign-in details and individual permissions.", "users"),
        "Group": ("Gruppen", "Groups", "Rollen bündeln und Berechtigungen gemeinsam vergeben.", "Organize roles and assign shared permissions.", "shield"),
        "DjangoAPIKey": ("API-Schlüssel", "API keys", "Zugänge für Integrationen und externe Werkzeuge.", "Access for integrations and external tools.", "key"),
        "MobileDevice": ("Mobile Geräte", "Mobile devices", "Gekoppelte Geräte und ihren Zugriffsstatus prüfen.", "Inspect paired devices and their access status.", "device"),
    }
    item = descriptions.get(model.get("object_name"))
    if not item:
        return {"title": model["name"], "description": "", "icon": "shield"}
    return {"title": item[0 if german else 1], "description": item[2 if german else 3], "icon": item[4]}
