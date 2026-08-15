import json
import logging
import os
from copy import deepcopy
from typing import Any

import requests
from django.http import QueryDict
from django.views.decorators.csrf import csrf_exempt

from rcon.utils import ApiKey, get_server_number

from .auth import AUTHORIZATION, api_response, login_required
from .decorators import permission_required, require_http_methods

logger = logging.getLogger("rcon")


def mobile_server_list(request, local_name: str) -> list[dict]:
    """Return the reachable game-server backends represented by this installation."""

    servers = [
        {
            "server_number": int(get_server_number()),
            "name": local_name,
            "game": os.getenv("HLL_GAME", "hll"),
            "available": True,
        }
    ]
    if not request.user.has_perm("api.can_view_other_crcon_servers"):
        return servers

    try:
        api_key = ApiKey()
        keys = api_key.get_all_keys()
        my_key = api_key.get_key()
    except Exception:
        logger.warning("Multi-server discovery is unavailable", exc_info=True)
        return servers
    auth_header = request.headers.get(AUTHORIZATION)
    headers = {"AUTHORIZATION": auth_header} if auth_header else {}
    cookies = (
        {"sessionid": request.COOKIES["sessionid"]}
        if request.COOKIES.get("sessionid")
        else {}
    )
    for host, key in keys.items():
        if key == my_key:
            continue
        try:
            response = requests.get(
                f"http://{host}/api/get_connection_info",
                timeout=3,
                headers=headers,
                cookies=cookies,
            )
            response.raise_for_status()
            info = response.json().get("result") or {}
            server_number = int(info["server_number"])
            if any(item["server_number"] == server_number for item in servers):
                continue
            servers.append(
                {
                    "server_number": server_number,
                    "name": str(info.get("name") or f"Server {server_number}"),
                    "game": info.get("game"),
                    "available": True,
                }
            )
        except (KeyError, TypeError, ValueError, requests.RequestException):
            logger.warning("Unable to discover mobile CRCON server at %s", host)
    return sorted(servers, key=lambda item: item["server_number"])


@login_required()
@permission_required("api.can_view_other_crcon_servers", raise_exception=True)
@csrf_exempt
@require_http_methods(["GET"])
def get_server_list(request):
    api_key = ApiKey()
    keys = api_key.get_all_keys()
    my_key = api_key.get_key()

    auth_header: str | None = request.headers.get(AUTHORIZATION)
    headers = {"AUTHORIZATION": auth_header} if auth_header else {}

    logger.debug(keys)
    names = []
    for host, key in keys.items():
        if key == my_key:
            continue
        url = f"http://{host}/api/get_connection_info"
        try:
            res = requests.get(
                url,
                timeout=5,
                cookies=dict(sessionid=request.COOKIES.get("sessionid")),
                headers=headers,
            )
            if res.ok:
                names.append(res.json()["result"])
        except requests.exceptions.RequestException:
            logger.warning(f"Unable to connect with {url}")

    return api_response(names, failed=False, command="server_list")


def forward_request(request):
    api_key = ApiKey()
    keys = api_key.get_all_keys()
    my_key = api_key.get_key()

    sessionid: str | None = request.COOKIES.get("sessionid")
    auth_header: str | None = request.headers.get(AUTHORIZATION)
    cookies = {"sessionid": sessionid} if sessionid else {}
    headers = {"AUTHORIZATION": auth_header} if auth_header else {}

    results = []
    for host, key in keys.items():
        if key == my_key:
            continue
        try:
            url = f"http://{host}{request.path}"

            params = dict(request.GET)
            params.pop("forward", None)
            try:
                data = json.loads(request.body)
                data.pop("forward", None)
            except json.JSONDecodeError as e:
                logger.error("JSON parse error %s: %s", request.path, e)
                data = None
            logger.info("Forwarding request: %s %s %s", url, params, data)
            res = requests.post(
                url,
                params=params,
                json=data,
                timeout=5,
                cookies=cookies,
                headers=headers,
            )
            # Automatically retry HttpResponseNotAllowed errors as GET requests
            if res.status_code == 405:
                res = requests.get(
                    url,
                    params=params,
                    json=data,
                    timeout=5,
                    cookies=cookies,
                    headers=headers,
                )

            if res.ok:
                r = {"host": host, "response": res.json()}
                results.append(r)
                logger.info(r)
            else:
                # todo add failure to results
                logger.warning(f"Forwarding to {host} failed %s", res.text)
        except requests.exceptions.RequestException:
            logger.warning(f"Unable to connect with {url=}")

    return results


