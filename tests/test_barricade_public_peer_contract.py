"""Synthetic contract probe using pinned public Barricade handler source.

No Discord, game server, live credentials, or external network are used.
"""
import ast
import asyncio
from enum import Enum
import hashlib
import json
import logging
import os
import re
from contextlib import asynccontextmanager
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch
from urllib.parse import parse_qs, urlparse, urlunparse

import pytest
peer_path = os.environ.get('BARRICADE_PEER_SOURCE')
if not peer_path:
    pytest.skip('requires pinned public Barricade source', allow_module_level=True)
import django
django.setup()
from rcon.barricade import BarricadeRequestError, RequestBody, ResponseBody, ServerRequestType
from api.barricade import BarricadeConsumer

source = Path(peer_path).read_bytes().replace(b'\r\n', b'\n')
header = b'blob ' + str(len(source)).encode() + b'\0'
assert hashlib.sha1(header + source).hexdigest() == 'ebc1663ff64c09386b12ee46620dab39b648a77c'
module = ast.parse(source.decode())
klass = next(node for node in module.body if isinstance(node, ast.ClassDef) and node.name == 'CustomWebsocket')
methods = [node for node in klass.body if isinstance(node, ast.AsyncFunctionDef)
           and node.name in ('handle_request', 'scan_players')]
assert {node.name for node in methods} == {'handle_request', 'scan_players'}
selected = ast.Module(body=[ast.ImportFrom(module='__future__', names=[ast.alias(name='annotations')], level=0),
    ast.ClassDef(name='PublicPeer', bases=[], keywords=[], body=methods, decorator_list=[])], type_ignores=[])
ast.fix_missing_locations(selected)

class Game(str, Enum):
    HLL = 'HLL'
    HLLV = 'HLLV'

class WebsocketRequestException(Exception):
    pass

effects = []
mode = 'ok'
async def fake_alert(community_id, player_ids, game):
    effects.append((community_id, list(player_ids), game.value))
    if mode == 'failure_after_effect':
        raise RuntimeError('synthetic downstream error')

namespace = {'ServerRequestType': ServerRequestType, 'Game': Game,
             'WebsocketRequestException': WebsocketRequestException,
             'send_optional_player_alert_to_community': fake_alert}
exec(compile(selected, '<pinned-public-barricade>', 'exec'), namespace)
PublicPeer = namespace['PublicPeer']

async def main():
    global mode
    consumer = BarricadeConsumer()
    peer = PublicPeer()
    peer.integration = SimpleNamespace(config=SimpleNamespace(community_id=123))
    peer.logger = logging.getLogger('synthetic-peer')
    peer.logger.disabled = True
    responses = []
    class Socket:
        async def send(self, text):
            payload = json.loads(text)
            responses.append(payload)
            await consumer.handle_response(ResponseBody.model_validate(payload))
    async def connected(timeout):
        return Socket()
    peer.wait_until_connected = connected
    async def to_peer(payload):
        await peer.handle_request(RequestBody.model_validate(payload))
    consumer.send_json = to_peer
    payload = {'player_ids': ['synthetic-eos'], 'game': 'HLLV'}
    assert await consumer.send_request(ServerRequestType.SCAN_PLAYERS, payload) is None
    assert await consumer.send_request(ServerRequestType.SCAN_PLAYERS, payload) is None
    assert effects == [(123, ['synthetic-eos'], 'HLLV')] * 2
    assert all(response['failed'] is False for response in responses)
    mode = 'failure_after_effect'
    try:
        await consumer.send_request(ServerRequestType.SCAN_PLAYERS, payload)
    except BarricadeRequestError as exc:
        assert str(exc) == 'synthetic downstream error'
    else:
        raise AssertionError('Failure after side effect was not propagated')
    assert len(effects) == 3 and responses[-1]['failed'] is True
    peer.integration = None
    mode = 'ok'
    assert await consumer.send_request(ServerRequestType.SCAN_PLAYERS, payload) is None
    assert len(effects) == 3 and responses[-1]['failed'] is False
    print('Pinned public peer handler: HLLV payload accepted; repeat invoked alert callback twice;')
    print('failure after callback propagated; success can also occur without invoking callback.')

def test_frontline_consumer_against_pinned_public_barricade_handler():
    asyncio.run(main())


