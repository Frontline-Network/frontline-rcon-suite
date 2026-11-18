"""Read-only contract probe against pinned public Barricade query source.

This models only the query's fields in a disposable PostgreSQL schema; no
Barricade credentials, production rows, game server or sanctions are involved.
"""
import ast
import asyncio
import hashlib
import importlib.util
import itertools
import logging
import os
from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, create_engine, exists, not_, select, text
from sqlalchemy.orm import declarative_base, relationship, selectinload, sessionmaker


@pytest.fixture
def peer_query():
    path = os.getenv('BARRICADE_PUBLIC_RESPONSES')
    if not path:
        pytest.skip('requires pinned public Barricade responses.py')
    data = Path(path).read_bytes().replace(b'\r\n', b'\n')
    expected = ('efe7e600f4ac16232cc35145d96d45b794cf7bdc' if os.getenv('BARRICADE_EXPECT_FIXED')
                else 'c0f2c324fe9452a7d1c3120963b72d72cc9e95be')
    assert hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest() == expected
    tree = ast.parse(data.decode())
    function = next(n for n in tree.body if isinstance(n, ast.AsyncFunctionDef) and n.name == 'get_successful_responses_without_bans')
    function.decorator_list = []
    base = declarative_base()

    class Token(base):
        __tablename__ = 'token'
        id = Column(Integer, primary_key=True)

    class Report(base):
        __tablename__ = 'report'
        id = Column(Integer, primary_key=True)
        game = Column(String, nullable=False)
        token_id = Column(Integer, ForeignKey('token.id'))
        token = relationship(Token)

    class PlayerReport(base):
        __tablename__ = 'player_report'
        id = Column(Integer, primary_key=True)
        player_id = Column(Integer, nullable=False)
        report_id = Column(Integer, ForeignKey('report.id'))
        report = relationship(Report)

    class PlayerReportResponse(base):
        __tablename__ = 'response'
        id = Column(Integer, primary_key=True)
        community_id = Column(Integer, nullable=False)
        banned = Column(Boolean, nullable=False)
        player_report_id = Column(Integer, ForeignKey('player_report.id'))
        player_report = relationship(PlayerReport)

    class PlayerBan(base):
        __tablename__ = 'ban'
        id = Column(Integer, primary_key=True)
        integration_id = Column(Integer, nullable=False)
        player_id = Column(Integer, nullable=False)
        game = Column(String, nullable=False)

    module = ast.Module(body=[ast.ImportFrom(module='__future__', names=[ast.alias(name='annotations')], level=0), function], type_ignores=[])
    ast.fix_missing_locations(module)
    ns = {'models': SimpleNamespace(PlayerReportResponse=PlayerReportResponse, PlayerReport=PlayerReport,
                                     PlayerBan=PlayerBan, Report=Report),
          'select': select, 'exists': exists, 'not_': not_, 'selectinload': selectinload}
    exec(compile(module, '<pinned-barricade-query>', 'exec'), ns)
    return base, ns['get_successful_responses_without_bans'], Token, Report, PlayerReport, PlayerReportResponse, PlayerBan


@pytest.fixture
def database():
    dsn = os.getenv('TEST_POSTGRES_DSN')
    if not dsn:
        pytest.skip('requires disposable PostgreSQL')
    admin = create_engine(dsn)
    schema = 'barricade_404_' + uuid4().hex
    with admin.begin() as conn:
        conn.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine = create_engine(dsn, connect_args={'options': f'-csearch_path={schema}'})
    try:
        yield engine
    finally:
        engine.dispose()
        with admin.begin() as conn:
            conn.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin.dispose()


