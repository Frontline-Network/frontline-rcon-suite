"""Offline probe of a pinned public Barricade community-ban endpoint."""
import ast
import asyncio
import hashlib
import inspect
import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest


def test_pinned_community_bans_endpoint_returns_nested_coroutine():
    path = os.environ.get("BARRICADE_PEER_BANS_SOURCE")
    if not path:
        pytest.skip("requires the pinned public Barricade bans router")
    source = Path(path).read_bytes().replace(b"\r\n", b"\n")
    blob = b"blob " + str(len(source)).encode() + b"\0" + source
    assert hashlib.sha1(blob).hexdigest() == "01539f3417ca0cac7ab965bb1b1d9e20d196a9e7"
    tree = ast.parse(source.decode())
    node = next(item for item in tree.body if isinstance(item, ast.AsyncFunctionDef)
                and item.name == "get_own_community_bans")
    node.decorator_list = []
    node.returns = None
    for arg in (*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs):
        arg.annotation = None
    module = ast.fix_missing_locations(ast.Module(body=[node], type_ignores=[]))
    get_bans = AsyncMock(return_value={"synthetic": True})
    namespace = {"get_bans": get_bans}
    exec(compile(module, "<pinned-barricade-bans-router>", "exec"), namespace)

    async def probe():
        result = await namespace["get_own_community_bans"](
            object(), object(), SimpleNamespace(community_id=7), integration_id=9
        )
        assert inspect.iscoroutine(result)
        get_bans.assert_not_awaited()
        assert await result == {"synthetic": True}  # clean up the returned coroutine
        get_bans.assert_awaited_once()

    asyncio.run(probe())


@pytest.mark.parametrize("await_nested, expected_status", [(False, 500), (True, 200)])
@pytest.mark.parametrize("model_kind", ["dictionary", "public_paginator"])
def test_pinned_community_bans_handler_with_fastapi_response_model(await_nested, expected_status, model_kind):
    fastapi = pytest.importorskip("fastapi")
    path = os.environ.get("BARRICADE_PEER_BANS_SOURCE")
    if not path:
        pytest.skip("requires the pinned public Barricade bans router")
    source = Path(path).read_bytes().replace(b"\r\n", b"\n")
    blob = b"blob " + str(len(source)).encode() + b"\0" + source
    assert hashlib.sha1(blob).hexdigest() == "01539f3417ca0cac7ab965bb1b1d9e20d196a9e7"
    node = next(item for item in ast.parse(source.decode()).body
                if isinstance(item, ast.AsyncFunctionDef) and item.name == "get_own_community_bans")
    node.decorator_list = []
    node.returns = None
    for arg in (*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs):
        arg.annotation = None
    module = ast.fix_missing_locations(ast.Module(body=[node], type_ignores=[]))
    get_bans = AsyncMock(return_value={"limit": 100, "items": [], "links": {"prev": None, "next": None}})
    namespace = {"get_bans": get_bans}
    exec(compile(module, "<pinned-barricade-bans-router>", "exec"), namespace)
    pending = []
    app = fastapi.FastAPI()
    response_model = dict
    if model_kind == "public_paginator":
        paginator_path = os.environ.get("BARRICADE_PEER_PAGINATOR_SOURCE")
        if not paginator_path:
            pytest.skip("requires the pinned public Barricade paginator")
        paginator_source = Path(paginator_path).read_bytes().replace(b"\r\n", b"\n")
        paginator_blob = b"blob " + str(len(paginator_source)).encode() + b"\0" + paginator_source
        assert hashlib.sha1(paginator_blob).hexdigest() == "c5c3ea7c9177acd608e2db4e1d585783585db18c"
        from typing import Generic, TypeVar
        from pydantic import AnyHttpUrl, BaseModel
        classes = [item for item in ast.parse(paginator_source.decode()).body
                   if isinstance(item, ast.ClassDef) and item.name in {"PaginatedResponseLinks", "PaginatedResponse"}]
        assert len(classes) == 2
        public_types = {"__name__": "pinned_barricade_paginator", "BaseModel": BaseModel,
                        "Generic": Generic, "M": TypeVar("M"), "AnyHttpUrl": AnyHttpUrl}
        exec(compile(ast.fix_missing_locations(ast.Module(body=classes, type_ignores=[])),
                     "<pinned-barricade-paginator>", "exec"), public_types)
        response_model = public_types["PaginatedResponse"][dict]

    @app.get("/synthetic", response_model=response_model)
    async def endpoint():
        result = await namespace["get_own_community_bans"](
            object(), object(), SimpleNamespace(community_id=7), integration_id=9
        )
        if await_nested:
            return await result
        pending.append(result)
        return result

    async def probe():
        sent = []
        scope = {"type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1",
                 "method": "GET", "scheme": "http", "path": "/synthetic",
                 "raw_path": b"/synthetic", "query_string": b"", "headers": [],
                 "server": ("test", 80), "client": ("test", 1), "root_path": ""}
        async def receive():
            return {"type": "http.request", "body": b"", "more_body": False}
        async def send(message):
            sent.append(message)
        try:
            await app(scope, receive, send)
        except fastapi.exceptions.ResponseValidationError:
            assert not await_nested
        finally:
            for coroutine in pending:
                coroutine.close()
        assert next(item["status"] for item in sent if item["type"] == "http.response.start") == expected_status
        assert get_bans.await_count == (1 if await_nested else 0)

    asyncio.run(probe())
