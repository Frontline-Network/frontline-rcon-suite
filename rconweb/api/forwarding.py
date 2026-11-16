import logging
from copy import deepcopy
from typing import Any

import requests
from django.conf import settings
from django.http import QueryDict

from rcon.utils import ApiKey, get_server_number

logger = logging.getLogger("rcon")
FRONTEND_KEY_PREFIX = "frontend_"
CSRF_RECOVERY_HEADER = "X-CRCON-CSRF-Recovery"
CSRF_TOKEN_HEADER = "X-CRCON-CSRF-Token"
CSRF_REQUEST_HEADER = "X-CSRFToken"


def normalize_forward_server_numbers(value) -> tuple[int, ...] | None:
    """Validate an optional, deterministic subset of multi-server targets.

    ``None`` preserves the legacy meaning of ``forward=true``: every other
    registered CRCON backend. A concrete value lets prepared actions retry only
    the failed server targets without repeating an already successful local or
    remote action.
    """

    if value is None:
        return None
    if isinstance(value, bool):
        raise ValueError("forward_server_numbers must contain server numbers")
    values = value if isinstance(value, (list, tuple, set)) else [value]
    if len(values) > 50:
        raise ValueError("At most 50 forward server numbers are allowed")

    normalized: list[int] = []
    for raw in values:
        if isinstance(raw, bool):
            raise ValueError("forward_server_numbers must contain server numbers")
        if not isinstance(raw, (int, str)):
            raise ValueError("forward_server_numbers must contain server numbers")
        try:
            server_number = int(raw)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                "forward_server_numbers must contain server numbers"
            ) from exc
        if server_number < 1:
            raise ValueError("forward server numbers must be positive")
        if server_number not in normalized:
            normalized.append(server_number)
    return tuple(normalized)


def _registered_server_number(host: str) -> int | None:
    if not host.startswith(FRONTEND_KEY_PREFIX):
        return None
    try:
        server_number = int(host.removeprefix(FRONTEND_KEY_PREFIX))
    except ValueError:
        return None
    return server_number if server_number > 0 else None


def _forward_failure(error: str) -> dict:
    return {
        "result": None,
        "failed": True,
        "error": error,
        "forward_results": None,
    }


def _safe_forward_response(response) -> dict:
    try:
        payload = response.json()
    except ValueError:
        return _forward_failure("The CRCON peer returned an invalid response")
    if not isinstance(payload, dict):
        return _forward_failure("The CRCON peer returned an invalid response")
    if not response.ok:
        remote_error = payload.get("error")
        if not isinstance(remote_error, str) or not remote_error.strip():
            remote_error = f"CRCON peer returned HTTP {response.status_code}"
        return _forward_failure(remote_error.strip()[:256])
    return payload


def _post_with_csrf_recovery(
    url: str,
    *,
    params: dict,
    data: dict,
    timeout: int,
    cookies: dict,
    headers: dict,
):
    """POST once, then recover one rejected session-CSRF request safely.

    Browser-originated multi-server actions forward the authenticated Django
    session to each peer. The peers therefore enforce CSRF just like they do
    for the original browser request. Their CSRF failure response contains a
    fresh token and cookie; retrying exactly once mirrors the browser recovery
    flow without weakening CSRF protection or exempting mutating endpoints.
    """

    response = requests.post(
        url,
        params=params,
        json=data,
        timeout=timeout,
        cookies=cookies,
        headers=headers,
    )
    response_headers = getattr(response, "headers", {})
    if (
        response.status_code != 403
        or response_headers.get(CSRF_RECOVERY_HEADER) != "1"
    ):
        return response

    recovery_token = response_headers.get(CSRF_TOKEN_HEADER)
    response_cookies = getattr(response, "cookies", {})
    recovery_cookie = response_cookies.get(settings.CSRF_COOKIE_NAME)
    if not recovery_token or not recovery_cookie:
        return response

    retry_headers = dict(headers)
    retry_headers[CSRF_REQUEST_HEADER] = recovery_token
    retry_cookies = dict(cookies)
    retry_cookies[settings.CSRF_COOKIE_NAME] = recovery_cookie
    return requests.post(
        url,
        params=params,
        json=data,
        timeout=timeout,
        cookies=retry_cookies,
        headers=retry_headers,
    )


