"""Minimal CLI used by long-running Supervisor services.

The general-purpose CLI imports every administrative command and dynamically
exposes the full RCON API. Long-running services only need one command each, so
their imports stay local to avoid retaining unrelated modules for their entire
lifetime.
"""

import logging
import sys

import click

logger = logging.getLogger(__name__)


@click.group()
def cli():
    pass


@cli.command(name="live_stats_loop")
def run_stats_loop():
    from rcon.player_stats import live_stats_loop

    try:
        live_stats_loop()
    except KeyboardInterrupt:
        sys.exit(0)
    except Exception:
        logger.exception("Stats loop stopped")
        sys.exit(1)


@cli.command(name="autobalancer")
def run_autobalancer():
    from rcon.autobalancer import service

    try:
        service.run()
    except KeyboardInterrupt:
        sys.exit(0)
    except Exception:
        logger.exception("Autobalancer stopped")
        sys.exit(1)


@cli.command(name="log_loop")
def run_log_loop():
    from rcon.cache_utils import invalidates
    from rcon.discord_chat import get_handler
    from rcon.log_hooks import register_log_hooks
    from rcon.logs.loop import LogLoop, load_generic_hooks

    register_log_hooks()
    # Invalidate the cache on startup so it always loads user settings since
    # they might have been changed through the UI or the general-purpose CLI.
    with invalidates(load_generic_hooks, get_handler):
        try:
            LogLoop().run()
        except Exception:
            logger.exception("Chat recorder stopped")
            sys.exit(1)


@cli.command(name="log_stream")
def run_log_stream():
    from rcon.logs.stream import LogStream
    from rcon.user_config.log_stream import LogStreamUserConfig

    try:
        config = LogStreamUserConfig.load_from_db()
        stream = LogStream()
        stream.clear()
        if config.enabled:
            stream.run()
    except Exception:
        logger.exception("Log stream stopped")
        sys.exit(1)


@cli.command(name="broadcast_loop")
def run_broadcast_loop():
    from rcon import broadcast

    broadcast.run()


@cli.command(name="campaign_message_loop")
def run_campaign_message_loop():
    from rcon import campaign_delivery

    campaign_delivery.run()


@cli.command(name="auto_settings")
def auto_settings_loop():
    from rcon import auto_settings

    auto_settings.run()


@cli.command(name="routines")
def run_routines():
    from rcon import routines

    routines.run()


@cli.command(name="combined_runtime")
def run_combined_runtime():
    from rcon import supervisor_runtime

    supervisor_runtime.run()


@cli.command(name="supervisor_runtime_mode")
@click.argument("mode", type=click.Choice(["split", "shared"]))
def set_supervisor_runtime_mode(mode):
    from rcon import supervisor_runtime

    supervisor_runtime.mark_runtime_mode(mode)


@cli.command(name="expiring_vips")
def run_expiring_vips():
    from rcon.expiring_vips import service

    service.run()


@cli.command(name="seed_vip")
def run_seed_vip():
    from rcon.seed_vip import service

    try:
        service.run()
    except Exception:
        logger.exception("seed VIP stopped")
        sys.exit(1)


@cli.command(name="watch_killrate")
def watch_killrate():
    from rcon import watch_killrate as service

    try:
        service.run()
    except Exception:
        logger.exception("Watch_KillRate stopped")
        sys.exit(1)


@cli.command(name="automod")
def run_automod():
    from rcon.automods import automod

    automod.run()


@cli.command(name="blacklists")
def run_blacklists():
    from rcon.blacklist import BlacklistCommandHandler

    BlacklistCommandHandler().run()


@cli.command(name="log_recorder")
@click.option("-t", "--frequency-min", required=False)
@click.option("-i", "--interval", default=10)
@click.option("-n", "--now", is_flag=True)
def run_log_recorder(interval, frequency_min, now):
    from rcon.logs.recorder import LogRecorder

    if frequency_min and interval:
        raise Exception("Cannot have frequency-min and interval at the same time")
    if frequency_min:
        interval = frequency_min * 60
    LogRecorder(interval).run(run_immediately=now)
