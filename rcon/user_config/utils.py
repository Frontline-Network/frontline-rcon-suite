import logging
import os
import threading
import time
from copy import deepcopy
from typing import Any, ClassVar, Iterable, Self, Type

import pydantic
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from rcon.models import UserConfig, enter_session
from rcon.utils import get_server_number

logger = logging.getLogger(__name__)

USER_CONFIG_KEY_FORMAT = "{server}_{cls_name}"
DISCORD_AUDIT_FORMAT = "changed values: `{differences}`"
USER_CONFIG_CACHE_TTL_SECONDS = 2

_USER_CONFIG_CACHE: dict[str, tuple[float, Any]] = {}
_USER_CONFIG_CACHE_LOCK = threading.RLock()
_USER_CONFIG_CACHE_GENERATION = 0


# Sourced without modification from https://stackoverflow.com/a/17246726
def all_subclasses(cls):
    return set(cls.__subclasses__()).union(
        [s for c in cls.__subclasses__() for s in all_subclasses(c)]
    )


def key_check(
    mandatory_keys: frozenset, optional_keys: frozenset, provided_keys: Iterable[str]
):
    missing_keys = mandatory_keys - set(provided_keys)
    extra_keys = set(provided_keys) - mandatory_keys - optional_keys
    if extra_keys or missing_keys:
        raise InvalidKeysConfigurationError(
            missing_keys=set(missing_keys),
            extra_keys=set(extra_keys),
            mandatory_keys=set(mandatory_keys),
            provided_keys=set(provided_keys),
        )


class _listType(pydantic.BaseModel):
    """Used to raise ValidationErrors when not passed a list"""

    values: list[Any]


class InvalidKeysConfigurationError(Exception):
    """Raised for user configs that have extra or missing keys"""

    def __init__(
        self,
        missing_keys: set[str] = set(),
        extra_keys: set[str] = set(),
        mandatory_keys: set[str] = set(),
        provided_keys: set[str] = set(),
        *args: object,
    ) -> None:
        super().__init__(*args)
        self.missing_keys = missing_keys
        self.extra_keys = extra_keys
        self.mandatory_keys = mandatory_keys
        self.provided_keys = provided_keys

    def __str__(self) -> str:
        return self.__repr__()

    def __repr__(self) -> str:
        return f"missing keys=({', '.join(self.missing_keys)}) | Extra keys = ({', '.join(self.extra_keys)}) | Mandatory keys=({', '.join(self.mandatory_keys)}) | Provided keys=({', '.join(self.provided_keys)})"

    def asdict(self) -> dict[str, Any]:
        return {
            "type": InvalidKeysConfigurationError.__name__,
            "missing_keys": sorted([k for k in self.missing_keys]),
            "extra_keys": sorted([k for k in self.extra_keys]),
            "mandatory_keys": sorted([k for k in self.mandatory_keys]),
            "provided_keys": sorted([k for k in self.provided_keys]),
        }


class BaseUserConfig(pydantic.BaseModel):
    """The interface UI config settings should adhere to in addition to pydantic.BaseModel"""

    # Most configurations are seeded at backend startup, so a missing record
    # normally signals an operational problem. Legacy, optional configurations
    # may lower this level when their default is an expected migration fallback.
    MISSING_CONFIG_LOG_LEVEL: ClassVar[int] = logging.ERROR

    @classmethod
    def KEY(cls) -> str:
        """The database primary key for a setting"""
        return USER_CONFIG_KEY_FORMAT.format(
            server=get_server_number(), cls_name=cls.__name__
        )

    @classmethod
    def load_from_db(cls, default_on_validation_error: bool = True) -> Self:
        # This should never happen in production, but allows tests to run
        if not os.getenv("HLL_DB_URL"):
            logger.warning(f"HLL_DB_URL not set, returning a default instance")
            return cls()

        # If the database returns no value, fall back to a default model instance,
        # but do not persist it and risk overwriting legitimate settings.
        conf = _get_cached_user_config(cls.KEY(), default=None)
        if conf is not None:
            try:
                return cls.model_validate(conf)
            except pydantic.ValidationError as e:
                if default_on_validation_error:
                    logger.error(
                        "Error loading %s; returning defaults (%s validation errors)",
                        cls.KEY(), e.error_count(),
                    )
                    return cls()
                else:
                    raise
        else:
            # This shouldn't happen because we seed the database on startup if the
            # records don't exist, if someone has manually edited their database that
            # is on them, previously we would not seed defaults and create/persist an
            # instance if `get_user_config` did not find a record for any reason.
            # This was resetting peoples legitimate configs in some scenarios, particularly
            # when containers were being created/torn down and a service or the backend queried
            # a model and postgres was unavailable.
            # Now models are only persisted to the database when they're either explicitly seeded
            # during backend startup, or if the `save_to_db` method is explicitly called, for
            # instance through the API, or CLI
            logger.log(
                cls.MISSING_CONFIG_LOG_LEVEL,
                "%s not found, returning defaults",
                cls.KEY(),
            )

        return cls()

    @staticmethod
    def save_to_db(values: dict[str, Any], dry_run: bool) -> None:
        raise NotImplementedError

    @classmethod
    def seed_db(cls, sess: Session):
        _set_default(sess, key=cls.KEY(), val=cls())


