"""The optional protocol version never changes the Frontline release version."""
import json
import os
from types import SimpleNamespace
from unittest.mock import Mock, patch

import django
import pytest
from django.test import RequestFactory

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'rconweb.rconweb.test_settings')
django.setup()
from api import barricade_crcon_compat as compat, views
from tests.test_barricade_scan_journal_postgres import database, prepare_adapter
from rcon import barricade_scan_journal as journal
from rcon.barricade_scan_identity import integration_namespace

PEER = '01234567-89ab-4def-8012-0123456789ab'
QUERY = f'frontline_integration={PEER}'
FLAGS = ('HLL_BARRICADE_DURABLE_SCANS', 'HLL_BARRICADE_JOURNAL_OBSERVATIONS',
         'HLL_BARRICADE_CRCON_COMPAT')


@pytest.fixture
def bound_peer(monkeypatch):
    for flag in FLAGS:
        monkeypatch.setenv(flag, '1')
    user = SimpleNamespace(is_active=True, has_perms=Mock(return_value=True))
    key = SimpleNamespace(pk=23, user=user)
    query = Mock()
    query.filter.return_value.first.return_value = key
    monkeypatch.setattr(compat.DjangoAPIKey.objects, 'select_related', lambda *_: query)
    monkeypatch.setattr(compat, 'make_password', lambda *_args, **_kwargs: 'synthetic-hash')
    monkeypatch.setattr(compat, 'get_server_number', lambda: '3')
    resolve = Mock(return_value=f'integration:{PEER}')
    monkeypatch.setattr(compat, 'integration_namespace', resolve)
    return user, key, resolve


def request(query=QUERY, authorization='Bearer synthetic-key'):
    return RequestFactory().get(f'/api/get_version?{query}', HTTP_AUTHORIZATION=authorization)


def test_only_explicit_registered_credential_receives_compatibility_version(bound_peer):
    user, key, resolve = bound_peer
    response = views.get_version(request())
    body = json.loads(response.content)
    assert response.status_code == 200 and body['result'] == 'v12.3.0'
    assert body['version'] == views.TAG_VERSION
    assert body['version'] != body['result']
    user.has_perms.assert_called_with(compat.REQUIRED_PERMISSIONS)
    resolve.assert_called_once_with(QUERY.encode(), server_number=3, credential_id=key.pk)


@pytest.mark.parametrize('flag', FLAGS)
def test_compatibility_is_disabled_if_any_opt_in_is_missing(bound_peer, monkeypatch, flag):
    monkeypatch.delenv(flag)
    assert views.get_version(request()).status_code == 403


@pytest.mark.parametrize('query,authorization', [
    (QUERY, ''), (QUERY, 'Basic synthetic-key'), (QUERY, 'Bearer'),
    (QUERY + '&' + QUERY, 'Bearer synthetic-key'),
    ('frontline_integration=not-a-uuid', 'Bearer synthetic-key'),
])
def test_invalid_or_ambiguous_identity_never_receives_compatibility_version(bound_peer, query, authorization):
    assert views.get_version(request(query, authorization)).status_code == 403


def test_revoked_permission_or_binding_and_database_error_fail_closed(bound_peer):
    user, key, resolve = bound_peer
    user.has_perms.return_value = False
    assert not compat.authorized_peer(request())
    user.has_perms.return_value = True
    user.is_active = False
    assert not compat.authorized_peer(request())
    user.is_active = True
    resolve.return_value = None
    assert not compat.authorized_peer(request())
    resolve.side_effect = OSError('synthetic database failure')
    assert not compat.authorized_peer(request())


def test_normal_version_route_is_unaffected_without_compatibility_marker(monkeypatch):
    for flag in FLAGS:
        monkeypatch.setenv(flag, '1')
    with patch.object(compat, 'authorized_peer', side_effect=AssertionError('unexpected peer check')):
        response = views.get_version(RequestFactory().get('/api/get_version'))
    assert json.loads(response.content)['result'] == views.TAG_VERSION


def test_postgres_binding_and_key_rotation_gate_compatibility(database, monkeypatch, bound_peer):
    prepare_adapter(database, monkeypatch)
    _, key, _ = bound_peer
    key.pk = 1
    monkeypatch.setattr(compat, 'integration_namespace', integration_namespace)
    assert views.get_version(request()).status_code == 200
    monkeypatch.setattr(compat, 'get_server_number', lambda: '4')
    assert views.get_version(request()).status_code == 403
    monkeypatch.setattr(compat, 'get_server_number', lambda: '3')
    assert journal.set_integration_credential(3, PEER, expected_credential_id=1,
        new_credential_id=2, actor='test', reason='synthetic rotation')
    assert views.get_version(request()).status_code == 403
    key.pk = 2
    assert views.get_version(request()).status_code == 200


def test_actual_django_key_and_postgres_binding(database, monkeypatch):
    from django.core.management import call_command
    from django.contrib.auth.models import User
    from api.models import DjangoAPIKey

    call_command('migrate', verbosity=0, interactive=False)
    for flag in FLAGS:
        monkeypatch.setenv(flag, '1')
    monkeypatch.setattr(compat, 'get_server_number', lambda: '3')
    prepare_adapter(database, monkeypatch)
    user = User.objects.create_superuser('synthetic-peer', 'peer@example.invalid', 'unused')
    key = DjangoAPIKey.objects.create(user=user, api_key='synthetic-key')
    if key.pk != 1:
        journal.set_integration_credential(3, PEER, expected_credential_id=1,
            new_credential_id=key.pk, actor='test', reason='bind real test key')
    assert views.get_version(request()).status_code == 200
    assert views.get_version(request(authorization='Bearer wrong-key')).status_code == 403
    user.is_active = False
    user.save(update_fields=['is_active'])
    assert views.get_version(request()).status_code == 403
