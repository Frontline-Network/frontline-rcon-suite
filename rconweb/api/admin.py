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
from .admin_theme import admin_appearance


# Define an inline admin descriptor for Employee model
# which acts a bit like a singleton
class SteamPlayerInline(admin.StackedInline):
    model = SteamPlayer
    can_delete = False
    verbose_name_plural = "steamid"


class DjangoAPIKeyAdminForm(forms.ModelForm):
    class Meta:
        model = DjangoAPIKey
        fields = "__all__"

    def clean_api_key(self):
        if len(self.cleaned_data["api_key"]) < 32:
            raise forms.ValidationError("Minimum API key length is 32 characters")

        if DjangoAPIKey.objects.filter(
            api_key=make_password(
                self.cleaned_data["api_key"], salt=settings.SECRET_KEY.replace("$", "")
            )
        ).exists():
            raise forms.ValidationError("Duplicate API keys are not allowed")

        return self.cleaned_data["api_key"]


class DjangoAPIKeyInline(admin.StackedInline):
    model = DjangoAPIKey
    form = DjangoAPIKeyAdminForm

    can_delete = True
    verbose_name_plural = "API Keys"

    show_change_link = True

    extra = 0
    readonly_fields = ["date_created", "date_modified"]


# Define a new User admin
class UserAdmin(ExplainedPermissionsAdminMixin, BaseUserAdmin):
    inlines = (SteamPlayerInline, DjangoAPIKeyInline)

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if admin_appearance(request)["crcon_admin_wardogs"] and (get_language() or "en").startswith("de"):
            explanations = {
                "is_active": ("Konto aktiv", "Erlaubt die Anmeldung. Deaktivieren sperrt den Zugang, ohne das Konto zu löschen."),
                "is_staff": ("Administrationszugang", "Erlaubt den Zugang zu dieser Verwaltung. Welche Daten bearbeitet werden dürfen, bestimmen die Gruppen und Einzelrechte."),
                "is_superuser": ("Vollzugriff", "Erteilt sämtliche Berechtigungen. Gruppen und Einzelrechte können diesen Vollzugriff nicht einschränken."),
            }
            for name, (label, description) in explanations.items():
                if name in form.base_fields:
                    form.base_fields[name].label = label
                    form.base_fields[name].help_text = description
        return form

    def get_inline_instances(self, request, obj=None):
        inlines = super().get_inline_instances(request, obj)
        if admin_appearance(request)["crcon_admin_wardogs"] and (get_language() or "en").startswith("de"):
            for inline in inlines:
                if isinstance(inline, SteamPlayerInline):
                    inline.verbose_name = "Spielkonto"
                    inline.verbose_name_plural = "Spielkonto-Verknüpfung"
                elif isinstance(inline, DjangoAPIKeyInline):
                    inline.verbose_name = "API-Schlüssel"
                    inline.verbose_name_plural = "API-Schlüssel"
        return inlines

    def get_fieldsets(self, request, obj=None):
        if obj is None or not admin_appearance(request)["crcon_admin_wardogs"]:
            return super().get_fieldsets(request, obj)
        de = (get_language() or "en").startswith("de")
        return (
            ("Anmeldung" if de else "Sign-in", {"fields": ("username", "password"), "classes": ("crcon-account-panel",)}),
            ("Persönliche Informationen" if de else "Personal information", {"fields": (("first_name", "last_name"), "email"), "classes": ("crcon-profile-panel",)}),
            ("Zugang & Status" if de else "Access & status", {"fields": ("is_active", "is_staff", "is_superuser"), "classes": ("crcon-status-panel",)}),
            ("Gruppen & Rollen" if de else "Groups & roles", {"fields": ("groups",), "classes": ("crcon-groups-panel",)}),
            ("Einzelne Berechtigungen" if de else "Individual permissions", {"fields": ("user_permissions",), "classes": ("crcon-permissions-panel",)}),
            ("Kontodaten" if de else "Account dates", {"fields": ("last_login", "date_joined"), "classes": ("crcon-dates-panel",)}),
        )


class GroupAdmin(ExplainedPermissionsAdminMixin, BaseGroupAdmin):
    pass


class IntegrationAdminPresentation:
    def changelist_view(self, request, extra_context=None):
        if admin_appearance(request)["crcon_admin_wardogs"]:
            de = (get_language() or "en").startswith("de")
            title = ("API-Schlüssel" if de else "API keys") if self.model is DjangoAPIKey else ("Mobile Geräte" if de else "Mobile devices")
            extra_context = {**(extra_context or {}), "title": title}
        return super().changelist_view(request, extra_context)


class DjangoAPIKeyAdmin(IntegrationAdminPresentation, admin.ModelAdmin):
    list_display = ("user", "api_key", "date_created", "date_modified", "notes")
    list_filter = ("user",)
    search_fields = ("notes",)

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

    def has_add_permission(self, request):
        return False


# Re-register UserAdmin
admin.site.unregister(User)
admin.site.register(User, UserAdmin)
admin.site.unregister(Group)
admin.site.register(Group, GroupAdmin)
admin.site.register(DjangoAPIKey, DjangoAPIKeyAdmin)