def forwarding_unavailable_results(server_numbers=None) -> list[dict]:
    requested_server_numbers = normalize_forward_server_numbers(server_numbers)
    current_server_number = int(get_server_number())
    targets = (
        requested_server_numbers if requested_server_numbers is not None else (None,)
    )
    return [
        {
            "host": None,
            "server_number": server_number,
            "status_code": None,
            "response": _forward_failure(
                "CRCON multi-server forwarding is unavailable"
            ),
        }
        for server_number in targets
        if server_number != current_server_number
    ]


def forward_command(
    path: str,
    sessionid: str | None,
    auth_header: str | None,
    params: dict[str, Any] | None = None,
    json: dict[str, Any] | QueryDict | None = None,
):
    params = deepcopy(params) or {}
    data = deepcopy(json) or {}
    requested_server_numbers = normalize_forward_server_numbers(
        data.pop("forward_server_numbers", None)
    )
    cookies = {"sessionid": sessionid} if sessionid else {}
    headers = {"AUTHORIZATION": auth_header} if auth_header else {}
    results = []

    if "forwarded" in params or "forwarded" in data:
        logger.debug("The request was already forwarded")
        return []
    current_server_number = int(get_server_number())
    if requested_server_numbers is not None and not any(
        server_number != current_server_number
        for server_number in requested_server_numbers
    ):
        return []

    server_api_key = ApiKey()
    keys = server_api_key.get_all_keys()
    my_key = server_api_key.get_key()
    if params:
        params.pop("forward", None)
        params["forwarded"] = True
    if data:
        data.pop("forward", None)
        data["forwarded"] = True

    registered_targets = []
    for host, key in keys.items():
        server_number = _registered_server_number(host)
        if key == my_key or server_number == current_server_number:
            continue
        if (
            requested_server_numbers is not None
            and server_number not in requested_server_numbers
        ):
            continue
        registered_targets.append((server_number, host))

    registered_targets.sort(
        key=lambda target: (
            target[0] is None,
            target[0] if target[0] is not None else target[1],
        )
    )
    registered_numbers = {
        server_number
        for server_number, _host in registered_targets
        if server_number is not None
    }

    for server_number, host in registered_targets:
        result = {
            "host": host,
            "server_number": server_number,
            "status_code": None,
            "response": None,
        }
        try:
            url = f"http://{host}{path}"

            logger.info("Forwarding command to server %s", server_number)
            res = _post_with_csrf_recovery(
                url,
                params=params,
                data=data,
                timeout=5,
                cookies=cookies,
                headers=headers,
            )
            if res.status_code == 405:
                res = requests.get(
                    url,
                    params=params,
                    json=data,
                    timeout=5,
                    cookies=cookies,
                    headers=headers,
                )
            result["status_code"] = res.status_code
            result["response"] = _safe_forward_response(res)
            results.append(result)
            if result["response"].get("failed"):
                logger.warning(
                    "Forwarding to %s (server %s) failed with HTTP %s",
                    host,
                    server_number,
                    res.status_code,
                )
        except requests.exceptions.RequestException:
            logger.warning("Unable to connect to server %s", server_number)
            result["response"] = _forward_failure(
                "The target CRCON server did not respond"
            )
            results.append(result)

    if requested_server_numbers is not None:
        for server_number in requested_server_numbers:
            if (
                server_number == current_server_number
                or server_number in registered_numbers
            ):
                continue
            results.append(
                {
                    "host": None,
                    "server_number": server_number,
                    "status_code": None,
                    "response": _forward_failure(
                        "The target CRCON server is not registered"
                    ),
                }
            )

    results.sort(
        key=lambda result: (
            result["server_number"] is None,
            (
                result["server_number"]
                if result["server_number"] is not None
                else result["host"]
            ),
        )
    )

    return results