def _get_conf(sess, key):
    try:
        return sess.query(UserConfig).filter(UserConfig.key == key).one_or_none()
    except SQLAlchemyError:
        # A database failure is not the same as an absent configuration.
        # Propagate it so callers do not enable default actions by accident.
        sess.rollback()
        raise


def get_user_config(key: str, default=None) -> dict[str, Any] | Any | None:
    # logger.debug("Getting user config for %s", key)
    with enter_session() as sess:
        res = _get_conf(sess, key)
        res = res.value if res else default
        # logger.debug("User config for %s is %s", key, res)
        return res


def _get_cached_user_config(key: str, default=None) -> dict[str, Any] | Any | None:
    """Reuse hot-loop config reads briefly without delaying updates for long.

    The cache is intentionally process-local. Configuration writes invalidate the
    current process immediately, while independent supervisor processes observe a
    change after at most ``USER_CONFIG_CACHE_TTL_SECONDS``. Values are copied on
    both ingress and egress so callers cannot mutate the cached JSON document.
    """

    now = time.monotonic()
    with _USER_CONFIG_CACHE_LOCK:
        cached = _USER_CONFIG_CACHE.get(key)
        if cached is not None:
            expires_at, value = cached
            if expires_at > now:
                return deepcopy(value)
            _USER_CONFIG_CACHE.pop(key, None)
        generation = _USER_CONFIG_CACHE_GENERATION

    value = get_user_config(key, default=default)
    with _USER_CONFIG_CACHE_LOCK:
        if generation == _USER_CONFIG_CACHE_GENERATION:
            _USER_CONFIG_CACHE[key] = (
                time.monotonic() + USER_CONFIG_CACHE_TTL_SECONDS,
                deepcopy(value),
            )
    return value


def _invalidate_user_config_cache(key: str) -> None:
    global _USER_CONFIG_CACHE_GENERATION
    with _USER_CONFIG_CACHE_LOCK:
        _USER_CONFIG_CACHE_GENERATION += 1
        _USER_CONFIG_CACHE.pop(key, None)


def _clear_user_config_cache() -> None:
    """Clear the process-local cache for tests and maintenance utilities."""

    global _USER_CONFIG_CACHE_GENERATION
    with _USER_CONFIG_CACHE_LOCK:
        _USER_CONFIG_CACHE_GENERATION += 1
        _USER_CONFIG_CACHE.clear()


def _add_conf(sess, key, val):
    try:
        return sess.add(UserConfig(key=key, value=val))
    except SQLAlchemyError as e:
        # Don't let a failed transaction block model creation
        # the session context manager will handle this
        sess.rollback()
        return None


def _remove_conf(sess, key):
    conf = _get_conf(sess, key)

    if conf is not None:
        logger.info("Deleting %s", key)
        sess.delete(conf)
        sess.commit()
        _invalidate_user_config_cache(key)


def _set_default(sess: Session, key: str, val: dict[str, Any] | BaseUserConfig):
    if isinstance(val, BaseUserConfig):
        val = val.model_dump()

    if _get_conf(sess, key) is None:
        logger.info("Seeding default values for %s", key)
        _add_conf(sess, key, val)
        _invalidate_user_config_cache(key)
    return val


def set_user_config(key: str, object_: dict[str, Any] | BaseUserConfig):
    if isinstance(object_, BaseUserConfig):
        object_ = object_.model_dump()

    logger.debug("Setting user config for %s", key)
    _invalidate_user_config_cache(key)
    try:
        with enter_session() as sess:
            from rcon.leadership_vote.storage import guard_command_config
            guard_command_config(sess, key, object_)
            conf = _get_conf(sess, key)
            if conf is None:
                _add_conf(sess, key, object_)
            else:
                conf.value = object_
    finally:
        _invalidate_user_config_cache(key)


def validate_user_config(
    model: Type[BaseUserConfig],
    data: dict[str, Any] | BaseUserConfig,
    dry_run: bool = True,
    reset_to_default: bool = False,
) -> bool:
    if reset_to_default and not dry_run:
        # Reject invalid input before changing persisted settings.
        model.save_to_db(values=data, dry_run=True)
        default = model()
        set_user_config(default.KEY(), default)

    model.save_to_db(values=data, dry_run=dry_run)
    return True


def mask_sensitive_data(
    values: dict[str, Any],
    sensitive_keys: set[str] = {
        "discord_webhook_url",
        "username",
        "password",
        "url",
        "webhook_urls",
        "api_key",
    },
    masked_value: str = "***",
) -> None:
    """Replace the value of any dict key in sensitive_keys with masked_value"""
    if not isinstance(values, dict):
        return

    for k, v in values.items():
        if isinstance(v, dict):
            mask_sensitive_data(values[k], sensitive_keys=sensitive_keys)
        elif isinstance(v, list):
            for ele in v:
                mask_sensitive_data(ele, sensitive_keys=sensitive_keys)

        if k in sensitive_keys:
            values[k] = masked_value