@pytest.mark.parametrize('existing_hll_ref', [False, True])
def test_repopulate_query_can_omit_vietnam_for_same_person(peer_query, database, existing_hll_ref):
    base, query, Token, Report, PlayerReport, Response, Ban = peer_query
    base.metadata.create_all(database)
    with sessionmaker(bind=database)() as session:
        token = Token(id=1)
        session.add_all([token, Report(id=1, game='HLL', token=token), Report(id=2, game='HLLV', token=token)])
        session.add_all([PlayerReport(id=1, player_id=5, report_id=1), PlayerReport(id=2, player_id=5, report_id=2)])
        session.add_all([Response(id=1, community_id=10, banned=True, player_report_id=1),
                         Response(id=2, community_id=10, banned=True, player_report_id=2)])
        if existing_hll_ref:
            session.add(Ban(integration_id=20, player_id=5, game='HLL'))
        session.commit()

        class DB:
            async def scalars(self, stmt):
                return session.scalars(stmt)

        results = asyncio.run(query(DB(), community_id=10, integration_id=20, game='HLLV' if existing_hll_ref else None))
        # The actual peer query loses one of two games, or excludes HLLV
        # altogether when the other game's integration reference exists.
        if os.getenv('BARRICADE_EXPECT_FIXED'):
            assert len(results) == (1 if existing_hll_ref else 2)
        else:
            assert len(results) == (0 if existing_hll_ref else 1)


@pytest.mark.parametrize('mode', ['missing_id', 'later_failure'])
def test_public_repopulate_reports_partial_failures_correctly(mode):
    root = os.getenv('BARRICADE_PUBLIC_SOURCE_DIR')
    if not root:
        pytest.skip('requires pinned public Barricade integration sources')

    def method(filename, blob, cls, name):
        data = (Path(root) / filename).read_bytes().replace(b'\r\n', b'\n')
        assert hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest() == blob
        tree = ast.parse(data.decode())
        klass = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == cls)
        function = next(n for n in klass.body if isinstance(n, ast.AsyncFunctionDef) and n.name == name)
        function.decorator_list = []
        return function

    repopulate = method('integration.py', 'c4835fdf067ddaeedfa6994d3ec3de58bdda35f3', 'Integration', 'repopulate')
    bulk = method('custom.py', 'ba6336d449f4b72f3459aff64d6a4b49207fd284' if os.getenv('BARRICADE_EXPECT_FIXED') else '20a04c97250fa7fadaa17822e3b4e5768a1626ff', 'CustomIntegration', 'bulk_ban_players')
    module = ast.Module(body=[ast.ImportFrom(module='__future__', names=[ast.alias(name='annotations')], level=0),
                              repopulate, bulk], type_ignores=[])
    ast.fix_missing_locations(module)

    def response(pid, game_id):
        player = SimpleNamespace(id=pid, get_game_id=lambda game: game_id)
        return SimpleNamespace(player_report=SimpleNamespace(player_id=pid, player=player,
                                                            report=SimpleNamespace(game='HLLV')))
    responses = [response(1, 'synthetic-eos'), response(2, None if mode == 'missing_id' else 'other-eos')]
    exits = []

    class Factory:
        def __call__(self):
            return self
        def begin(self):
            return self
        async def __aenter__(self):
            return object()
        async def __aexit__(self, *args):
            exits.append(args[0])

    async def query(*args, **kwargs):
        return responses

    class BulkError(Exception):
        def __init__(self, player_ids, *args):
            self.player_ids = player_ids
            super().__init__(*args)

    namespace = {'session_factory': Factory(), 'get_successful_responses_without_bans': query,
                 'schemas': SimpleNamespace(ResponseWithToken=SimpleNamespace(model_validate=lambda x: x)),
                 'itertools': itertools, 'batched': itertools.batched,
                 'IntegrationBulkBanError': BulkError}
    exec(compile(module, '<pinned-barricade-repopulate>', 'exec'), namespace)
    created = []

    class Peer:
        config = SimpleNamespace(id=20, community_id=10)
        logger = logging.getLogger('synthetic-barricade')
        async def get_ban(self, *args, **kwargs):
            return None
        def get_ban_reason(self, response):
            return 'synthetic'
        async def add_multiple_bans(self, mapping, game):
            for index, game_id in enumerate(mapping):
                if mode == 'later_failure' and index == 1:
                    raise BulkError([2], 'synthetic later failure')
                yield game_id, 'synthetic-record'
        async def set_multiple_ban_ids(self, db, *items):
            created.extend(items)
        bulk_ban_players = namespace['bulk_ban_players']

    expected = (1, 2) if os.getenv('BARRICADE_EXPECT_FIXED') or mode == 'later_failure' else (2, 2)
    assert asyncio.run(namespace['repopulate'](Peer())) == expected
    assert created == [(1, 'synthetic-record', 'HLLV')]
    if mode == 'later_failure':
        assert (exits[-1] is None) == bool(os.getenv('BARRICADE_EXPECT_FIXED'))


