"""Task bundles are presentation helpers, not an alternate authorization layer."""
import ast
from pathlib import Path

from django.contrib.auth.models import Group, Permission, User
from django.test import TestCase, override_settings
from django.urls import reverse

from .permission_help import permission_help
from .permission_workflows import WORKFLOWS, permission_workflows
from .permission_wizard import wizard_metadata


class PermissionWorkflowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.permissions = list(Permission.objects.select_related('content_type').all())
        cls.by_id = {str(p.pk): p for p in cls.permissions}
        cls.workflows = {w['id']: w for w in permission_workflows(cls.permissions)}
        source = ast.parse(Path(__file__).with_name('views.py').read_text(encoding='utf-8'))
        declaration = next(n for n in source.body if isinstance(n, ast.AnnAssign) and getattr(n.target, 'id', '') == 'ENDPOINT_PERMISSIONS')
        cls.requirements = {k.attr: ast.literal_eval(v) for k, v in zip(declaration.value.keys, declaration.value.values)}

    def codes(self, bundle):
        return {self.by_id[pk].codename for pk in bundle['permissions']}

    def test_all_explicit_and_config_bundles_are_complete(self):
        self.assertGreater(len(self.workflows), len(WORKFLOWS))
        for workflow in self.workflows.values():
            read = workflow['bundles'][0]
            self.assertTrue(all(code.startswith('can_view_') for code in self.codes(read)), workflow['id'])
            for bundle in workflow['bundles']:
                self.assertFalse(bundle['unavailable'], bundle)
                self.assertTrue(set(read['permissions']) <= set(bundle['permissions']))
                self.assertFalse(any(permission_help(self.by_id[pk])['internal'] for pk in bundle['permissions']))

    def test_console_view_includes_all_three_read_permissions_and_no_grants(self):
        self.assertEqual(self.codes(self.workflows['console']['bundles'][0]), {
            'can_view_admins', 'can_view_admin_ids', 'can_view_admin_groups',
        })

    def test_page_bundles_cover_actual_backend_endpoint_requirements(self):
        endpoints = {
            'console': ['get_admin_ids', 'get_admin_groups'],
            'players': ['get_players_history', 'get_bans', 'get_player_profile', 'get_player_comments', 'get_player_messages', 'get_logs', 'get_historical_logs'],
            'vips': ['get_vip_ids'],
            'blacklists': ['get_blacklists', 'get_blacklist_records'],
            'rotation': ['get_map_rotation', 'get_map_sequence', 'get_map_shuffle_enabled', 'get_maps'],
            'votemap': ['get_votemap_status', 'get_votemap_results', 'get_votemap_config', 'get_votemap_whitelist', 'get_maps'],
            'templates': ['get_message_templates', 'get_message_template_categories'],
            'broadcast': ['get_auto_broadcasts_config', 'get_campaign_delivery_status', 'get_vip_lifecycle_status', 'get_message_templates'],
        }
        for workflow, names in endpoints.items():
            codes = {'api.' + c for c in self.codes(self.workflows[workflow]['bundles'][0])}
            for name in names:
                with self.subTest(workflow=workflow, endpoint=name):
                    required = self.requirements[name]
                    self.assertTrue(({required} if isinstance(required, str) else set(required)) <= codes)

    def test_console_actions_and_broadcast_changes_add_only_explicit_actions(self):
        for workflow, index, endpoint in [('console', 1, 'add_admin'), ('console', 2, 'remove_admin'), ('broadcast', 1, 'set_auto_broadcasts_config')]:
            read = self.codes(self.workflows[workflow]['bundles'][0])
            action = self.codes(self.workflows[workflow]['bundles'][index])
            self.assertEqual({'api.' + code for code in action - read}, {self.requirements[endpoint]})

    def test_partial_permission_queryset_marks_unavailable_prerequisites(self):
        permission = next(p for p in self.permissions if p.codename == 'can_view_admins')
        console = next(w for w in permission_workflows([permission]) if w['id'] == 'console')
        self.assertEqual(console['bundles'][0]['permissions'], [str(permission.pk)])
        self.assertEqual(console['bundles'][0]['unavailable'], ['can_view_admin_groups', 'can_view_admin_ids'])

    def test_de_en_have_identical_grants(self):
        english = permission_workflows(self.permissions, german=False)
        for de, en in zip(self.workflows.values(), english):
            self.assertEqual(de['id'], en['id'])
            for left, right in zip(de['bundles'], en['bundles']):
                self.assertEqual(left['permissions'], right['permissions'])
                self.assertEqual(left['unavailable'], right['unavailable'])

    def test_wizard_covers_each_workflow_once_with_localized_explanations(self):
        for german in (True, False):
            workflows = permission_workflows(self.permissions, german)
            before = [(w['id'], w['bundles']) for w in workflows]
            sections = wizard_metadata(workflows, german)
            ids = [key for section in sections for key in section['workflows']]
            self.assertEqual(len(ids), len(set(ids)))
            self.assertEqual(set(ids), {w['id'] for w in workflows})
            self.assertTrue(all(w['explanation'] for w in workflows))
            self.assertEqual(before, [(w['id'], w['bundles']) for w in workflows])
            self.assertTrue(all(section['description'] for section in sections))

    def test_internal_metadata_separated_and_console_aliases_searchable(self):
        for p in self.permissions:
            meta = permission_help(p)
            if p.content_type.app_label == 'contenttypes':
                self.assertTrue(meta['internal'])
                self.assertIn('Wartung', meta['category'])
                self.assertEqual(meta['sensitive'], not p.codename.startswith('view_'))
            if p.codename == 'can_view_admin_ids':
                self.assertIn('Konsolen', meta['title'])
                self.assertIn('Kennungen', meta['aliases'])
                self.assertIn('Console', permission_help(p, False)['title'])

    def test_multiple_groups_can_complete_a_page_without_direct_grants(self):
        user = User.objects.create_user('combined-task')
        groups = [Group.objects.create(name='task-a'), Group.objects.create(name='task-b')]
        read = self.workflows['console']['bundles'][0]['permissions']
        groups[0].permissions.set(read[:1])
        groups[1].permissions.set(read[1:])
        user.groups.add(*groups)
        self.assertTrue(user.has_perms(['api.' + code for code in self.codes(self.workflows['console']['bundles'][0])]))
        self.assertEqual(user.user_permissions.count(), 0)
        self.assertFalse(user.has_perm('api.can_add_admin_roles'))

    @override_settings(ROOT_URLCONF='api.test_admin_theme')
    def test_render_and_exact_save_preserve_existing_internal_permissions(self):
        owner = User.objects.create_superuser('workflow-owner', password='test-only')
        self.client.force_login(owner)
        group = Group.objects.create(name='unchanged-workflow')
        internal = next(p for p in self.permissions if p.codename == 'view_contenttype')
        group.permissions.add(internal)
        url = reverse('admin:auth_group_change', args=[group.pk])
        response = self.client.get(url)
        self.assertContains(response, 'permission-planner.js')
        self.assertContains(response, 'permission-wizard.js')
        self.assertContains(response, '"wizardSections"')
        self.assertContains(response, '"workflows"')
        self.assertEqual(set(group.permissions.values_list('pk', flat=True)), {internal.pk})
        requested = [str(internal.pk), *self.workflows['console']['bundles'][0]['permissions']]
        response = self.client.post(url, {'name': group.name, 'permissions': requested, '_save': 'Save'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(set(map(str, group.permissions.values_list('pk', flat=True))), set(requested))
