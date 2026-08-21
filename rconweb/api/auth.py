import csv
import datetime
import json
import logging
from dataclasses import asdict, dataclass
from functools import wraps
from typing import Any, Sequence

import orjson
import pydantic
from channels.db import database_sync_to_async
from channels.security.websocket import WebsocketDenier
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import Group, Permission, User
from django.contrib.sessions.backends.db import SessionStore
from django.core.exceptions import PermissionDenied
from django.db.models.signals import post_delete, post_save
from django.http import HttpResponse, QueryDict, parse_cookie
from django.middleware.csrf import get_token
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django_ratelimit.decorators import ratelimit

from rcon.audit import heartbeat, set_registered_mods
from rcon.cache_utils import invalidates, ttl_cache
from rcon.types import DjangoGroup, DjangoPermission, DjangoUserPermissions
from rcon.user_config.rcon_server_settings import RconServerSettingsUserConfig
from rconweb.settings import SECRET_KEY, TAG_VERSION

from .decorators import require_content_type, require_http_methods
from .mobile_tokens import authenticate_mobile_access_token
from .models import DjangoAPIKey, SteamPlayer
from .ratelimits import login_account_rate_limit_key, request_rate_limit_key

logger = logging.getLogger("rconweb")

HTTP_AUTHORIZATION_HEADER = "HTTP_AUTHORIZATION"
AUTHORIZATION = "AUTHORIZATION"
BEARER = ("BEARER", "BEARER:")


def update_mods(sender, instance, **kwargs):
    """Update registered admin player IDs when User/SteamPlayer models are changed"""
    with invalidates(get_moderators_accounts):
        set_registered_mods(get_moderators_accounts())


post_save.connect(update_mods, sender=User)
post_delete.connect(update_mods, sender=User)
post_save.connect(update_mods, sender=SteamPlayer)
post_delete.connect(update_mods, sender=SteamPlayer)


def authenticate_bearer_token(raw_api_key: str | None):
    """Authenticate legacy API keys and revocable mobile access tokens."""

    mobile_identity = authenticate_mobile_access_token(raw_api_key)
    if mobile_identity:
        return mobile_identity

    hashed_api_key = make_password(raw_api_key, salt=SECRET_KEY.replace("$", ""))
    api_key = DjangoAPIKey.objects.select_related("user").get(api_key=hashed_api_key)
    return api_key.user, None


@database_sync_to_async
def get_user(raw_api_key) -> tuple[User, object | None]:
    return authenticate_bearer_token(raw_api_key)


@database_sync_to_async
def has_perms(scope, perms: tuple[str, ...]) -> bool:
    user = scope.get("user")
    if not user:
        return False
    try:
        user = User.objects.get(pk=user.pk)
    except User.DoesNotExist:
        return False
    scope["user"] = user
    if not user.is_active:
        return False
    device = scope.get("mobile_device")
    if device is not None:
        try:
            device.refresh_from_db(
                fields=("revoked_at", "absolute_expires_at", "user_id")
            )
        except device.__class__.DoesNotExist:
            return False
        if (
            device.revoked_at is not None
            or device.user_id != user.pk
            or not device.absolute_expires_at
            or device.absolute_expires_at <= timezone.now()
        ):
            return False
    return user.has_perms(perms)


