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