def public_method(path, blob, class_name, method_name, extra_globals=None):
    source_bytes = Path(path).read_bytes().replace(b'\r\n', b'\n')
    header = b'blob ' + str(len(source_bytes)).encode() + b'\0'
    assert hashlib.sha1(header + source_bytes).hexdigest() == blob
    tree = ast.parse(source_bytes.decode())
    public_class = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == class_name)
    method = next(node for node in public_class.body
                  if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == method_name)
    method.decorator_list = []
    module = ast.Module(body=[ast.ImportFrom(module='__future__', names=[ast.alias(name='annotations')], level=0),
        ast.ClassDef(name='PublicClass', bases=[], keywords=[], body=[method], decorator_list=[])], type_ignores=[])
    ast.fix_missing_locations(module)
    namespace = {'urlparse': urlparse, 'urlunparse': urlunparse}
    namespace.update(extra_globals or {})
    exec(compile(module, '<pinned-public-url>', 'exec'), namespace)
    return getattr(namespace['PublicClass'], method_name)


def test_public_peer_url_modes_preserve_custom_query_but_not_crcon_base_query():
    directory = os.environ.get('BARRICADE_PEER_URL_SOURCES')
    if not directory:
        pytest.skip('requires pinned public Barricade URL sources')
    root = Path(directory)
    custom = public_method(root / 'custom.py', '20a04c97250fa7fadaa17822e3b4e5768a1626ff',
                           'CustomIntegration', 'get_ws_url')
    crcon = public_method(root / 'crcon.py', '783e5fe6d52071d68b652e39a1fd8c91990d4b22',
                          'CRCONIntegration', 'get_ws_url')
    url = public_method(root / 'websocket.py', '8c672a2c59d6ccfc7e64611de88c7cee50263480',
                        'Websocket', 'get_url')
    ident = '01234567-89ab-4def-8012-0123456789ab'
    custom_address = f'https://example.invalid/ws/barricade?frontline_integration={ident}'
    custom_peer = SimpleNamespace(config=SimpleNamespace(api_url=custom_address))
    custom_url = url(SimpleNamespace(address=custom(custom_peer)))
    assert urlparse(custom_url).path == '/ws/barricade'
    assert parse_qs(urlparse(custom_url).query) == {'frontline_integration': [ident]}
    crcon_peer = SimpleNamespace(config=SimpleNamespace(api_url=f'https://example.invalid?frontline_integration={ident}'))
    crcon_url = url(SimpleNamespace(address=crcon(crcon_peer)))
    assert urlparse(crcon_url).path != '/ws/barricade'
    assert parse_qs(urlparse(crcon_url).query) != {'frontline_integration': [ident]}


def test_public_crcon_version_gate_and_unrecognized_ban_policy():
    directory = os.environ.get('BARRICADE_PEER_URL_SOURCES')
    if not directory:
        pytest.skip('requires pinned public Barricade URL sources')
    path = Path(directory) / 'crcon.py'
    blob = '783e5fe6d52071d68b652e39a1fd8c91990d4b22'

    class IntegrationValidationError(Exception):
        pass

    source_tree = ast.parse(path.read_text(encoding='utf-8'))
    assignment = next(node for node in source_tree.body if isinstance(node, ast.Assign)
                      and any(isinstance(target, ast.Name) and target.id == 'RE_VERSION' for target in node.targets))
    version_globals = {'re': re}
    exec(compile(ast.Module(body=[assignment], type_ignores=[]), '<pinned-version-pattern>', 'exec'), version_globals)
    validate = public_method(path, blob, 'CRCONIntegration', 'validate_crcon_version', {
        'RE_VERSION': version_globals['RE_VERSION'],
        'IntegrationValidationError': IntegrationValidationError,
    })

    async def version_check(version):
        peer = SimpleNamespace(_make_request=AsyncMock(return_value={'result': version}))
        return await validate(peer)

    with pytest.raises(IntegrationValidationError, match='v10 or above'):
        asyncio.run(version_check('v0.9.12'))
    assert asyncio.run(version_check('v12.3.0')) is None

    @asynccontextmanager
    async def fake_session():
        yield SimpleNamespace()

    async def no_local_bans(*_args, **_kwargs):
        if False:
            yield None

    async def community(*_args, **_kwargs):
        return SimpleNamespace()

    sent = []
    async def expire(record_id):
        sent.append(record_id)

    async def remote_bans(_game):
        return {'9': {'id': 9, 'is_active': True}}

    peer = SimpleNamespace(config=SimpleNamespace(id=1, community_id=2, api_url='https://example.invalid'),
                           get_blacklist_bans=remote_bans, expire_ban=expire,
                           logger=logging.getLogger('synthetic-crcon'))
    synchronize = public_method(path, blob, 'CRCONIntegration', 'synchronize', {
        'session_factory': SimpleNamespace(begin=fake_session), 'get_community_by_id': community,
        'schemas': SimpleNamespace(CommunityRef=SimpleNamespace(model_validate=lambda value: value)),
        'Game': (Game.HLLV,), 'get_bans_by_integration': no_local_bans,
        'get_danger_embed': lambda *_args, **_kwargs: None,
        'safe_send_to_community': lambda *_args, **_kwargs: None,
    })
    asyncio.run(synchronize(peer))
    assert sent == [9]