class APITokenAuthMiddleware:
    def __init__(self, app, perms: str | Sequence[str]) -> None:
        self.app = app
        if isinstance(perms, str):
            self.perms = (perms,)
        else:
            self.perms = tuple(perms)

    async def __call__(self, scope, receive, send):
        ENDPOINT = scope["path"]
        logger.info("Incoming websocket connection on %s", ENDPOINT)

        headers = dict(scope["headers"])
        headers = {k.decode(): v.decode() for k, v in headers.items()}

        # Extract any cookies
        raw_cookies = headers.get("cookies")
        if raw_cookies:
            cookies = parse_cookie(raw_cookies)
        else:
            cookies = {}

        # Try to authenticate the user if they include a sessionid cookie
        session_id = cookies.get("sessionid")
        if session_id:
            session = SessionStore(session_id)
            await database_sync_to_async(session.load)()
            user_id = await database_sync_to_async(session.get)("_auth_user_id")
            try:
                user = await database_sync_to_async(User.objects.get)(pk=user_id)
            except User.DoesNotExist:
                logger.error(
                    "Could not find a Django User account with user_id=%s", user_id
                )
                user = None
            scope["user"] = user
        # Otherwise try to use their API key
        else:
            try:
                header_name, raw_api_key = headers.get("authorization", "").split(
                    maxsplit=1
                )
                if not header_name.upper().strip() in BEARER:
                    raw_api_key = None
            except (KeyError, ValueError):
                raw_api_key = None
                logger.info(f"Couldn't parse API key {raw_api_key=}")

            try:
                # Retrieve the user to use the normal authentication system
                # to include their permissions.
                scope["user"], scope["mobile_device"] = await get_user(raw_api_key)
            except (DjangoAPIKey.DoesNotExist, ValueError, TypeError):
                scope["user"] = None
                logger.info(
                    "API key not associated with a user, denying connection to %s",
                    ENDPOINT,
                )
                denier = WebsocketDenier()
                return await denier(scope, receive, send)

        if not await has_perms(scope, self.perms):
            logger.warning(
                "User %s does not have permission to view %s", scope["user"], ENDPOINT
            )
            denier = WebsocketDenier()
            return await denier(scope, receive, send)

        return await self.app(scope, receive, send)


@dataclass
class RconResponse:
    result: Any = None
    command: str = None
    arguments: dict = None
    failed: bool = True
    error: str = None
    forwards_results: Any = None
    version: str | None = None

    def to_dict(self):
        # asdict() cannot convert a Django QueryDict properly
        if isinstance(self.arguments, QueryDict):
            self.arguments = self.arguments.dict()
        return asdict(self)


class RconJsonResponse(HttpResponse):
    """Similar to JsonResponse but use orjson for speed + automatically serialize pydantic objects"""

    @staticmethod
    def _orjson_dump_pydantic(o):
        if isinstance(o, pydantic.BaseModel):
            return o.model_dump()
        elif isinstance(o, datetime.timedelta):
            return o.total_seconds()
        elif isinstance(o, set):
            return [val for val in sorted(o)]
        else:
            raise ValueError(f"Cannot serialize {o}, {type(o)} to JSON")

    def __init__(self, data, **kwargs):
        data = orjson.dumps(
            data,
            default=RconJsonResponse._orjson_dump_pydantic,
            option=orjson.OPT_NON_STR_KEYS,
        )
        kwargs.setdefault("content_type", "application/json")
        super().__init__(content=data, **kwargs)


def api_response(*args, **kwargs):
    status_code = kwargs.pop("status_code", 200)
    return RconJsonResponse(
        RconResponse(version=TAG_VERSION, *args, **kwargs).to_dict(), status=status_code
    )


def api_csv_response(content, name, header):
    # TODO Probably want to put command name, etc. in this like the other
    # RCON response methods
    response = HttpResponse(
        content_type="text/csv",
    )
    response["Content-Disposition"] = 'attachment; filename="%s"' % name

    writer = csv.DictWriter(response, fieldnames=header, dialect="excel")
    writer.writerow({k: k for k in header})
    writer.writerows(content)

    return response


@csrf_exempt
@require_http_methods(["POST"])
@require_content_type()
@ratelimit(
    group="login-account",
    key=login_account_rate_limit_key,
    rate="10/15m",
    block=True,
)
@ratelimit(
    group="login-client",
    key=request_rate_limit_key,
    rate="30/15m",
    block=True,
)
def do_login(request):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        logger.debug("Login attempt without data")
        raise PermissionDenied("No data")

    name = data.get("username")
    password = data.get("password")
    try:
        user = authenticate(request, username=name, password=password)
        if user is not None:
            login(request, user)
            # The frontend uses this token for subsequent session-authenticated
            # writes. get_token() marks the CSRF cookie for the response.
            get_token(request)
            logger.info("Successful login: %s", name)
            return api_response(
                result=True, command="login", arguments=name, failed=False
            )
        else:
            logger.warning("Failed login attempt %s", name)
            raise PermissionDenied("Invalid login")
    except PermissionDenied:
        logger.warning("Failed login attempt %s", name)
        return api_response(command="login", arguments=name, status_code=401)


@ttl_cache(60 * 60, cache_falsy=False)
def get_moderators_accounts() -> list[tuple[str, str]]:
    """Return all active Django accounts associated with a player ID"""
    return [
        (u.user.username, u.steam_id_64)
        for u in SteamPlayer.objects.all()
        if u.user.is_active
    ]


