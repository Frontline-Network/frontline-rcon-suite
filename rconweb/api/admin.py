# Register your models here.
from django import forms
from django.conf import settings
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.admin import GroupAdmin as BaseGroupAdmin
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import Group, User
from django.utils.translation import get_language


from .models import DjangoAPIKey, MobileDevice, SteamPlayer
from .permission_widgets import ExplainedPermissionsAdminMixin


def _french_display(field, label):
    """Read the original field; translate only its admin presentation label."""
    @admin.display(description=label, ordering=field)
    def display(self, obj):
        return getattr(obj, field)
    return display


# Define an inline admin descriptor for Employee model
# which acts a bit like a singleton
class SteamPlayerAdminForm(forms.ModelForm):
    class Meta:
        model = SteamPlayer
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if (get_language() or "en").split("-")[0] == "fr" and "steam_id_64" in self.fields:
            self.fields["steam_id_64"].label = "Identifiant du joueur"


class SteamPlayerInline(admin.StackedInline):
    model = SteamPlayer
    form = SteamPlayerAdminForm
    can_delete = False
    verbose_name_plural = "steamid"


class DjangoAPIKeyAdminForm(forms.ModelForm):
    class Meta:
        model = DjangoAPIKey
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if (get_language() or "en").split("-")[0] == "fr":
            for name, label in {"user": "Utilisateur", "api_key": "Clé API", "notes": "Notes"}.items():
                if name in self.fields:
                    self.fields[name].label = label

    def clean_api_key(self):
        if len(self.cleaned_data["api_key"]) < 32:
            language = (get_language() or "en").split("-")[0]
            raise forms.ValidationError({"de": "Der API-Schlüssel muss mindestens 32 Zeichen lang sein.", "fr": "La clé API doit contenir au moins 32 caractères."}.get(language, "Minimum API key length is 32 characters"))

        if DjangoAPIKey.objects.filter(
            api_key=make_password(
                self.cleaned_data["api_key"], salt=settings.SECRET_KEY.replace("$", "")
            )
        ).exists():
            language = (get_language() or "en").split("-")[0]
            raise forms.ValidationError({"de": "Doppelte API-Schlüssel sind nicht erlaubt.", "fr": "Les clés API en double ne sont pas autorisées."}.get(language, "Duplicate API keys are not allowed"))

        return self.cleaned_data["api_key"]


class DjangoAPIKeyInline(admin.StackedInline):
    model = DjangoAPIKey
    form = DjangoAPIKeyAdminForm

    can_delete = True
    verbose_name_plural = "API Keys"

    show_change_link = True

    extra = 0
    readonly_fields = ["date_created", "date_modified"]
    fr_date_created = _french_display("date_created", "Date de création")
    fr_date_modified = _french_display("date_modified", "Date de modification")

    def get_readonly_fields(self, request, obj=None):
        fields = super().get_readonly_fields(request, obj)
        if (get_language() or "en").split("-")[0] == "fr":
            return tuple(fields) + ("fr_date_created", "fr_date_modified")
        return fields

    def get_fields(self, request, obj=None):
        fields = super().get_fields(request, obj)
        if (get_language() or "en").split("-")[0] == "fr":
            mapping = {"date_created": "fr_date_created", "date_modified": "fr_date_modified"}
            return [mapping.get(field, field) for field in fields if field not in mapping.values()]
        return fields


# Define a new User admin
class UserAdmin(ExplainedPermissionsAdminMixin, BaseUserAdmin):
    inlines = (SteamPlayerInline, DjangoAPIKeyInline)

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        language = (get_language() or "en").split("-")[0]
        if language in {"de", "fr"}:
            explanations = {
                "is_active": ("Konto aktiv", "Erlaubt die Anmeldung. Deaktivieren sperrt den Zugang, ohne das Konto zu löschen."),
                "is_staff": ("Administrationszugang", "Erlaubt den Zugang zu dieser Verwaltung. Welche Daten bearbeitet werden dürfen, bestimmen die Gruppen und Einzelrechte."),
                "is_superuser": ("Vollzugriff", "Erteilt sämtliche Berechtigungen. Gruppen und Einzelrechte können diesen Vollzugriff nicht einschränken."),
            } if language == "de" else {
                "is_active": ("Compte actif", "Autorise la connexion. La désactivation bloque l'accès sans supprimer le compte."),
                "is_staff": ("Accès à l'administration", "Autorise l'accès à cette administration. Les groupes et autorisations individuelles déterminent les données modifiables."),
                "is_superuser": ("Accès complet", "Accorde toutes les autorisations. Les groupes et autorisations individuelles ne peuvent pas limiter cet accès."),
            }
            for name, (label, description) in explanations.items():
                if name in form.base_fields:
                    form.base_fields[name].label = label
                    form.base_fields[name].help_text = description
        return form

    def get_inline_instances(self, request, obj=None):
        inlines = super().get_inline_instances(request, obj)
        language = (get_language() or "en").split("-")[0]
        if language in {"de", "fr"}:
            for inline in inlines:
                if isinstance(inline, SteamPlayerInline):
                    inline.verbose_name = "Spielkonto" if language == "de" else "Compte de jeu"
                    inline.verbose_name_plural = "Spielkonto-Verknüpfung" if language == "de" else "Association du compte de jeu"
                elif isinstance(inline, DjangoAPIKeyInline):
                    inline.verbose_name = "API-Schlüssel" if language == "de" else "Clé API"
                    inline.verbose_name_plural = "API-Schlüssel" if language == "de" else "Clés API"
        return inlines

    def get_fieldsets(self, request, obj=None):
        if obj is None:
            return super().get_fieldsets(request, obj)
        language = (get_language() or "en").split("-")[0]
        def label(de, en, fr):
            return {"de": de, "fr": fr}.get(language, en)
        return (
            (label("Anmeldung", "Sign-in", "Connexion"), {"fields": ("username", "password"), "classes": ("crcon-account-panel",)}),
            (label("Persönliche Informationen", "Personal information", "Informations personnelles"), {"fields": (("first_name", "last_name"), "email"), "classes": ("crcon-profile-panel",)}),
            (label("Zugang & Status", "Access & status", "Accès et statut"), {"fields": ("is_active", "is_staff", "is_superuser"), "classes": ("crcon-status-panel",)}),
            (label("Gruppen & Rollen", "Groups & roles", "Groupes et rôles"), {"fields": ("groups",), "classes": ("crcon-groups-panel",)}),
            (label("Einzelne Berechtigungen", "Individual permissions", "Autorisations individuelles"), {"fields": ("user_permissions",), "classes": ("crcon-permissions-panel",)}),
            (label("Kontodaten", "Account dates", "Dates du compte"), {"fields": ("last_login", "date_joined"), "classes": ("crcon-dates-panel",)}),
        )


