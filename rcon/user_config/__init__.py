import os

# Only the general-purpose CLI needs every config model registered at package
# import time. Long-running supervisor services import the specific config
# classes they use and should not retain all unrelated models.
if not any(
    os.getenv(name)
    for name in (
        "HLL_MAINTENANCE_CONTAINER",
        "HLL_WH_SERVICE_CONTAINER",
        "HLL_SUPERVISOR_PROCESS",
    )
):

    # Import all the sub modules that represent a user setting
    # so that .utils.all_subclasses() can properly report subclasses
    # for exporting settings through the CLI
    from . import (
        auto_broadcast,
        autobalancer,
        auto_kick,
        auto_mod_level,
        auto_mod_no_leader,
        auto_mod_seeding,
        auto_mod_solo_tank,
        ban_tk_on_connect,
        camera_notification,
        chat_commands,
        expired_vips,
        gtx_server_name,
        log_line_webhooks,
        log_stream,
        leadership_vote,
        report_admin,
        name_kicks,
        population_history,
        rcon_connection_settings,
        rcon_server_settings,
        real_vip,
        scoreboard,
        standard_messages,
        steam,
        vac_game_bans,
        vote_map,
        webhooks,
        vip_rewards,
    )