@csrf_exempt
@require_http_methods(["GET"])
@ratelimit(key=request_rate_limit_key, rate="180/m", block=True)
def is_logged_in(request):
    is_auth = request.user.is_authenticated
    if is_auth:
        try:
            player_id = None
            try:
                player_id = request.user.steamplayer.steam_id_64
            except:
                logger.warning("%s's player ID is not set", request.user.username)
            try:
                heartbeat(request.user.username, player_id)
            except:
                logger.exception("Unable to register mods")
        except:
            logger.exception("Can't record heartbeat")

    res = dict(authenticated=is_auth)
    return api_response(result=res, command="is_logged_in", failed=False)


@csrf_exempt
@require_http_methods(["GET", "POST"])
@ratelimit(key=request_rate_limit_key, rate="30/m", block=True)
def do_logout(request):
    logout(request)
    return api_response(result=True, command="logout", failed=False)


def check_api_key(request):
    # Extract the header and bearer key if present, otherwise fall back on
    # requiring the user to be logged in
    try:
        header_name, raw_api_key = request.META[HTTP_AUTHORIZATION_HEADER].split(
            maxsplit=1
        )
        if not header_name.upper().strip() in BEARER:
            raw_api_key = None
    except (KeyError, ValueError):
        raw_api_key = None

    try:
        # Retrieve the user to use the normal authentication system and keep
        # a device reference for mobile audit records.
        request.user, request.mobile_device = authenticate_bearer_token(raw_api_key)
    except DjangoAPIKey.DoesNotExist:
        pass


def login_required():
    """Flag this endpoint as one that requires the user
    to be logged in.
    """

    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            # Check if API-Key is used
            check_api_key(request)

            if not request.user.is_authenticated:
                return api_response(
                    command=request.path,
                    error="You must be logged in to use this",
                    failed=True,
                    status_code=401,
                )

            try:
                return func(request, *args, **kwargs)
            except PermissionDenied as e:
                return api_response(
                    command=request.path,
                    error="You do not have the required permissions to use this",
                    failed=True,
                    status_code=403,
                )
            except Exception as e:
                logger.exception("Unexpected error in %s", func.__name__)
                return api_response(
                    command=request.path, error=repr(e), failed=True, status_code=500
                )

        return wrapper

    return decorator


def staff_required(request):
    if request.user.is_authenticated and request.user.is_staff:
        return True
    return False


def stats_login_required(func):
    config = RconServerSettingsUserConfig.load_from_db()

    if not config.lock_stats_api:
        return func

    @wraps(func)
    def wrapper(request, *args, **kwargs):
        # Check if API-Key is used
        check_api_key(request)

        if not request.user.is_authenticated:
            return api_response(
                command=request.path,
                error="You must be logged in to use this",
                failed=True,
                status_code=401,
            )
        try:
            return func(request, *args, **kwargs)
        except Exception as e:
            logger.exception("Unexpected error in %s", func.__name__)
            return api_response(
                command=request.path, error=repr(e), failed=True, status_code=500
            )

    return wrapper


@csrf_exempt
@login_required()
@require_http_methods(["GET"])
def get_own_user_permissions(request):
    command_name = "get_own_user_permissions"

    unique_permissions: set[tuple[str, str]] = set()
    trimmed_groups: list[DjangoGroup] = []

    permissions = Permission.objects.filter(user=request.user)
    for p in permissions.values():
        unique_permissions.add((p["codename"], p["name"]))

    groups = Group.objects.filter(user=request.user)
    for g in groups:
        trimmed_groups.append({"name": g.name})
        for p in g.permissions.values():
            unique_permissions.add((p["codename"], p["name"]))

    trimmed_permissions: list[DjangoPermission] = [
        {
            "permission": permission,
            "description": description,
        }
        for permission, description in unique_permissions
    ]
    try:
        player_id = request.user.steamplayer.steam_id_64
    except SteamPlayer.DoesNotExist as e:
        logger.info(f"{request.user} does not have a player ID set on the admin site")
        player_id = None

    result: DjangoUserPermissions = {
        "is_superuser": request.user.is_superuser,
        "user_name": request.user.get_username(),
        "player_id": player_id,
        "permissions": trimmed_permissions,
        "groups": trimmed_groups,
    }

    return api_response(
        command=command_name,
        result=result,
        failed=False,
    )