def test_public_sync_can_delete_reference_created_after_a_complete_snapshot():
    root = os.getenv('BARRICADE_PUBLIC_SOURCE_DIR')
    if not root:
        pytest.skip('requires pinned public Barricade integration sources')
    data = (Path(root) / 'crcon.py').read_bytes().replace(b'\r\n', b'\n')
    expected = ('62db75a2d4f2bc517d0b75bbc1058c06f41aede7' if os.getenv('BARRICADE_EXPECT_FIXED')
                else '783e5fe6d52071d68b652e39a1fd8c91990d4b22')
    assert hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest() == expected
    tree = ast.parse(data.decode())
    klass = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'CRCONIntegration')
    function = next(n for n in klass.body if isinstance(n, ast.AsyncFunctionDef) and n.name == 'synchronize')
    function.decorator_list = []
    module = ast.Module(body=[ast.ImportFrom(module='__future__', names=[ast.alias(name='annotations')], level=0), function], type_ignores=[])
    ast.fix_missing_locations(module)
    db = SimpleNamespace(delete=AsyncMock())
    reference = SimpleNamespace(remote_id='new-ban')
    peer_references = []

    class Factory:
        def begin(self):
            return self
        async def __aenter__(self):
            return db
        async def __aexit__(self, *args):
            pass

    async def community(*args):
        return object()

    async def local_bans(*args, **kwargs):
        for item in peer_references:
            yield item

    async def snapshot(game):
        # This is a complete, consistent snapshot taken before a new ban.
        # Another peer request then persists that ban's reference before the
        # synchronization queries its local references.
        peer_references.append(reference)
        return {}

    ns = {'session_factory': Factory(), 'get_community_by_id': community,
          'schemas': SimpleNamespace(CommunityRef=SimpleNamespace(model_validate=lambda x: x)),
          'Game': ('HLLV',), 'get_bans_by_integration': local_bans}
    exec(compile(module, '<pinned-barricade-sync>', 'exec'), ns)
    peer = SimpleNamespace(config=SimpleNamespace(id=20, community_id=10),
                           get_blacklist_bans=snapshot, logger=logging.getLogger('synthetic-barricade'))
    asyncio.run(ns['synchronize'](peer))
    if os.getenv('BARRICADE_EXPECT_FIXED'):
        db.delete.assert_not_awaited()
    else:
        db.delete.assert_awaited_once_with(reference)


