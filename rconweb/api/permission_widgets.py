from django import forms
from django.contrib.auth.models import Group
from django.utils.html import json_script
from django.utils.safestring import mark_safe
from django.utils.translation import get_language

from .permission_help import permission_help
from .permission_presets import permission_presets
from .permission_workflows import permission_workflows
from .admin_theme import admin_appearance


class ExplainedPermissionSelect(forms.SelectMultiple):
    """Progressive enhancement: submit the ordinary ModelMultipleChoiceField."""

    class Media:
        css = {"all": ("api/css/permission-picker.css",)}
        js = ("api/js/permission-planner.js", "api/js/permission-picker.js",)

    def __init__(self, *args, permissions, **kwargs):
        self.permissions = permissions
        super().__init__(*args, **kwargs)

    def render(self, name, value, attrs=None, renderer=None):
        attrs = {**(attrs or {}), "class": "crcon-permission-select", "size": 12}
        german = (get_language() or "en").startswith("de")
        permission_objects = list(self.permissions.select_related("content_type"))
        catalog = [permission_help(permission, german) for permission in permission_objects]
        groups = []
        if name == "user_permissions":
            groups = [{"id": str(group.pk), "name": group.name, "permissions": [str(p.pk) for p in group.permissions.all()]}
                      for group in Group.objects.prefetch_related("permissions")]
        data = {"permissions": catalog, "groups": groups, "german": german, "direct": name == "user_permissions",
                "presets": permission_presets(permission_objects, german) if name == "permissions" else [],
                "workflows": permission_workflows(permission_objects, german)}
        return mark_safe(super().render(name, value, attrs, renderer) + json_script(data, attrs["id"] + "_help"))


class ExplainedPermissionsAdminMixin:
    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == "groups" and admin_appearance(request)["crcon_admin_wardogs"]:
            kwargs["widget"] = forms.SelectMultiple(attrs={"class": "crcon-group-select"})
            field = super().formfield_for_manytomany(db_field, request, **kwargs)
            field.help_text = ""
            return field
        if db_field.name in {"permissions", "user_permissions"}:
            kwargs["widget"] = forms.SelectMultiple
            field = super().formfield_for_manytomany(db_field, request, **kwargs)
            field.widget = ExplainedPermissionSelect(permissions=field.queryset)
            field.widget.choices = field.choices
            field.help_text = ""
            return field
        return super().formfield_for_manytomany(db_field, request, **kwargs)
