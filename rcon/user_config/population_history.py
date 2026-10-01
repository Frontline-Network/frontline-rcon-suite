"""Collection settings, persisted per server through the existing settings CLI."""

import logging
from typing import ClassVar, Literal

from pydantic import ConfigDict, Field

from rcon.user_config.utils import BaseUserConfig


class PopulationHistoryUserConfig(BaseUserConfig):
    MISSING_CONFIG_LOG_LEVEL: ClassVar[int] = logging.DEBUG
    model_config = ConfigDict(extra="forbid", strict=True)

    enabled: bool = True
    interval_seconds: Literal[15, 30, 60] = 30
    retention_days: int = Field(default=60, ge=1, le=365)