def test_sync_preserves_references_when_offset_pages_shift():
    root = os.getenv('BARRICADE_PUBLIC_SOURCE_DIR')
    if not root:
        pytest.skip('requires pinned public Barricade integration sources')
    data = (Path(root) / 'crcon.py').read_bytes().replace(b'\r\n', b'\n')
    expected = ('62db75a2d4f2bc517d0b75bbc1058c06f41aede7' if os.getenv('BARRICADE_EXPECT_FIXED')
                else '783e5fe6d52071d68b652e39a1fd8c91990d4b22')
    assert hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest() == expected
    tree = ast.parse(data.decode())
    klass = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'CRCONIntegration')
    methods = [n for n in klass.body if isinstance(n, ast.AsyncFunctionDef) and n.name in ('synchronize', 'get_blacklist_bans')]
    assert len(methods) == 2
    for method in methods:
        method.decorator_list = []
    module = ast.Module(body=[ast.ImportFrom(module='__future__', names=[ast.alias(name='annotations')], level=0), *methods], type_ignores=[])
    ast.fix_missing_locations(module)
    db = SimpleNamespace(delete=AsyncMock())
    records = [{'id': i, 'is_active': True} for i in range(101, 0, -1)]
    references = [SimpleNamespace(remote_id=str(i)) for i in range(101, 0, -1)]

    class Factory:
        def begin(self):
            return self
        async def __aenter__(self):
            return db
        async def __aexit__(self, *args):
            pass

    async def community(*args):
        return object()
    async def local_bans(*args, **kwargs):
        for reference in references:
            yield reference
    async def request(method, endpoint, data):
        if data['page'] == 2:
            records.pop(0)
        start = (data['page'] - 1) * data['page_size']
        return {'result': {'records': records[start:start + data['page_size']], 'total': len(records)}}

    ns = {'session_factory': Factory(), 'get_community_by_id': community,
          'schemas': SimpleNamespace(CommunityRef=SimpleNamespace(model_validate=lambda x: x)),
          'Game': ('HLLV',), 'get_bans_by_integration': local_bans,
          'game_switch': lambda game, h, v: v}
    exec(compile(module, '<peer-pagination-sync>', 'exec'), ns)
    peer = SimpleNamespace(config=SimpleNamespace(id=20, community_id=10, hll_banlist_id='hll', hllv_banlist_id='hllv'),
                           _make_request=request, logger=logging.getLogger('synthetic-barricade'))
    peer.get_blacklist_bans = lambda game: ns['get_blacklist_bans'](peer, game)
    asyncio.run(ns['synchronize'](peer))
    assert any(r['id'] == 1 for r in records)
    omitted = references[-1]
    if os.getenv('BARRICADE_EXPECT_FIXED'):
        db.delete.assert_not_awaited()
    else:
        assert omitted in [call.args[0] for call in db.delete.await_args_list]


def test_sync_does_not_expire_unrecognized_remote_ban():
    root = os.getenv('BARRICADE_PUBLIC_SOURCE_DIR')
    if not root:
        pytest.skip('requires pinned public Barricade integration sources')
    data = (Path(root) / 'crcon.py').read_bytes().replace(b'\r\n', b'\n')
    expected = ('62db75a2d4f2bc517d0b75bbc1058c06f41aede7' if os.getenv('BARRICADE_EXPECT_FIXED')
                else '783e5fe6d52071d68b652e39a1fd8c91990d4b22')
    assert hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest() == expected
    tree = ast.parse(data.decode())
    klass = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'CRCONIntegration')
    method = next(n for n in klass.body if isinstance(n, ast.AsyncFunctionDef) and n.name == 'synchronize')
    method.decorator_list = []
    module = ast.Module(body=[ast.ImportFrom(module='__future__', names=[ast.alias(name='annotations')], level=0), method], type_ignores=[])
    ast.fix_missing_locations(module)
    class Factory:
        def begin(self):
            return self
        async def __aenter__(self):
            return SimpleNamespace(delete=AsyncMock())
        async def __aexit__(self, *args):
            pass
    async def local_bans(*args, **kwargs):
        if False:
            yield None
    async def community(*args):
        return object()
    async def remote(*args):
        return {'new': {'id': 99, 'is_active': True}}
    ns = {'session_factory': Factory(), 'get_community_by_id': community,
          'schemas': SimpleNamespace(CommunityRef=SimpleNamespace(model_validate=lambda x: x)),
          'Game': ('HLLV',), 'get_bans_by_integration': local_bans,
          'get_danger_embed': lambda *args: None, 'safe_send_to_community': lambda *args, **kwargs: None}
    exec(compile(module, '<peer-unrecognized-sync>', 'exec'), ns)
    peer = SimpleNamespace(config=SimpleNamespace(id=20, community_id=10, api_url='https://example.invalid/api'),
                           get_blacklist_bans=remote, expire_ban=AsyncMock(), logger=logging.getLogger('synthetic-barricade'))
    asyncio.run(ns['synchronize'](peer))
    if os.getenv('BARRICADE_EXPECT_FIXED'):
        peer.expire_ban.assert_not_awaited()
    else:
        peer.expire_ban.assert_awaited_once_with(99)


