import asyncio
import itertools
import os
import time
from contextvars import Context
from threading import Event
from logging import getLogger
from urllib.parse import parse_qsl

import pydantic
from cachetools import TTLCache
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.urls import path
from sqlalchemy import exists

from rcon import models
from rcon.barricade import *
from rcon.blacklist import (
    BlacklistBarricadeWarnOnlineCommand,
    BlacklistCommand,
    BlacklistCommandHandler,
    BlacklistCommandType,
    add_record_to_blacklist,
    get_player_blacklist_records,
    remove_record_from_blacklist,
)
from rcon.vip_rewards.locking import lock
from rcon.utils import get_server_number

logger = getLogger("rconweb")


def _explicit_durable_request(query_string):
    """Recognize a peer requesting the registered integration namespace."""
    if not isinstance(query_string, bytes) or len(query_string) > 2048:
        return True
    try:
        pairs = parse_qsl(query_string.decode('utf-8'), keep_blank_values=True,
                          encoding='utf-8', errors='strict', max_num_fields=16)
    except (UnicodeError, ValueError):
        return True
    return any(key == 'frontline_integration' for key, _ in pairs)


@database_sync_to_async
def assert_blacklist_exists(blacklist_id: int):
    stmt = exists().where(models.Blacklist.id == blacklist_id)
    with models.enter_session() as sess:
        if not sess.query(stmt).scalar():
            raise BarricadeRequestError("Blacklist does not exist")


@database_sync_to_async
def ban_player(player_id: str, blacklist_id: int, reason: str) -> int | None:
    try:
        # Concurrent requests/retries for the same player and list must not
        # both create a record after observing an empty result.
        with lock(f"barricade-ban:{blacklist_id}:{player_id}"):
            with models.enter_session() as sess:
                current_records = get_player_blacklist_records(
                    sess=sess,
                    player_id=player_id,
                    include_expired=False,
                    include_other_servers=True,
                )
                matching = next((record for record in current_records
                                 if record.blacklist_id == blacklist_id), None)
                if matching is not None:
                    return matching.id

            record = add_record_to_blacklist(
                player_id=player_id,
                blacklist_id=blacklist_id,
                reason=reason,
                admin_name="Barricade",
            )
    except:
        logger.exception("Failed to blacklist player %s", player_id)
        return None
    else:
        return record["id"]


@database_sync_to_async
def unban_player(record_id: int, blacklist_id: int):
    try:
        return remove_record_from_blacklist(
            record_id=record_id, expected_blacklist_id=blacklist_id
        ) is True
    except:
        logger.exception("Failed to remove blacklist record #%s", record_id)
        return False


