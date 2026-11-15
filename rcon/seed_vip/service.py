import sys
from collections import defaultdict
from datetime import datetime, timezone
from logging import getLogger
import humanize

import discord
from rcon.api_commands import get_rcon_api
from rcon.seed_vip import journal
from rcon.seed_vip.notifications import RETRY_SECONDS, NotificationOutbox
from rcon.service_runtime import stopping, wait
from rcon.seed_vip.utils import (
    calc_vip_expiration_timestamp,
    collect_steam_ids,
    filter_indefinite_vip_steam_ids,
    format_vip_reward_name,
    get_gamestate,
    get_next_player_bucket,
    get_online_players,
    get_vips,
    is_seeded,
    make_seed_announcement_embed,
    message_players,
)
from rcon.user_config.seed_vip import SeedVIPUserConfig
from rcon.utils import get_server_number

logger = getLogger(__name__)


def send_seed_hooks(hooks, embed):
    """Isolate webhook failures from the seed transition and other hooks."""
    for hook in hooks:
        try:
            discord.SyncWebhook.from_url(url=str(hook.url)).send(embed=embed)
        except Exception as exc:
            # HTTP exception text and tracebacks can contain webhook tokens.
            logger.warning("Seed VIP webhook delivery failed (%s)", type(exc).__name__)


def get_server_snapshot(rcon_api):
    """Read the RCON data needed by one loop without stopping the service."""
    try:
        online_players = get_online_players(rcon=rcon_api)
        gamestate = get_gamestate(rcon=rcon_api)
    except Exception as e:
        logger.warning(
            "Unable to query HLL RCON for Seed VIP (%s); retrying on the next poll",
            type(e).__name__,
        )
        return None

    if online_players is None or gamestate is None:
        logger.warning("HLL RCON returned an incomplete Seed VIP snapshot; retrying")
        return None

    return online_players, gamestate


def recover_rewards(rcon_api, config, outbox, server_number):
    """Resume each durable grant independently, without replaying uncertain writes."""
    try:
        grant_ids = journal.pending(server_number)
    except Exception as exc:
        logger.error("Unable to load Seed VIP grants (%s)", type(exc).__name__)
        return
    for grant_id in grant_ids:
        try:
            result = journal.deliver(rcon_api, server_number=server_number, grant_id=grant_id)
            if result == "confirmed":
                player_id, target, _ = journal.grant_info(server_number, grant_id)
                message_players(rcon=rcon_api, config=config,
                                message=config.player_messages.reward_player_message,
                                steam_ids={player_id}, expiration_timestamps={player_id: target},
                                outbox=outbox)
            elif result in {"review", "rejected"}:
                logger.warning("Seed VIP grant %s requires attention: %s", grant_id, result)
        except Exception as exc:
            # A prepared grant will be reconciled read-only on the next poll.
            logger.warning("Seed VIP grant %s deferred (%s)", grant_id, type(exc).__name__)


