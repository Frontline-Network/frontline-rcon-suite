"""The admin theme must not broaden access or replace Django's form handling."""

import ast
from pathlib import Path

from django.contrib import admin
from django.contrib.auth.models import Group, Permission, User
from django.test import Client, TestCase, override_settings
from django.urls import path, reverse

from .models import UserAppearancePreference
from .permission_help import permission_help
from .permission_presets import PRESETS, permission_presets

urlpatterns = [path("admin/", admin.site.urls)]


@override_settings(ROOT_URLCONF=__name__)
class AdminThemeTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create_superuser("theme-owner", password="only-for-tests")
        UserAppearancePreference.objects.create(user=cls.owner, preferences={"preset": "wardogs", "mode": "dark"})

    def setUp(self):
        self.client.force_login(self.owner)

    def test_dashboard_uses_only_registered_model_links(self):
        response = self.client.get(reverse("admin:index"))
        self.assertContains(response, 'class="crcon-admin-card"', count=4)
        self.assertContains(response, reverse("admin:auth_user_changelist"))
        self.assertContains(response, reverse("admin:api_mobiledevice_changelist"))
        self.assertNotContains(response, "/admin/api/mobiledevice/add/")

    def test_restricted_staff_only_sees_authorized_models(self):
        staff = User.objects.create_user("limited", is_staff=True)
        staff.user_permissions.add(Permission.objects.get(content_type__app_label="auth", codename="view_user"))
        UserAppearancePreference.objects.create(user=staff, preferences={"preset": "wardogs"})
        self.client.force_login(staff)
        response = self.client.get(reverse("admin:index"))
        self.assertContains(response, 'class="crcon-admin-card"', count=1)
        self.assertContains(response, reverse("admin:auth_user_changelist"))
        self.assertNotContains(response, reverse("admin:auth_user_add"))
        self.assertNotContains(response, reverse("admin:api_djangoapikey_changelist"))
        self.assertEqual(self.client.get(reverse("admin:api_djangoapikey_changelist")).status_code, 403)

    def test_theme_does_not_grant_non_staff_access(self):
        user = User.objects.create_user("non-staff")
        UserAppearancePreference.objects.create(user=user, preferences={"preset": "wardogs"})
        self.client.force_login(user)
        self.assertEqual(self.client.get(reverse("admin:index")).status_code, 302)

    def test_frontline_retains_original_dashboard(self):
        UserAppearancePreference.objects.filter(user=self.owner).update(preferences={"preset": "frontline-gold"})
        response = self.client.get(reverse("admin:index"))
        self.assertNotContains(response, 'class="crcon-admin-card"')
        self.assertContains(response, "Django")

    def test_missing_or_malformed_preferences_do_not_break_admin(self):
        for preferences in (None, [], {"preset": "wardogs", "mode": "invalid"}):
            with self.subTest(preferences=preferences):
                if preferences is None:
                    UserAppearancePreference.objects.filter(user=self.owner).delete()
                else:
                    UserAppearancePreference.objects.update_or_create(user=self.owner, defaults={"preferences": preferences})
                response = self.client.get(reverse("admin:index"))
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.context["crcon_admin_appearance"]["mode"], "dark")

    def test_standard_admin_forms_and_lists_render(self):
        for name, args in (
            ("auth_user_changelist", []), ("auth_user_add", []),
            ("auth_user_change", [self.owner.pk]), ("auth_group_changelist", []),
            ("auth_group_add", []), ("api_djangoapikey_changelist", []),
            ("api_djangoapikey_add", []), ("api_mobiledevice_changelist", []),
            ("password_change", []),
        ):
            with self.subTest(view=name):
                response = self.client.get(reverse(f"admin:{name}", args=args))
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, "api/css/admin-wardogs.css")
                embedded = self.client.get(reverse(f"admin:{name}", args=args) + "?embedded=1")
                self.assertEqual(embedded.status_code, 200)
                self.assertNotContains(embedded, "Datenbankfehler")

    def test_csrf_remains_required_for_admin_writes(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.owner)
        response = client.post(reverse("admin:auth_group_add"), {"name": "Must not be created"})
        self.assertEqual(response.status_code, 403)
        response = client.post(reverse("admin:auth_group_add") + "?embedded=1", {"name": "Must not be created"})
        self.assertEqual(response.status_code, 403)

    def test_django_validation_is_preserved(self):
        response = self.client.post(reverse("admin:auth_group_add"), {"name": ""})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["adminform"].form.errors.get("name"))

    def test_every_current_custom_permission_has_reviewed_help(self):
        unknown = [p.codename for p in Permission.objects.filter(content_type__app_label="api", codename__startswith="can_").select_related("content_type") if not permission_help(p)["documented"]]
        self.assertEqual(unknown, [])

    def test_explained_permission_widget_keeps_native_form_field(self):
        group = Group.objects.create(name="Read only")
        permission = Permission.objects.get(content_type__app_label="auth", codename="view_user")
        group.permissions.add(permission)
        response = self.client.get(reverse("admin:auth_user_change", args=[self.owner.pk]))
        self.assertContains(response, 'name="user_permissions"')
        self.assertContains(response, "id_user_permissions_help")
        self.assertContains(response, '"name": "Read only"')
        self.assertNotContains(response, 'class="selectfilter" name="user_permissions"')

    def test_group_permission_selection_roundtrips_without_broadening(self):
        group = Group.objects.create(name="Theme test group")
        read = Permission.objects.get(content_type__app_label="auth", codename="view_user")
        change = Permission.objects.get(content_type__app_label="auth", codename="change_user")
        group.permissions.set([read, change])
        response = self.client.post(reverse("admin:auth_group_change", args=[group.pk]), {"name": group.name, "permissions": [read.pk], "_save": "Save"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(list(group.permissions.values_list("pk", flat=True)), [read.pk])

    def test_embedding_only_allows_same_origin_and_keeps_redirect_context(self):
        response = self.client.get(reverse("admin:index"))
        self.assertEqual(response["X-Frame-Options"], "DENY")
        response = self.client.get(reverse("admin:index") + "?embedded=1")
        self.assertEqual(response["X-Frame-Options"], "SAMEORIGIN")
        self.assertIn("frame-ancestors 'self'", response["Content-Security-Policy"])
        self.client.logout()
        response = self.client.get(reverse("admin:index") + "?embedded=1")
        self.assertEqual(response.status_code, 302)
        self.assertIn("embedded=1", response["Location"])

    def test_embedded_search_preserves_django_filters(self):
        response = self.client.get(reverse("admin:auth_user_changelist"), {"embedded": "1", "ui_language": "de", "q": "no-such-account"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["cl"].result_count, 0)

    @override_settings(LANGUAGE_CODE="en-us")
    def test_embedded_admin_uses_selected_rcon_language(self):
        response = self.client.get(reverse("admin:auth_user_change", args=[self.owner.pk]), {"embedded": "1", "ui_language": "de"})
        self.assertContains(response, "Einzelne Berechtigungen")
        response = self.client.get(reverse("admin:auth_user_change", args=[self.owner.pk]), {"embedded": "1", "ui_language": "en"})
        self.assertContains(response, "Individual permissions")

    def test_group_choices_still_use_django_validation(self):
        group = Group.objects.create(name="Chosen group")
        response = self.client.get(reverse("admin:auth_user_change", args=[self.owner.pk]))
        field = response.context["adminform"].form.fields["groups"]
        self.assertEqual(list(field.clean([str(group.pk)])), [group])
        self.assertEqual(list(field.clean([])), [])
        from django.core.exceptions import ValidationError
        with self.assertRaises(ValidationError):
            field.clean(["9999999"])

    def test_role_presets_reference_existing_permissions_without_account_control(self):
        available = set(Permission.objects.filter(content_type__app_label="api", content_type__model="rconuser").values_list("codename", flat=True))
        forbidden = {"can_run_raw_commands", "can_add_admin_roles", "can_remove_admin_roles", "can_manage_all_mobile_devices", "can_view_steam_config", "can_change_steam_config", "can_view_rcon_connection_settings_config", "can_change_rcon_connection_settings_config"}
        for key, *_, codes in PRESETS:
            with self.subTest(preset=key):
                self.assertFalse(codes - available)
                self.assertFalse(codes & forbidden)
                self.assertTrue(all(code.startswith("can_") for code in codes))
                if key == "observer":
                    self.assertTrue(all(code.startswith("can_view_") for code in codes))

    def test_role_presets_never_add_choices_outside_the_field(self):
        read = Permission.objects.select_related("content_type").get(codename="can_view_gamestate")
        templates = permission_presets([read])
        self.assertTrue(templates)
        for template in templates:
            self.assertEqual(template["permissions"], [str(read.pk)])

    def test_opening_role_templates_does_not_change_group_rights(self):
        group = Group.objects.create(name="Unchanged")
        response = self.client.get(reverse("admin:auth_group_change", args=[group.pk]))
        self.assertContains(response, '"id": "moderator"')
        self.assertEqual(group.permissions.count(), 0)

    def test_admin_receives_saved_color_style_and_safe_legacy_default(self):
        from .wardogs_styles import WARDOGS_STYLES
        for style in [*WARDOGS_STYLES, None, "invalid", []]:
            with self.subTest(style=style):
                UserAppearancePreference.objects.filter(user=self.owner).update(preferences={"preset": "wardogs", "wardogsStyle": style})
                response = self.client.get(reverse("admin:index"))
                expected = style if isinstance(style, str) and style in WARDOGS_STYLES else "rose"
                self.assertEqual(response.context["crcon_admin_appearance"]["wardogsStyle"], expected)
                self.assertEqual(response.context["crcon_admin_appearance"]["wardogsStyles"], WARDOGS_STYLES)
                self.assertContains(response, "api/css/admin-wardogs-colors.css")


class PermissionPresetWorkflowTests(TestCase):
    """Check real Django group grants against the API's actual requirements.

    Read permission declarations via AST so the isolated admin suite need not
    boot the RCON server, Redis, or the game integration. No actions are sent.
    Endpoint lists describe the workflows, independently of preset allowlists.
    """

    @classmethod
    def setUpTestData(cls):
        permissions = Permission.objects.select_related("content_type").all()
        cls.roles = {}
        cls.groups = {}
        for preset in permission_presets(permissions):
            group = Group.objects.create(name=preset["id"])
            group.permissions.set(preset["permissions"])
            user = User.objects.create_user(preset["id"])
            user.groups.add(group)
            cls.roles[preset["id"]] = user
            cls.groups[preset["id"]] = group

        views = ast.parse(Path(__file__).with_name("views.py").read_text(encoding="utf-8"))
        declaration = next(node for node in views.body if isinstance(node, ast.AnnAssign)
                           and isinstance(node.target, ast.Name)
                           and node.target.id == "ENDPOINT_PERMISSIONS")
        cls.requirements = {key.attr: ast.literal_eval(value)
                            for key, value in zip(declaration.value.keys, declaration.value.values)}
        autobalancer = ast.parse(Path(__file__).with_name("autobalancer.py").read_text(encoding="utf-8"))
        for node in autobalancer.body:
            if not isinstance(node, ast.FunctionDef):
                continue
            for decorator in node.decorator_list:
                if isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Name) and decorator.func.id == "permission_required":
                    cls.requirements[node.name] = ast.literal_eval(decorator.args[0])

    def assert_workflow_allowed(self, role, endpoints):
        user = self.roles[role]
        for endpoint in endpoints:
            with self.subTest(role=role, endpoint=endpoint):
                required = self.requirements[endpoint]
                if isinstance(required, str):
                    required = [required]
                missing = [permission for permission in required if not user.has_perm(permission)]
                self.assertEqual(missing, [], f"{role}: {endpoint} needs {missing}")
                self.assertTrue(user.has_perms(required))

    def test_player_records_and_logs_load_for_read_and_moderation_roles(self):
        for role in ("observer", "support", "moderator"):
            self.assert_workflow_allowed(role, (
                "get_status", "get_gamestate", "get_team_view", "get_recent_logs",
                "get_maps", "get_players_history", "get_bans", "get_player_profile",
                "get_player_messages", "get_player_comments", "get_ban",
                "get_logs", "get_historical_logs", "get_blacklists", "get_blacklist_records",
            ))

    def test_moderator_can_complete_player_actions_and_reverse_bans(self):
        self.assert_workflow_allowed("moderator", (
            "get_message_templates", "get_standard_punishments_messages",
            "message_player", "post_player_comment", "watch_player", "unwatch_player",
            "kick", "punish", "remove_player_from_squad", "disband_squad_by_name",
            "switch_player_now", "switch_player_on_death", "temp_ban", "perma_ban",
            "remove_temp_ban", "remove_perma_ban", "unban", "flag_player", "unflag_player",
            "get_blacklists", "add_blacklist_record", "edit_blacklist_record",
            "delete_blacklist_record", "unblacklist_player",
        ))

    def test_moderator_can_operate_autobalancer_without_configuring_it(self):
        self.assert_workflow_allowed("moderator", (
            "get_autobalancer_config", "get_autobalancer_status", "get_autobalancer_history",
            "get_autobalancer_history_dashboard", "get_autobalancer_shadow_overview",
            "get_autobalancer_round_archive", "approve_autobalancer_proposal",
            "cancel_autobalancer_incident", "review_autobalancer_shadow_decision",
            "execute_autobalancer_squad_switch",
        ))
        self.assertFalse(self.roles["moderator"].has_perm("api.can_change_autobalancer_config"))

    def test_operations_can_manage_maps_and_voting_end_to_end(self):
        self.assert_workflow_allowed("operations", (
            "get_status", "get_maps", "get_map", "get_next_map", "set_map",
            "get_map_rotation", "set_map_rotation", "get_map_sequence", "set_map_sequence",
            "get_map_shuffle_enabled", "set_map_shuffle_enabled", "get_objective_rows",
            "set_game_layout", "set_dynamic_weather_enabled", "set_match_timer",
            "remove_match_timer", "set_warmup_timer", "remove_warmup_timer",
            "get_votemap_status", "get_votemap_results", "get_votemap_config",
            "validate_votemap_config", "set_votemap_config", "get_votemap_whitelist",
            "set_votemap_whitelist", "reset_map_votemap_whitelist",
            "add_map_to_votemap", "remove_map_from_votemap", "set_votemap_winner",
            "add_votemap_vote", "reset_votemap_state", "send_votemap_reminder",
        ))

    def test_operations_can_load_edit_and_test_server_messages(self):
        self.assert_workflow_allowed("operations", (
            "get_broadcast_message", "set_broadcast", "get_welcome_message", "set_welcome_message",
            "get_message_templates", "get_auto_broadcasts_config", "get_campaign_delivery_status",
            "get_vip_lifecycle_status", "preview_vip_lifecycle", "validate_auto_broadcasts_config",
            "set_auto_broadcasts_config", "get_players", "message_all_players", "message_player",
            "test_player_campaign", "test_vip_lifecycle_message",
        ))

    def test_roles_keep_distinct_responsibilities(self):
        for role, user in self.roles.items():
            with self.subTest(role=role):
                self.assertFalse(user.is_staff)
                self.assertFalse(user.is_superuser)
                self.assertFalse(user.has_perm("auth.change_user"))
                self.assertFalse(user.has_perm("auth.change_group"))
                self.assertFalse(user.has_perm("api.can_add_vip"))
                self.assertFalse(user.has_perm("api.can_delete_blacklists"))
                if role != "moderator":
                    for code in ("can_kick_players", "can_punish_players", "can_temp_ban_players", "can_perma_ban_players", "can_switch_players_immediately"):
                        self.assertFalse(user.has_perm(f"api.{code}"))
                if role != "operations":
                    self.assertFalse(user.has_perm("api.can_change_current_map"))
                    self.assertFalse(user.has_perm("api.can_change_auto_broadcast_config"))
        self.assertFalse(self.roles["operations"].has_perm("api.can_view_player_history"))

    def test_moderation_and_operations_can_be_combined(self):
        user = User.objects.create_user("combined")
        user.groups.add(self.groups["moderator"], self.groups["operations"])
        self.assertTrue(user.has_perms([
            "api.can_kick_players", "api.can_remove_player_from_squad",
            "api.can_change_current_map", "api.can_change_votemap_config",
            "api.can_change_auto_broadcast_config",
        ]))
        self.assertFalse(user.has_perm("auth.change_group"))
