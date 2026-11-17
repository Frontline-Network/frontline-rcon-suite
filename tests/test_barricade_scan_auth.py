import os
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import django
import pytest

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'rconweb.rconweb.test_settings')
django.setup()
from api import barricade_scan_auth as auth
from api import auth as websocket_auth


def test_current_permissions_are_loaded_for_each_check():
    user = SimpleNamespace(is_active=True, has_perms=Mock(side_effect=[True, False]))
    query = Mock()
    query.get.return_value = SimpleNamespace(user=user)
    with patch.object(auth.DjangoAPIKey.objects, 'select_related', return_value=query):
        assert auth.current_credential_is_authorized(1)
        assert not auth.current_credential_is_authorized(1)
    assert query.get.call_count == 2
    user.has_perms.assert_called_with(auth.BARRICADE_PERMISSIONS)


def test_deleted_key_and_inactive_user_are_rejected():
    query = Mock()
    with patch.object(auth.DjangoAPIKey.objects, 'select_related', return_value=query):
        query.get.side_effect = auth.DjangoAPIKey.DoesNotExist
        assert not auth.current_credential_is_authorized(1)
        query.get.side_effect = None
        user = SimpleNamespace(is_active=False, has_perms=Mock())
        query.get.return_value = SimpleNamespace(user=user)
        assert not auth.current_credential_is_authorized(1)
        user.has_perms.assert_not_called()
        query.get.side_effect = OSError('synthetic auth database outage')
        with pytest.raises(OSError):
            auth.current_credential_is_authorized(1)


@pytest.mark.parametrize('credential_id', [None, 0, -1, True, '1'])
def test_invalid_credential_id_is_rejected(credential_id):
    assert not auth.current_credential_is_authorized(credential_id)


def test_key_id_lookup_is_scoped_to_authenticated_user():
    query = Mock()
    query.values_list.return_value.first.return_value = 42
    with patch.object(websocket_auth, 'make_password', return_value='synthetic-hash') as hash_key, \
         patch.object(websocket_auth.DjangoAPIKey.objects, 'filter', return_value=query) as lookup:
        assert websocket_auth.get_barricade_api_key_id.func('synthetic-key', 7) == 42
        lookup.assert_called_once_with(api_key='synthetic-hash', user_id=7)
        hash_key.assert_called_once()


def test_missing_explicit_peer_or_key_never_gets_a_durable_namespace():
    assert websocket_auth.get_barricade_scan_namespace.func(b'', 42) is None
    assert websocket_auth.get_barricade_scan_namespace.func(
        b'frontline_integration=01234567-89ab-4def-8012-0123456789ab', None) is None


@pytest.mark.parametrize('mobile,expected', [(False, 42), (True, None)])
def test_websocket_only_exposes_key_id_for_authenticated_legacy_key(mobile, expected):
    async def run():
        captured = {}
        async def downstream(scope, _receive, _send):
            captured.update(scope)
        app = websocket_auth.APITokenAuthMiddleware(downstream, perms=('synthetic',))
        scope = {'type': 'websocket', 'path': '/ws/barricade',
                 'headers': [(b'authorization', b'Bearer synthetic-key')], 'query_string': b'synthetic=query'}
        with patch.object(websocket_auth, 'get_user', AsyncMock(return_value=(SimpleNamespace(pk=7), object() if mobile else None))), \
             patch.object(websocket_auth, 'has_perms', AsyncMock(return_value=True)), \
             patch.object(websocket_auth, 'get_barricade_api_key_id', AsyncMock(return_value=42)) as lookup, \
             patch.object(websocket_auth, 'get_barricade_scan_namespace', AsyncMock(return_value='registered-peer' if not mobile else None)) as resolve:
            await app(scope, None, None)
        assert captured['barricade_credential_id'] == expected
        assert captured['barricade_scan_namespace'] == ('registered-peer' if not mobile else None)
        assert lookup.await_count == (0 if mobile else 1)
        resolve.assert_awaited_once_with(b'synthetic=query', expected)
    asyncio.run(run())
