import asyncio

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.urls import path

from rcon.admin_incidents import list_incident_changes

from .auth import APITokenAuthMiddleware, has_perms
from .mobile import mobile_integration_enabled


def _json_value(value):
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: _json_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_value(item) for item in value]
    return value


class MobileIncidentStreamConsumer(AsyncJsonWebsocketConsumer):
    connected = False

    async def websocket_connect(self, *args, **kwargs):
        if not mobile_integration_enabled():
            await self.close(code=4004)
            return
        self.connected = True
        await super().websocket_connect(*args, **kwargs)

    async def websocket_disconnect(self, *args, **kwargs):
        self.connected = False
        await super().websocket_disconnect(*args, **kwargs)

    async def receive_json(self, content, **kwargs):
        try:
            cursor = int(content["cursor"])
            if cursor < 0:
                raise ValueError
        except (KeyError, TypeError, ValueError):
            await self.send_json({"error": "A valid incident cursor is required"})
            return await self.close(code=4000)

        statuses = content.get("status") or None
        server_numbers = content.get("server_number") or None
        if isinstance(statuses, str):
            statuses = [statuses]
        if isinstance(server_numbers, (str, int)):
            server_numbers = [server_numbers]
        while self.connected:
            if not await has_perms(self.scope, ("api.can_view_admin_incidents",)):
                await self.close(code=4003)
                return
            incidents, next_cursor = await database_sync_to_async(
                list_incident_changes
            )(
                cursor,
                limit=100,
            )
            if next_cursor != cursor:
                cursor = next_cursor
                if statuses:
                    incidents = [
                        incident
                        for incident in incidents
                        if incident["status"] in statuses
                    ]
                if server_numbers:
                    server_set = {int(value) for value in server_numbers}
                    incidents = [
                        incident
                        for incident in incidents
                        if incident["server_number"] in server_set
                    ]
                await self.send_json(
                    {
                        "incidents": _json_value(incidents),
                        "cursor": cursor,
                        "error": None,
                    }
                )
            await asyncio.sleep(0.5)


urlpatterns = [
    path(
        "ws/mobile/v1/incidents",
        APITokenAuthMiddleware(
            app=MobileIncidentStreamConsumer.as_asgi(),
            perms="api.can_view_admin_incidents",
        ),
    )
]