class GroupAdmin(ExplainedPermissionsAdminMixin, BaseGroupAdmin):
    pass


class IntegrationAdminPresentation:
    def changelist_view(self, request, extra_context=None):
        language = (get_language() or "en").split("-")[0]
        title = ({"de": "API-Schlüssel", "fr": "Clés API"}.get(language, "API keys") if self.model is DjangoAPIKey
                 else {"de": "Mobile Geräte", "fr": "Appareils mobiles"}.get(language, "Mobile devices"))
        extra_context = {**(extra_context or {}), "title": title}
        return super().changelist_view(request, extra_context)


class DjangoAPIKeyAdmin(IntegrationAdminPresentation, admin.ModelAdmin):
    list_display = ("user", "api_key", "date_created", "date_modified", "notes")
    list_filter = ("user",)
    search_fields = ("notes",)
    fr_user = _french_display("user", "Utilisateur")
    fr_api_key = _french_display("api_key", "Clé API")
    fr_date_created = _french_display("date_created", "Date de création")
    fr_date_modified = _french_display("date_modified", "Date de modification")
    fr_notes = _french_display("notes", "Notes")

    def get_list_display(self, request):
        if (get_language() or "en").split("-")[0] == "fr":
            return ("fr_user", "fr_api_key", "fr_date_created", "fr_date_modified", "fr_notes")
        return super().get_list_display(request)

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        return form

    form = DjangoAPIKeyAdminForm


@admin.register(MobileDevice)
class MobileDeviceAdmin(IntegrationAdminPresentation, admin.ModelAdmin):
    list_display = (
        "name",
        "user",
        "platform",
        "created_at",
        "last_seen_at",
        "revoked_at",
    )
    list_filter = ("platform", "notifications_enabled", "revoked_at")
    search_fields = ("name", "user__username")
    readonly_fields = (
        "id",
        "user",
        "platform",
        "app_version",
        "created_at",
        "last_seen_at",
        "revoked_at",
        "refresh_expires_at",
        "absolute_expires_at",
    )
    exclude = ("refresh_token_digest", "push_handle", "push_capability")
    fr_id = _french_display("id", "Identifiant")
    fr_user = _french_display("user", "Utilisateur")
    fr_name = _french_display("name", "Nom")
    fr_platform = _french_display("platform", "Plateforme")
    fr_app_version = _french_display("app_version", "Version de l'application")
    fr_created_at = _french_display("created_at", "Date de création")
    fr_last_seen_at = _french_display("last_seen_at", "Dernière activité")
    fr_revoked_at = _french_display("revoked_at", "Révoqué le")
    fr_refresh_expires_at = _french_display("refresh_expires_at", "Expiration du jeton de renouvellement")
    fr_absolute_expires_at = _french_display("absolute_expires_at", "Expiration définitive")

    def get_list_display(self, request):
        if (get_language() or "en").split("-")[0] == "fr":
            return ("fr_name", "fr_user", "fr_platform", "fr_created_at", "fr_last_seen_at", "fr_revoked_at")
        return super().get_list_display(request)

    def get_readonly_fields(self, request, obj=None):
        fields = super().get_readonly_fields(request, obj)
        if (get_language() or "en").split("-")[0] == "fr":
            return tuple(fields) + tuple("fr_" + field for field in fields)
        return fields

    def get_fields(self, request, obj=None):
        fields = super().get_fields(request, obj)
        if (get_language() or "en").split("-")[0] == "fr":
            mapping = {field: "fr_" + field for field in self.readonly_fields}
            return [mapping.get(field, field) for field in fields if field not in mapping.values()]
        return fields

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if (get_language() or "en").split("-")[0] == "fr":
            for name, label in {"name": "Nom", "platform": "Plateforme", "notifications_enabled": "Notifications activées"}.items():
                if name in form.base_fields:
                    form.base_fields[name].label = label
        return form

    def has_add_permission(self, request):
        return False


# Re-register UserAdmin
admin.site.unregister(User)
admin.site.register(User, UserAdmin)
admin.site.unregister(Group)
admin.site.register(Group, GroupAdmin)
admin.site.register(DjangoAPIKey, DjangoAPIKeyAdmin)
