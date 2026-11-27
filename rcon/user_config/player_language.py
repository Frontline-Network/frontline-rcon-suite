"""Recipient language routing; opt-in preserves upgraded installations' texts."""
import logging
from pydantic import ConfigDict
from rcon.user_config.utils import BaseUserConfig, set_user_config


class PlayerLanguageUserConfig(BaseUserConfig):
    model_config = ConfigDict(extra="forbid")
    MISSING_CONFIG_LOG_LEVEL = logging.DEBUG
    enabled: bool = False

    @classmethod
    def save_to_db(cls, values, dry_run=False):
        config = cls.model_validate(values)
        if not dry_run:
            set_user_config(cls.KEY(), config)