class BarricadeConsumer(AsyncJsonWebsocketConsumer):
    groups = [GROUP_NAME]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._counter = itertools.count()
        self._waiters: dict[int, asyncio.Future] = {}
        self._processing: set[int] = set()
        self._resp_cache = TTLCache(9999, ttl=60)
        self._scan_players_task = None
        self._report_scan_tasks = set()

    async def connect(self):
        enabled = os.getenv('HLL_BARRICADE_DURABLE_SCANS', '1') == '1'
        bound = (self.scope.get('barricade_scan_namespace')
                 and self.scope.get('barricade_credential_id'))
        durable = enabled and bound
        if (self.scope.get('barricade_registered_namespace') or self.scope.get('barricade_scan_namespace') or
                _explicit_durable_request(self.scope.get('query_string', b''))) and not bound:
            logger.warning('Rejected Barricade durable integration: disabled or not registered')
            await self.close(code=4403)
            return
        logger.info("Accepted connection with Barricade client")
        await self.accept()
        if self._scan_players_task and not self._scan_players_task.done():
            self._scan_players_task.cancel()
        if durable:
            self._scan_players_task = asyncio.create_task(self._durable_scan_loop())

    async def disconnect(self, code):
        logger.info("Closed connection with Barricade client")

        if self._scan_players_task and not self._scan_players_task.done():
            self._scan_players_task.cancel()
        for task in tuple(self._report_scan_tasks):
            task.cancel()

    async def _durable_scan_once(self):
        """Experimental only: missing evidence defers a scan, never invents it."""
        from rcon import barricade_scan_dispatch, barricade_scan_presence
        from rcon.cache_utils import get_redis_client
        from rcon.player_presence import database_scope

        server_number = int(get_server_number())
        scope = database_scope(os.environ['HLL_DB_URL'])
        redis = get_redis_client(global_pool=True)
        from rcon.player_presence import redis_time
        # One barrier per pass; each player is still individually rechecked
        # against the current roster, session and non-superseded log poll.
        barrier = await asyncio.to_thread(redis_time, redis)

        async def verify_session(session_id, player_id):
            return await barricade_scan_presence.confirm_with_fresh_poll(
                redis, scope=scope, server_number=server_number, session_id=session_id, player_id=player_id,
                barrier=barrier)

        roster = None
        roster_checked = float('-inf')
        async def get_roster():
            nonlocal roster, roster_checked
            if time.monotonic() - roster_checked >= 5:
                deadline = time.monotonic() + 20
                while True:
                    roster = await asyncio.to_thread(barricade_scan_presence.observed_players_after,
                        redis, scope=scope, server_number=server_number, barrier=barrier)
                    if roster is not None or time.monotonic() >= deadline:
                        break
                    await asyncio.sleep(.25)
                roster_checked = time.monotonic()
            return roster

        async def observed_player(_session_id, player_id):
            roster = await get_roster()
            return player_id in roster if roster is not None else None

        async def send_scan(player_id, game):
            return await self.send_request(ServerRequestType.SCAN_PLAYERS,
                ScanPlayersRequestPayload(player_ids=[player_id], game=game).model_dump())

        return await barricade_scan_dispatch.scan_once(server_number,
            self.scope['barricade_scan_namespace'], barricade_game_for_server(), send_scan, verify_session,
            credential_id=self.scope['barricade_credential_id'], is_observed=observed_player, get_roster=get_roster)

    async def _durable_scan_loop(self):
        while True:
            await asyncio.sleep(60)
            try:
                await self._durable_scan_once()
            except Exception:
                logger.exception('Experimental Barricade scan pass failed; no legacy fallback')

    async def receive_json(self, content, **kwargs):
        try:
            request = content["request"]
        except KeyError:
            logger.error("Received malformed Barricade request: %s", content)
            return

        try:
            if request:
                await self.handle_request(RequestBody.model_validate(content))
            else:
                await self.handle_response(ResponseBody.model_validate(content))
        except pydantic.ValidationError:
            logger.error("Received malformed Barricade request: %s", content)
            return

    async def send_request(
        self, request_type: ServerRequestType, payload: dict | None
    ) -> dict | None:
        request = RequestBody(
            id=next(self._counter),
            request=request_type,
            payload=payload,
        )
        # Register before yielding to the websocket send: a fast peer can
        # otherwise answer before the response waiter exists.
        fut = asyncio.get_running_loop().create_future()
        self._waiters[request.id] = fut

        try:
            await self.send_json(request.model_dump())
            # Wait for response
            response: dict | None = await asyncio.wait_for(fut, timeout=10)
        except asyncio.TimeoutError:
            logger.error("Barricade did not respond in time to request: %r", request)
            raise
        except BarricadeRequestError as e:
            logger.error(
                'Barricade returned error "%s" %s for request: %r',
                e.error,
                e.kwargs,
                request,
            )
            raise
        finally:
            # Remove waiter
            if request.id in self._waiters:
                del self._waiters[request.id]
            if not fut.done():
                fut.cancel()
            elif not fut.cancelled():
                # A response may arrive before send_json subsequently fails.
                # Consume any stored error so it does not become unhandled.
                fut.exception()

        return response

    async def handle_request(self, request: RequestBody):
        if request.id in self._processing:
            return

        if cached_response := self._resp_cache.get(request.id):
            await self.send_json(cached_response)
            return

        try:
            self._processing.add(request.id)

            try:
                result = None

                match request.request:
                    case ClientRequestType.BAN_PLAYERS:
                        result = await self.ban_players(
                            BanPlayersRequestPayload.model_validate(request.payload)
                        )
                    case ClientRequestType.UNBAN_PLAYERS:
                        result = await self.unban_players(
                            UnbanPlayersRequestPayload.model_validate(request.payload)
                        )
                    case ClientRequestType.NEW_REPORT:
                        result = await self.new_report(
                            NewReportRequestPayload.model_validate(request.payload)
                        )
                    case _:
                        raise BarricadeRequestError("No such command")

                response = request.response_ok(result)

            except pydantic.ValidationError as e:
                logger.warn("Failed to validate payload: %s", e)
                response = request.response_error("Failed to validate payload")
            except BarricadeRequestError as e:
                # These should indicate a client error...
                response = request.response_error(e.error, **e.kwargs)
            except Exception as e:
                # ...whereas these typically indicate a server error
                logger.error(
                    "Internal error when handling Barricade request: %r",
                    request,
                    exc_info=e,
                )
                response = request.response_error(f"{type(e).__name__}: {e}")

            # Respond
            dumped_response = response.model_dump()
            self._resp_cache[response.id] = dumped_response
            await self.send_json(dumped_response)

        finally:
            self._processing.remove(request.id)

    async def handle_response(self, response: ResponseBody):
        waiter = self._waiters.get(response.id)

        # Make sure response is being awaited
        if not waiter:
            logger.warning(
                "Discarding response since it is not being awaited: %r", response
            )
            return

        # Make sure waiter is still available
        if waiter.done():
            logger.warning(
                "Discarding response since waiter is already marked done: %r", response
            )
            return

        # Set response
        if response.failed:
            waiter.set_exception(BarricadeRequestError(**response.response))
        else:
            waiter.set_result(response.response)

    async def handle_broadcast(self, event):
        if event.get('request_type') == ServerRequestType.SCAN_PLAYERS.value:
            return
        try:
            return await self.send_request(event["request_type"], event["payload"])
        except (asyncio.TimeoutError, BarricadeRequestError):
            # These are already logged by send_request
            pass

    async def ban_players(self, payload: BanPlayersRequestPayload):
        validate_barricade_game(payload.config.game)
        if payload.config.banlist_id is None:
            raise BarricadeRequestError("Missing config.banlist_id")

        try:
            blacklist_id = int(payload.config.banlist_id)
        except ValueError:
            raise BarricadeRequestError("Invalid banlist ID")

        await assert_blacklist_exists(blacklist_id)

        ids = await asyncio.gather(*[
                ban_player(
                    player_id=player_id,
                    blacklist_id=blacklist_id,
                    reason=reason or payload.config.reason,
                )
                for player_id, reason in payload.player_ids.items()
            ])
        # The client expects strings for confirmed records. A missing ID is
        # an uncertain/failed write, not the literal successful ID "None".
        ban_ids = {player_id: str(ban_id)
                   for player_id, ban_id in zip(payload.player_ids, ids)
                   if ban_id is not None}
        if len(ban_ids) != len(payload.player_ids):
            raise BarricadeRequestError("Could not blacklist all players", ban_ids=ban_ids)
        return {"ban_ids": ban_ids}

    async def unban_players(self, payload: UnbanPlayersRequestPayload):
        validate_barricade_game(payload.config.game)
        try:
            blacklist_id = int(payload.config.banlist_id)
        except ValueError:
            raise BarricadeRequestError("Invalid banlist ID")
        await assert_blacklist_exists(blacklist_id)

        record_ids: list[int] = []
        for record_id in payload.record_ids:
            try:
                record_id = int(record_id)
            except ValueError:
                continue
            record_ids.append(record_id)

        successes = await asyncio.gather(
            *[unban_player(record_id, blacklist_id) for record_id in record_ids]
        )

        successful_record_ids = [
            # The client expects strings, not ints
            str(record_id)
            for record_id, success in zip(record_ids, successes)
            if success
        ]

        response = {"ban_ids": successful_record_ids}

        if len(successful_record_ids) != len(payload.record_ids):
            raise BarricadeRequestError("Could not unban all players", **response)
        else:
            return response

    async def new_report(self, payload: NewReportRequestPayload):
        validate_barricade_game(payload.game)
        namespace = self.scope.get('barricade_scan_namespace')
        credential = self.scope.get('barricade_credential_id')
        if (os.getenv('HLL_BARRICADE_DURABLE_SCANS', '1') != '1'
                or not namespace or not credential):
            # This acknowledges receipt of the report, not delivery of a scan.
            return
        server = int(get_server_number())
        from rcon import barricade_scan_dispatch

        async def send_scan(player_ids):
            return await self.send_request(ServerRequestType.SCAN_PLAYERS,
                ScanPlayersRequestPayload(player_ids=player_ids, game=barricade_game_for_server()).model_dump())

        async def dispatch():
            try:
                await barricade_scan_dispatch.dispatch_report_scan(
                    server, namespace, credential, [player.player_id for player in payload.players], send_scan)
            except Exception:
                logger.exception('Barricade report scan failed; no automatic retry')

        task = asyncio.create_task(dispatch())
        self._report_scan_tasks.add(task)
        task.add_done_callback(self._report_scan_tasks.discard)


from api.auth import APITokenAuthMiddleware

urlpatterns = [
    path(
        "ws/barricade",
        APITokenAuthMiddleware(
            app=BarricadeConsumer.as_asgi(),
            perms=(
                "api.can_view_blacklists",
                "api.can_create_blacklists",
                "api.can_add_blacklist_records",
                "api.can_change_blacklist_records",
                "api.can_delete_blacklist_records",
            ),
        ),
    )
]
