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
from pathlib import Path
from types import SimpleNamespace
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


def public_method(path, blob, class_name, method_name):
    source_bytes = Path(path).read_bytes().replace(b'\r\n', b'\n')
    header = b'blob ' + str(len(source_bytes)).encode() + b'\0'
    assert hashlib.sha1(header + source_bytes).hexdigest() == blob
    tree = ast.parse(source_bytes.decode())
    public_class = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == class_name)
    method = next(node for node in public_class.body if isinstance(node, ast.FunctionDef) and node.name == method_name)
    module = ast.Module(body=[ast.ImportFrom(module='__future__', names=[ast.alias(name='annotations')], level=0),
        ast.ClassDef(name='PublicClass', bases=[], keywords=[], body=[method], decorator_list=[])], type_ignores=[])
    ast.fix_missing_locations(module)
    namespace = {'urlparse': urlparse, 'urlunparse': urlunparse}
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