def test_public_crcon_create_list_payload_matches_frontline_default():
    directory = os.environ.get('BARRICADE_PEER_URL_SOURCES')
    if not directory:
        pytest.skip('requires pinned public Barricade URL sources')
    from rcon.blacklist import BlacklistSyncMethod
    from tests.test_blacklist_sync_api_postgres import invoke

    create = public_method(Path(directory) / 'crcon.py',
        '783e5fe6d52071d68b652e39a1fd8c91990d4b22', 'CRCONIntegration', 'create_remote_ban_list')
    observed = []
    async def request(method, endpoint, data):
        observed.append((method, endpoint, data))
        response = invoke('create_blacklist', 'POST', {'api.can_create_blacklists'}, data)
        assert response.status_code == 200
        return json.loads(response.content)
    peer = SimpleNamespace(logger=Mock(), _make_request=request)
    with patch('rcon.blacklist.create_blacklist', return_value={'id': 17}) as create_list:
        result = asyncio.run(create(peer, SimpleNamespace(name='Synthetic', id=9), Game.HLLV))
    assert result == '17'
    assert observed[0][2]['sync_method'] == 'kick_only'
    assert create_list.call_args.kwargs['sync'] == BlacklistSyncMethod.KICK_ONLY


def test_public_crcon_profile_lookup_never_returns_vietnam_eos():
    directory = os.environ.get('BARRICADE_PEER_URL_SOURCES')
    if not directory:
        pytest.skip('requires pinned public Barricade URL sources')
    method = public_method(Path(directory) / 'crcon.py',
        '783e5fe6d52071d68b652e39a1fd8c91990d4b22',
        'CRCONIntegration', 'get_player_eos_ids')
    request = AsyncMock(return_value={'result': {'soldier': {'eos_id': 'synthetic-eos'}}})
    peer = SimpleNamespace(_make_request=request, logger=Mock())
    assert asyncio.run(method(peer, 123)) == ('synthetic-eos', None)
    request.assert_awaited_once_with('GET', '/get_player_profile', data={'player_id': 123})


def test_public_crcon_missing_remote_record_deletes_local_reference():
    directory = os.environ.get('BARRICADE_PEER_URL_SOURCES')
    if not directory:
        pytest.skip('requires pinned public Barricade URL sources')
    @asynccontextmanager
    async def fake_session():
        yield db
    db = SimpleNamespace(delete=AsyncMock())
    ban = SimpleNamespace(remote_id='9')
    async def local_bans(*_args, **_kwargs):
        yield ban
    async def community(*_args, **_kwargs):
        return SimpleNamespace()
    peer = SimpleNamespace(config=SimpleNamespace(id=1, community_id=2),
        get_blacklist_bans=AsyncMock(return_value={}), expire_ban=AsyncMock(),
        logger=logging.getLogger('synthetic-crcon'))
    synchronize = public_method(Path(directory) / 'crcon.py',
        '783e5fe6d52071d68b652e39a1fd8c91990d4b22', 'CRCONIntegration', 'synchronize', {
            'session_factory': SimpleNamespace(begin=fake_session), 'get_community_by_id': community,
            'schemas': SimpleNamespace(CommunityRef=SimpleNamespace(model_validate=lambda value: value)),
            'Game': (Game.HLLV,), 'get_bans_by_integration': local_bans,
        })
    asyncio.run(synchronize(peer))
    db.delete.assert_awaited_once_with(ban)
    peer.expire_ban.assert_not_awaited()