def test_patch_serializes_cross_instance_peer_sync_and_ban(monkeypatch):
    root, dsn = os.getenv('BARRICADE_PUBLIC_SOURCE_DIR'), os.getenv('TEST_POSTGRES_DSN')
    if not root or not dsn or not os.getenv('BARRICADE_EXPECT_FIXED'):
        pytest.skip('requires patched peer sources and isolated PostgreSQL')
    # Load the actual patch with a synthetic configuration; PostgreSQL is real.
    monkeypatch.setitem(sys.modules, 'barricade.constants', SimpleNamespace(
        DB_URL=dsn.replace('postgresql://', 'postgresql+asyncpg://')))
    spec = importlib.util.spec_from_file_location('peer_serialization_test', Path(root) / 'serialization.py')
    serialization = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(serialization)

    async def exercise():
        snapshot_open, release_scan, writer_entered = asyncio.Event(), asyncio.Event(), asyncio.Event()
        config = SimpleNamespace(id=20, community_id=10)
        # Separate instances deliberately defeat the process-local lock, so
        # only the PostgreSQL advisory lock can serialize these operations.
        scanner = SimpleNamespace(config=config, lock=asyncio.Lock())
        writer = SimpleNamespace(config=config, lock=asyncio.Lock())
        other = SimpleNamespace(config=SimpleNamespace(id=21), lock=asyncio.Lock())

        peer_references = []
        db = SimpleNamespace(delete=AsyncMock())

        class Factory:
            def begin(self):
                return self
            async def __aenter__(self):
                return db
            async def __aexit__(self, *args):
                pass

        async def snapshot(game):
            snapshot_open.set()
            await release_scan.wait()
            assert not writer_entered.is_set()
            return {}

        async def local_bans(*args, **kwargs):
            for item in peer_references:
                yield item

        async def community(*args):
            return object()

        source = (Path(root) / 'crcon.py').read_text()
        tree = ast.parse(source)
        klass = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'CRCONIntegration')
        method = next(n for n in klass.body if isinstance(n, ast.AsyncFunctionDef) and n.name == 'synchronize')
        assert any(isinstance(d, ast.Name) and d.id == 'serialized_integration' for d in method.decorator_list)
        method.decorator_list = []
        extracted = ast.Module(body=[ast.ImportFrom(module='__future__', names=[ast.alias(name='annotations')], level=0), method], type_ignores=[])
        ast.fix_missing_locations(extracted)
        ns = {'session_factory': Factory(), 'get_community_by_id': community,
              'schemas': SimpleNamespace(CommunityRef=SimpleNamespace(model_validate=lambda x: x)),
              'Game': ('HLLV',), 'get_bans_by_integration': local_bans}
        exec(compile(extracted, '<patched-barricade-sync>', 'exec'), ns)
        scan = serialization.serialized_integration(ns['synchronize'])
        scanner.get_blacklist_bans = snapshot
        scanner.logger = logging.getLogger('synthetic-barricade')

        @serialization.serialized_integration
        async def write(integration):
            peer_references.append(SimpleNamespace(remote_id='new-ban'))
            writer_entered.set()

        @serialization.serialized_integration
        async def independent(integration):
            return True

        first = asyncio.create_task(scan(scanner))
        await asyncio.wait_for(snapshot_open.wait(), 3)
        second = asyncio.create_task(write(writer))
        try:
            await asyncio.sleep(.2)
            assert not writer_entered.is_set()
            assert await asyncio.wait_for(independent(other), 3)
        finally:
            release_scan.set()
        await asyncio.wait_for(asyncio.gather(first, second), 3)
        assert writer_entered.is_set()
        db.delete.assert_not_awaited()
        await serialization.lock_engine.dispose()

    asyncio.run(exercise())


