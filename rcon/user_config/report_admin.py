"""Opt-in server-local rules, with separately selected semantic interpretation."""

import logging
from typing import ClassVar, Literal

from pydantic import ConfigDict, Field

from rcon.user_config.utils import BaseUserConfig


class ReportAdminUserConfig(BaseUserConfig):
    MISSING_CONFIG_LOG_LEVEL: ClassVar[int] = logging.DEBUG
    model_config = ConfigDict(extra="forbid", strict=True)
    enabled: bool = False
    mode: Literal["dry_run", "active"] = "dry_run"
    reason_mode: Literal["rules", "ai"] = "rules"
    communication: bool = True
    communication_squad_members: bool = False
    teamkills: bool = True
    cheating: bool = False  # Explicit opt-in for new review/receipt behavior.
    allow_self_reports: bool = False
    communication_template_id: int | None = Field(default=None, gt=0)
    teamkills_template_id: int | None = Field(default=None, gt=0)

    @staticmethod
    def save_to_db(values, dry_run=False):
        config = ReportAdminUserConfig.model_validate(values)
        if not dry_run:
            from rcon.report_admin import configure
            from rcon.utils import get_server_number

            configure(int(get_server_number()), config)