@pytest.mark.parametrize('delete_between_pages', [False, True])
def test_public_crcon_pagination_can_hide_existing_record_after_deletion(delete_between_pages):
    directory = os.environ.get('BARRICADE_PEER_URL_SOURCES')
    if not directory:
        pytest.skip('requires pinned public Barricade URL sources')
    crcon = Path(directory) / 'crcon.py'
    blob = '783e5fe6d52071d68b652e39a1fd8c91990d4b22'
    get_bans = public_method(crcon, blob, 'CRCONIntegration', 'get_blacklist_bans', {
        'game_switch': lambda game, hll, hllv: hllv if game == Game.HLLV else hll,
    })
    records = [{'id': i, 'is_active': True} for i in range(101, 0, -1)]
    async def request(method, endpoint, data):
        assert method == 'GET' and endpoint == '/get_blacklist_records'
        if data['page'] == 2 and delete_between_pages:
            records.pop(0)  # unrelated earlier record removed between requests
        size, page = data['page_size'], data['page']
        return {'result': {'records': records[(page - 1) * size:page * size], 'total': len(records)}}
    peer = SimpleNamespace(config=SimpleNamespace(hll_banlist_id='classic', hllv_banlist_id='vietnam'),
                           _make_request=request)
    observed = asyncio.run(get_bans(peer, Game.HLLV))
    assert any(record['id'] == 1 for record in records)
    assert ('1' not in observed) is delete_between_pages

    @asynccontextmanager
    async def fake_session():
        yield db
    db = SimpleNamespace(delete=AsyncMock())
    reference = SimpleNamespace(remote_id='1')
    observed_ids = tuple(observed)
    async def local_bans(*_args, **_kwargs):
        yield reference
        for record_id in observed_ids:
            if record_id != reference.remote_id:
                yield SimpleNamespace(remote_id=record_id)
    async def community(*_args, **_kwargs):
        return SimpleNamespace()
    sync_peer = SimpleNamespace(config=SimpleNamespace(id=1, community_id=2),
        get_blacklist_bans=AsyncMock(return_value=observed),
        expire_ban=AsyncMock(), logger=logging.getLogger('synthetic-crcon'))
    synchronize = public_method(crcon, blob, 'CRCONIntegration', 'synchronize', {
        'session_factory': SimpleNamespace(begin=fake_session), 'get_community_by_id': community,
        'schemas': SimpleNamespace(CommunityRef=SimpleNamespace(model_validate=lambda value: value)),
        'Game': (Game.HLLV,), 'get_bans_by_integration': local_bans,
    })
    asyncio.run(synchronize(sync_peer))
    if delete_between_pages:
        db.delete.assert_awaited_once_with(reference)
    else:
        db.delete.assert_not_awaited()


def test_public_forwarding_uses_vietnam_game_id_as_eos():
    path = os.environ.get('BARRICADE_PEER_FORWARDING_SOURCE')
    if not path:
        pytest.skip('requires pinned public Barricade forwarding source')
    source_bytes = Path(path).read_bytes().replace(b'\r\n', b'\n')
    header = b'blob ' + str(len(source_bytes)).encode() + b'\0'
    assert hashlib.sha1(header + source_bytes).hexdigest() == 'f08718099b4fae1dfbdf9af9c274586c49137f22'
    tree = ast.parse(source_bytes.decode())
    function = next(node for node in tree.body
                    if isinstance(node, ast.FunctionDef) and node.name == 'is_eos_id_necessary')
    module = ast.Module(body=[ast.ImportFrom(module='__future__', names=[ast.alias(name='annotations')], level=0),
                              function], type_ignores=[])
    ast.fix_missing_locations(module)
    env = {'Game': Game, 'might_forward_to_staff': lambda _: True,
           'get_player_id_type': lambda value: 'steam' if value == 'synthetic-steam-id' else 'other',
           'PlayerIDType': SimpleNamespace(STEAM_64_ID='steam')}
    exec(compile(module, '<pinned-forwarding>', 'exec'), env)
    check = env['is_eos_id_necessary']
    assert check(SimpleNamespace(game=Game.HLLV), 'synthetic-vietnam-eos') is False
    assert check(SimpleNamespace(game=Game.HLL), 'synthetic-steam-id') is False
    assert check(SimpleNamespace(game=Game.HLL), 'synthetic-console-id') is True
