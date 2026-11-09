"""Server-local report automation; no direct action or arbitrary model endpoint."""

import json

from django.urls import path

from rcon import report_admin as service
from rcon.models import MessageTemplate
from rcon.user_config.report_admin import ReportAdminUserConfig as Config
from sqlalchemy import select

from .leadership_vote import endpoint, audit, KICK

MANAGE = "api.can_manage_discord_report_bot"


@endpoint([MANAGE], {"GET", "PUT"})
def configuration(request, server):
    if request.method == "PUT":
        if request.content_type != "application/json" or len(request.body) > 4096:
            raise ValueError("Small JSON configuration required")
        cfg = Config.model_validate(json.loads(request.body))
        if cfg.enabled and not request.user.has_perm(KICK):
            raise PermissionError("Automatic kicks require kick permission")
        service.configure(server, cfg, request.user.username)
        audit(request, "report_admin_configure", server, cfg.model_dump())
    with service.enter_session() as sess:
        return {
            "config": service.config(sess, server).model_dump(),
            "can_enable": request.user.has_perm(KICK),
            "teamkill_policy": "individual_case",
            "teamkill_grace_seconds": 60,
            "context_window_seconds": 900,
            "cheat_sanctions": "manual_only",
            "manual_cheat_ban_hours": 24,
            "templates": [
                {"id": row.id, "title": row.title}
                for row in sess.scalars(
                    select(MessageTemplate)
                    .where(MessageTemplate.category == "REASON")
                    .order_by(MessageTemplate.id)
                )
            ],
        }


urlpatterns = [path("config", configuration)]
