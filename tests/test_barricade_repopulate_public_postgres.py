"""Read-only contract probe against pinned public Barricade query source.

This models only the query's fields in a disposable PostgreSQL schema; no
Barricade credentials, production rows, game server or sanctions are involved.
"""
import ast
import asyncio
import hashlib
import itertools
import logging
import os
from pathlib import Path
from types import SimpleNamespace
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
    assert hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest() == 'c0f2c324fe9452a7d1c3120963b72d72cc9e95be'
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
        assert len(results) == (0 if existing_hll_ref else 1)


def test_public_repopulate_reports_success_when_missing_game_id_is_skipped():
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
    bulk = method('custom.py', '20a04c97250fa7fadaa17822e3b4e5768a1626ff', 'CustomIntegration', 'bulk_ban_players')
    module = ast.Module(body=[ast.ImportFrom(module='__future__', names=[ast.alias(name='annotations')], level=0),
                              repopulate, bulk], type_ignores=[])
    ast.fix_missing_locations(module)

    def response(pid, game_id):
        player = SimpleNamespace(id=pid, get_game_id=lambda game: game_id)
        return SimpleNamespace(player_report=SimpleNamespace(player_id=pid, player=player,
                                                            report=SimpleNamespace(game='HLLV')))
    responses = [response(1, 'synthetic-eos'), response(2, None)]

    class Factory:
        def __call__(self):
            return self
        def begin(self):
            return self
        async def __aenter__(self):
            return object()
        async def __aexit__(self, *args):
            pass

    async def query(*args, **kwargs):
        return responses

    namespace = {'session_factory': Factory(), 'get_successful_responses_without_bans': query,
                 'schemas': SimpleNamespace(ResponseWithToken=SimpleNamespace(model_validate=lambda x: x)),
                 'itertools': itertools, 'batched': itertools.batched,
                 'IntegrationBulkBanError': type('IntegrationBulkBanError', (Exception,), {})}
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
            for game_id in mapping:
                yield game_id, 'synthetic-record'
        async def set_multiple_ban_ids(self, db, *items):
            created.extend(items)
        bulk_ban_players = namespace['bulk_ban_players']

    assert asyncio.run(namespace['repopulate'](Peer())) == (2, 2)
    assert created == [(1, 'synthetic-record', 'HLLV')]
