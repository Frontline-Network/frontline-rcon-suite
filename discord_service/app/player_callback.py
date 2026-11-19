"""Trusted direct-origin routing for player panels on mixed-version installations."""

from urllib.parse import urlsplit

from .config import get_settings
from .player_models import PlayerPanelCallback
from .security import decrypt


def allowed_origin(value):
    # Panel callbacks are always direct HTTPS origins. An empty allowlist is
    # valid for historical pairing but never opts an operator into overrides.
    try:
        parsed = urlsplit(value)
        if (
            not parsed.hostname
            or parsed.scheme != "https"
            or parsed.username is not None
            or parsed.password is not None
            or parsed.port not in {None, 443}
            or parsed.path not in {"", "/"}
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError("Expected a direct HTTPS origin")
        host = parsed.hostname.lower()
        if value.lower() not in {
            f"https://{host}",
            f"https://{host}/",
            f"https://{host}:443",
            f"https://{host}:443/",
        }:
            raise ValueError("Invalid origin")
    except (TypeError, AttributeError, ValueError) as exc:
        raise ValueError("Invalid player callback origin") from exc
    if host not in get_settings().crcon_host_allowlist():
        raise ValueError("Player callback host must be explicitly allowed")
    origin = f"https://{host}"
    from .main import _validate_crcon_callback

    # Repeat the same public resolution checks on every use, incl. after a DNS change.
    _validate_crcon_callback(origin + "/api/discord/v1/pairings/complete")
    if urlsplit(get_settings().callback_broker_url).hostname == host:
        raise ValueError("Player override must target a direct RCON origin")
    return origin


def effective_origin(session, panel, integration):
    override = session.get(PlayerPanelCallback, panel.id)
    if not override:
        return integration.crcon_base_url
    if (override.installation_id, override.guild_id, override.server_number) != (
        integration.installation_id,
        integration.guild_id,
        panel.server_number,
    ):
        raise ValueError("Player callback pairing has changed")
    return allowed_origin(override.origin)


def verify_and_bind(session, panel, integration, origin):
    from .main import _crcon_post

    origin = allowed_origin(origin)
    headers = {
        "Authorization": f"Bearer {decrypt(integration.action_capability_ciphertext)}"
    }
    ping = _crcon_post(
        origin + "/api/discord/v1/diagnostics/ping",
        headers=headers,
        json={"installation_id": integration.installation_id},
        timeout=8,
        follow_redirects=False,
    )
    ping.raise_for_status()
    if (
        ping.json().get("result", {}).get("installation_id")
        != integration.installation_id
    ):
        raise ValueError("Player callback did not confirm installation")
    # A successful list response verifies the guild, active player feature and
    # server profile. The bot's own account is used; no player's cases are queried.
    bot_id = str(get_settings().discord_application_id or "")
    if not bot_id.isascii() or not bot_id.isdecimal() or len(bot_id) > 22:
        raise ValueError("A configured Discord application ID is required")
    probe = _crcon_post(
        origin + "/api/discord/v1/player-reports",
        headers=headers,
        json={
            "installation_id": integration.installation_id,
            "guild_id": panel.guild_id,
            "server_number": panel.server_number,
            "channel_id": panel.channel_id,
            "discord_user_id": bot_id,
            "interaction_id": bot_id,
            "operation": "list",
            "arguments": {},
        },
        timeout=8,
        follow_redirects=False,
    )
    probe.raise_for_status()
    body = probe.json()
    if body.get("failed") or not isinstance(body.get("result", {}).get("content"), str):
        raise ValueError("Player callback did not confirm the panel")
    session.merge(
        PlayerPanelCallback(
            panel_id=panel.id,
            installation_id=integration.installation_id,
            guild_id=panel.guild_id,
            server_number=panel.server_number,
            origin=origin,
        )
    )
