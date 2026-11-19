"""Publish or update the guild's mobile report panel for one RCON server."""

import argparse
import hashlib


from sqlalchemy import select

from .db import SessionLocal
from .discord_client import DiscordClient
from .models import Integration
from .player_callback import verify_and_bind
from .player_models import PlayerPanel, PlayerPanelCallback
from .player_panel import SNOWFLAKE, public_message


def publish(
    session,
    installation_id,
    server,
    guild,
    channel,
    discord,
    *,
    callback_origin=None,
    use_installation_callback=False,
):
    if (
        not SNOWFLAKE.fullmatch(guild)
        or not SNOWFLAKE.fullmatch(channel)
        or not 1 <= server <= 10000
    ):
        raise ValueError("Invalid server, guild, or channel")
    integration = session.get(Integration, installation_id, with_for_update=True)
    if not integration or not integration.enabled or integration.guild_id != guild:
        raise ValueError("Installation is not paired to this guild")
    if discord.settings.dry_run or not discord.settings.discord_bot_token:
        raise ValueError("Publishing requires a live Discord bot")
    discord.validate_channel(channel, guild)
    panel = session.scalar(
        select(PlayerPanel).where(
            PlayerPanel.installation_id == installation_id,
            PlayerPanel.server_number == server,
        )
    )
    if panel and (panel.channel_id != channel or panel.guild_id != guild):
        raise ValueError(
            "A panel for this server is already bound to a different channel"
        )
    if not panel:
        panel = PlayerPanel(
            id=hashlib.sha256(
                f"{installation_id}:{server}:{guild}:{channel}".encode()
            ).hexdigest()[:32],
            installation_id=installation_id,
            server_number=server,
            guild_id=guild,
            channel_id=channel,
        )
        session.add(panel)
        session.flush()
    if callback_origin is not None and use_installation_callback:
        raise ValueError("Choose only one callback setting")
    if callback_origin is not None:
        verify_and_bind(session, panel, integration, callback_origin)
    elif use_installation_callback:
        prior = session.get(PlayerPanelCallback, panel.id)
        if prior is not None:
            session.delete(prior)
    payload = public_message(panel)
    if not panel.message_id:
        payload.update(
            nonce=hashlib.sha256(
                f"{installation_id}:{server}:{guild}:{channel}".encode()
            ).hexdigest()[:24],
            enforce_nonce=True,
        )
    panel.message_id = discord.upsert(channel, payload, panel.message_id)
    session.commit()
    return panel.message_id


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--installation", required=True)
    parser.add_argument("--server", type=int, required=True)
    parser.add_argument("--guild", required=True)
    parser.add_argument("--channel", required=True)
    routing = parser.add_mutually_exclusive_group()
    routing.add_argument(
        "--callback-origin",
        help="Use an explicitly allowed HTTPS origin for this panel",
    )
    routing.add_argument(
        "--use-installation-callback",
        action="store_true",
        help="Clear the panel override",
    )
    args = parser.parse_args()
    with SessionLocal() as session:
        result = publish(
            session,
            args.installation,
            args.server,
            args.guild,
            args.channel,
            DiscordClient(),
            callback_origin=args.callback_origin,
            use_installation_callback=args.use_installation_callback,
        )
    print(f"https://discord.com/channels/{args.guild}/{args.channel}/{result}")


if __name__ == "__main__":
    main()
