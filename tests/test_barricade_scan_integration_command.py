import json
import os
from io import StringIO
from types import SimpleNamespace
from unittest.mock import patch

import django
import pytest
from django.core.management.base import CommandError

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'rconweb.rconweb.test_settings')
django.setup()
from api.management.commands import barricade_scan_integration as command


def options(**overrides):
    return {'action': 'register', 'actor': 'operator', 'reason': 'synthetic setup',
            'credential_id': 4, 'integration_id': None, 'expected_credential_id': None,
            'legacy_scanner_stopped': True, 'dedicated_key_confirmed': True, **overrides}


def test_registration_uses_verified_key_and_emits_only_public_identifier():
    output = StringIO()
    instance = command.Command(stdout=output)
    user = SimpleNamespace(username='operator', is_active=True, is_superuser=True)
    with patch.object(command.User.objects, 'get', return_value=user), \
         patch.object(command, 'current_credential_is_authorized', return_value=True), \
         patch.object(command, 'get_server_number', return_value='3'), \
         patch.object(command, 'set_integration_credential', return_value=True) as change:
        instance.handle(**options())
    payload = json.loads(output.getvalue())
    assert payload['query_parameter'] == f"frontline_integration={payload['integration_id']}"
    assert payload['changed'] is True
    assert change.call_args.kwargs['new_credential_id'] == 4
    assert change.call_args.kwargs['expected_credential_id'] is None


def test_registration_refuses_non_superuser_and_unusable_key():
    instance = command.Command(stdout=StringIO())
    user = SimpleNamespace(username='operator', is_active=True, is_superuser=False)
    with patch.object(command.User.objects, 'get', return_value=user), \
         patch.object(command, 'set_integration_credential') as change:
        with pytest.raises(CommandError, match='superuser'):
            instance.handle(**options())
        change.assert_not_called()
    user.is_superuser = True
    with patch.object(command.User.objects, 'get', return_value=user), \
         patch.object(command, 'current_credential_is_authorized', return_value=False), \
         patch.object(command, 'set_integration_credential') as change:
        with pytest.raises(CommandError, match='missing or lacks'):
            instance.handle(**options())
        change.assert_not_called()


def test_rotation_requires_expected_previous_key():
    instance = command.Command(stdout=StringIO())
    user = SimpleNamespace(username='operator', is_active=True, is_superuser=True)
    with patch.object(command.User.objects, 'get', return_value=user), \
         patch.object(command, 'current_credential_is_authorized', return_value=True), \
         patch.object(command, 'set_integration_credential') as change:
        with pytest.raises(CommandError, match='expected key ID'):
            instance.handle(**options(action='rotate', integration_id='01234567-89ab-4def-8012-0123456789ab'))
        change.assert_not_called()
