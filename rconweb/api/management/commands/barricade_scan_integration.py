"""Manage experimental bindings from a trusted administrative shell.

The actor argument is an audit attribution, not shell-user authentication.
Access to this command must be restricted to trusted host administrators.
"""
import json
from uuid import uuid4

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError

from api.barricade_scan_auth import current_credential_is_authorized
from rcon.barricade_scan_journal import set_integration_credential
from rcon.utils import get_server_number


class Command(BaseCommand):
    help = 'Register or rotate a Barricade scan binding (experimental; no scan is sent).'

    def add_arguments(self, parser):
        parser.add_argument('action', choices=('register', 'rotate'))
        parser.add_argument('--actor', required=True, help='Active superuser responsible for the change')
        parser.add_argument('--reason', required=True)
        parser.add_argument('--credential-id', required=True, type=int)
        parser.add_argument('--integration-id', help='Existing integration UUID for rotation')
        parser.add_argument('--expected-credential-id', type=int)
        parser.add_argument('--legacy-scanner-stopped', action='store_true',
                            help='Confirm every old scanner is stopped and cannot reconnect')

    def handle(self, *args, **options):
        try:
            actor = User.objects.get(username=options['actor'])
        except User.DoesNotExist as exc:
            raise CommandError('Active superuser required') from exc
        if not actor.is_active or not actor.is_superuser:
            raise CommandError('Active superuser required')
        if not current_credential_is_authorized(options['credential_id']):
            raise CommandError('The new key is missing or lacks Barricade permissions')
        if options['action'] == 'register':
            if not options['legacy_scanner_stopped']:
                raise CommandError('Stop all legacy scanners before registering the cutover')
            if options['integration_id'] is not None or options['expected_credential_id'] is not None:
                raise CommandError('Register creates a new integration UUID')
            integration_id, expected = str(uuid4()), None
        else:
            integration_id, expected = options['integration_id'], options['expected_credential_id']
            if not integration_id or expected is None:
                raise CommandError('Rotation requires the integration UUID and expected key ID')
        try:
            changed = set_integration_credential(int(get_server_number()), integration_id,
                expected_credential_id=expected, new_credential_id=options['credential_id'],
                actor=actor.username, reason=options['reason'])
        except ValueError as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(json.dumps({'integration_id': integration_id,
            'query_parameter': f'frontline_integration={integration_id}', 'changed': changed}))