def forward_command(
    path: str,
    sessionid: str | None,
    auth_header: str | None,
    params: dict[str, Any] | None = None,
    json: dict[str, Any] | QueryDict | None = None,
):
    server_api_key = ApiKey()
    keys = server_api_key.get_all_keys()
    my_key = server_api_key.get_key()
    params = deepcopy(params) or {}
    data = deepcopy(json) or {}
    cookies = {"sessionid": sessionid} if sessionid else {}
    headers = {"AUTHORIZATION": auth_header} if auth_header else {}
    results = []

    if "forwarded" in params or "forwarded" in data:
        logger.debug("The request was already forwarded")
        return []
    if params:
        params.pop("forward", None)
        params["forwarded"] = True
    if data:
        data.pop("forward", None)
        data["forwarded"] = True

    for host, key in keys.items():
        if key == my_key:
            continue
        try:
            url = f"http://{host}{path}"

            logger.info("Forwarding command: %s %s %s", url, params, data)
            res = requests.post(
                url,
                params=params,
                json=data,
                timeout=5,
                cookies=cookies,
                headers=headers,
            )
            # Automatically retry HttpResponseNotAllowed errors as GET requests
            if res.status_code == 405:
                res = requests.get(
                    url,
                    params=params,
                    json=data,
                    timeout=5,
                    cookies=cookies,
                    headers=headers,
                )

            if res.ok:
                r = {"host": host, "response": res.json()}
                results.append(r)
            else:
                # todo add failure to results
                logger.warning(f"Forwarding to {host} failed %s", res.text)
        except requests.exceptions.RequestException as e:
            logger.warning("Unable to connect with %s: %s", host, e)

    return results


def forward_mobile_request_to_server(
    request,
    server_number: int,
    path: str,
    data: dict | None = None,
    *,
    method: str = "POST",
    params: dict | None = None,
):
    """Forward one mobile command to exactly one CRCON game-server backend."""

    if int(get_server_number()) == int(server_number):
        return None

    try:
        api_key = ApiKey()
        keys = api_key.get_all_keys()
        my_key = api_key.get_key()
    except Exception as exc:
        raise ValueError("CRCON multi-server discovery is unavailable") from exc
    auth_header = request.headers.get(AUTHORIZATION)
    headers = {"AUTHORIZATION": auth_header} if auth_header else {}

    for host, key in keys.items():
        if key == my_key:
            continue
        try:
            connection_response = requests.get(
                f"http://{host}/api/get_connection_info",
                timeout=5,
                headers=headers,
            )
            if not connection_response.ok:
                continue
            connection_info = connection_response.json().get("result") or {}
            if int(connection_info.get("server_number", -1)) != int(server_number):
                continue
            payload = deepcopy(data) or {}
            query = deepcopy(params) or {}
            if method.upper() == "GET":
                query["forwarded"] = "1"
                return requests.get(
                    f"http://{host}{path}",
                    params=query,
                    timeout=10,
                    headers=headers,
                )
            payload["forwarded"] = True
            return requests.request(
                method.upper(),
                f"http://{host}{path}",
                json=payload,
                params=query,
                timeout=10,
                headers=headers,
            )
        except (requests.RequestException, TypeError, ValueError):
            logger.exception("Unable to forward mobile request to %s", host)

    raise ValueError(f"CRCON server {server_number} is unavailable")