def test_patch_does_not_delete_references_when_existing_list_is_missing():
    root = os.getenv('BARRICADE_PUBLIC_SOURCE_DIR')
    if not root or not os.getenv('BARRICADE_EXPECT_FIXED'):
        pytest.skip('requires patched peer sources')
    tree = ast.parse((Path(root) / 'mixins.py').read_text())
    klass = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'IntegrationBanListMixin')
    method = next(n for n in klass.body if isinstance(n, ast.AsyncFunctionDef) and n.name == 'create_ban_list')
    assert any(isinstance(d, ast.Name) and d.id == 'serialized_integration' for d in method.decorator_list)
    method.decorator_list = []
    extracted = ast.Module(body=[ast.ImportFrom(module='__future__', names=[ast.alias(name='annotations')], level=0), method], type_ignores=[])
    ast.fix_missing_locations(extracted)
    class ValidationError(Exception):
        pass
    game = SimpleNamespace(HLL='HLL', HLLV='HLLV')
    ns = {'IntegrationValidationError': ValidationError, 'game_switch': lambda g, h, v: h if g == 'HLL' else v, 'Game': game}
    exec(compile(extracted, '<patched-create-ban-list>', 'exec'), ns)
    peer = SimpleNamespace(config=SimpleNamespace(id=20, hll_banlist_id='old-list', hllv_banlist_id=None),
                           logger=logging.getLogger('synthetic-barricade'), create_remote_ban_list=AsyncMock())
    with pytest.raises(ValidationError):
        asyncio.run(ns['create_ban_list'](peer, object(), 'HLL'))
    peer.create_remote_ban_list.assert_not_awaited()
    assert peer.config.hll_banlist_id == 'old-list'

    class Factory:
        def begin(self):
            return self
        async def __aenter__(self):
            return object()
        async def __aexit__(self, *args):
            pass
    ns['session_factory'] = Factory()
    peer.config.hll_banlist_id = None
    peer.create_remote_ban_list.return_value = 'new-list'
    peer.update = AsyncMock()
    assert asyncio.run(ns['create_ban_list'](peer, object(), 'HLL')) == 'new-list'
    assert peer.config.hll_banlist_id == 'new-list'
    peer.update.assert_awaited_once()


def test_patch_still_needs_durable_intent_for_lost_replies():
    root = os.getenv('BARRICADE_PUBLIC_SOURCE_DIR')
    if not root or not os.getenv('BARRICADE_EXPECT_FIXED'):
        pytest.skip('requires patched peer sources')
    data = (Path(root) / 'custom.py').read_bytes().replace(b'\r\n', b'\n')
    assert hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest() == 'ba6336d449f4b72f3459aff64d6a4b49207fd284'
    tree = ast.parse(data.decode())
    klass = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'CustomIntegration')
    method = next(n for n in klass.body if isinstance(n, ast.AsyncFunctionDef) and n.name == 'bulk_ban_players')
    method.decorator_list = []
    module = ast.Module(body=[ast.ImportFrom(module='__future__', names=[ast.alias(name='annotations')], level=0), method], type_ignores=[])
    ast.fix_missing_locations(module)

    class Factory:
        def begin(self):
            return self
        async def __aenter__(self):
            return object()
        async def __aexit__(self, *args):
            pass

    ns = {'session_factory': Factory(), 'itertools': itertools, 'batched': itertools.batched}
    exec(compile(module, '<patched-peer-bulk>', 'exec'), ns)
    attempts = []
    player = SimpleNamespace(id=1, get_game_id=lambda game: 'synthetic-eos')
    response = SimpleNamespace(player_report=SimpleNamespace(player_id=1, player=player, report=SimpleNamespace(game='HLLV')))
    class Peer:
        logger = logging.getLogger('synthetic-barricade')
        async def get_ban(self, *args, **kwargs):
            return None
        def get_ban_reason(self, response):
            return 'synthetic'
        async def add_multiple_bans(self, mapping, game):
            attempts.append(dict(mapping))
            # The remote side may have acted before its reply was lost.
            raise ConnectionError('synthetic lost reply')
            yield
    for _ in range(2):
        with pytest.raises(ConnectionError):
            asyncio.run(ns['bulk_ban_players'](Peer(), [response]))
    assert len(attempts) == 2