def run(stop_event=None):
    try:
        config = SeedVIPUserConfig.load_from_db()
    except Exception as exc:
        raise RuntimeError(f"Seed VIP configuration unavailable ({type(exc).__name__})") from None
    current_lang = config.language

    rcon_api = get_rcon_api()
    outbox = NotificationOutbox()
    server_number = int(get_server_number())

    prev_announced_bucket: int = 0
    player_buckets = config.player_announce_thresholds
    if player_buckets:
        next_player_bucket = player_buckets[0]
    else:
        next_player_bucket = None
    last_bucket_announced = False
    disabled_logged = False

    try:
        while not stopping(stop_event):
            # Reload the config each loop to catch changes to the config
            config = SeedVIPUserConfig.load_from_db()

            if not config.enabled:
                outbox.clear()
                if not disabled_logged:
                    logger.info("Seed VIP is not enabled")
                    disabled_logged = True
                if stop_event is None:
                    break
                if wait(stop_event, 5):
                    return
                continue
            disabled_logged = False

            if config.dry_run:
                outbox.clear()
                pending_notices = False
            else:
                pending_notices = outbox.flush(rcon_api)
                recover_rewards(rcon_api, config, outbox, server_number)
                pending_notices = outbox.flush(rcon_api) or pending_notices

            try:
                if current_lang != config.language:
                    logger.info(f"Deactivating language={current_lang}")
                    humanize.deactivate()

                if config.language:
                    # The language to translate to if using the `nice_time_delta` and `nice_expiration_date` settings
                    # Any valid language code shoud work, look here for examples: https://gist.github.com/jacobbubu/1836273
                    current_lang = config.language
                    humanize.activate(config.language)
                    logger.info(f"Activated language={config.language}")
            except FileNotFoundError as e:
                logger.exception(e)
                logger.error(
                    f"Unable to activate language={config.language}, defaulting to English"
                )

            snapshot = get_server_snapshot(rcon_api)
            if snapshot is None:
                if wait(stop_event, config.poll_time_seeding):
                    return
                continue

            online_players, gamestate = snapshot
            total_players = (
                gamestate["num_allied_players"] + gamestate["num_axis_players"]
            )
            eligible_ids = collect_steam_ids(
                config=config,
                players=online_players,
                cum_steam_ids=set(),
            )
            eligible = {
                p.player_id: p.name for p in online_players.players.values()
                if p.player_id in eligible_ids
            }
            try:
                observation = journal.observe(
                    server_number=server_number,
                    preview=config.dry_run,
                    seeded=is_seeded(config=config, gamestate=gamestate),
                    player_count=total_players,
                    eligible=eligible,
                    online_when_seeded=config.requirements.online_when_seeded,
                    buffer=config.requirements.buffer.as_timedelta,
                    reward_seconds=config.reward.timeframe.as_timedelta.total_seconds(),
                    cumulative=config.reward.cumulative,
                    reward_name=lambda name: format_vip_reward_name(
                        name, config.reward.player_name_format_not_current_vip
                    ),
                    now=datetime.now(timezone.utc),
                )
            except Exception as exc:
                # Never grant VIP when the observation was not durably recorded.
                logger.error("Unable to journal Seed VIP observation (%s)", type(exc).__name__)
                if wait(stop_event, config.poll_time_seeding):
                    return
                continue
            is_seeding = observation.phase == "seeding"

            # Server seeded
            if observation.completed:
                seeded_timestamp = observation.seeded_at
                logger.info(f"Server seeded at {seeded_timestamp.isoformat()}")
                try:
                    all_vips = get_vips(rcon=rcon_api)
                    indefinite_vip_steam_ids = filter_indefinite_vip_steam_ids(all_vips)
                except Exception as exc:
                    logger.warning("Unable to read Seed VIP recipients (%s)", type(exc).__name__)
                    all_vips = {}
                    indefinite_vip_steam_ids = set()

                # Players who were online when we seeded but didn't meet the criteria for VIP
                no_reward_steam_ids = {
                    p.player_id for p in online_players.players.values()
                } - (observation.recipients - indefinite_vip_steam_ids)

                if config.dry_run:
                    expiration_timestamps = defaultdict(
                        lambda: calc_vip_expiration_timestamp(config, None, seeded_timestamp)
                    )
                    for player in all_vips.values():
                        expiration_timestamps[player.player.player_id] = calc_vip_expiration_timestamp(
                            config, player.expiration_date, seeded_timestamp
                        )
                    message_players(rcon=rcon_api, config=config,
                                    message=config.player_messages.reward_player_message,
                                    steam_ids=observation.recipients - indefinite_vip_steam_ids,
                                    expiration_timestamps=expiration_timestamps, outbox=outbox)
                else:
                    recover_rewards(rcon_api, config, outbox, server_number)

                # Message those who did not earn
                message_players(
                    rcon=rcon_api,
                    config=config,
                    message=config.player_messages.reward_player_message_no_vip,
                    steam_ids=no_reward_steam_ids,
                    expiration_timestamps=None,
                    outbox=outbox,
                )
                if not config.dry_run:
                    pending_notices = outbox.flush(rcon_api)

                # Post seeding complete Discord message
                if config.hooks:
                    logger.debug(
                        f"Making embed for `{config.player_messages.seeding_complete_message}`"
                    )
                    embed = make_seed_announcement_embed(
                        message=config.player_messages.seeding_complete_message,
                        current_map=rcon_api.current_map.pretty_name,
                        time_remaining=gamestate["raw_time_remaining"],
                        player_count_message=config.player_messages.player_count_message,
                        num_allied_players=gamestate["num_allied_players"],
                        num_axis_players=gamestate["num_axis_players"],
                    )
                    if embed:
                        send_seed_hooks(config.hooks, embed)

                # Reset for next seed
                last_bucket_announced = False
                prev_announced_bucket = 0

            if is_seeding:
                sleep_time = config.poll_time_seeding

                # When we fall back into seeding with players still on the
                # server we want to announce the largest bucket possible or
                # it will announce from the smallest to the largest and spam
                # Discord with unneccessary announcements
                next_player_bucket = get_next_player_bucket(
                    config.player_announce_thresholds,
                    total_players=total_players,
                )

                # Announce seeding progress
                logger.debug(
                    f"webhook_count={len(config.hooks)} {config.player_announce_thresholds=} {total_players=} {prev_announced_bucket=} {next_player_bucket=} {last_bucket_announced=}"
                )
                if (
                    config.hooks
                    and next_player_bucket
                    and not last_bucket_announced
                    and prev_announced_bucket < next_player_bucket
                    and total_players >= next_player_bucket
                ):
                    prev_announced_bucket = next_player_bucket

                    embed = make_seed_announcement_embed(
                        message=config.player_messages.seeding_in_progress_message.format(
                            player_count=total_players
                        ),
                        current_map=rcon_api.current_map.pretty_name,
                        time_remaining=gamestate["raw_time_remaining"],
                        player_count_message=config.player_messages.player_count_message,
                        num_allied_players=gamestate["num_allied_players"],
                        num_axis_players=gamestate["num_axis_players"],
                    )
                    if next_player_bucket == config.player_announce_thresholds[-1]:
                        logger.debug(f"setting last_bucket_announced=True")
                        last_bucket_announced = True

                    if embed:
                        send_seed_hooks(config.hooks, embed)

            else:
                sleep_time = config.poll_time_seeded

            if pending_notices:
                sleep_time = min(sleep_time, RETRY_SECONDS)
            logger.info(f"sleeping {sleep_time=}")
            if wait(stop_event, sleep_time):
                return
    except* Exception as eg:
        # Client exceptions may contain configured webhook URLs or tokens.
        error_types = ", ".join(sorted({type(e).__name__ for e in eg.exceptions}))
        logger.error("Seed VIP stopped (%s)", error_types)
        raise RuntimeError(f"Seed VIP stopped ({error_types})") from None


if __name__ == "__main__":
    try:
        run()
    except Exception as e:
        logger.error("Seed VIP stopped")
        logger.exception(e)
        sys.exit(1)
