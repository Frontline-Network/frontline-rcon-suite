"""Registration for log-loop handlers with no import-time side effects."""

_registered = False


def register_log_hooks() -> None:
    """Import every built-in log handler exactly once in this process."""
    global _registered
    if _registered:
        return

    # These imports register decorated callbacks in rcon.logs.loop.HOOKS.
    from rcon import hooks  # noqa: F401
    from rcon.autobalancer import hooks as autobalancer_hooks  # noqa: F401
    from rcon.auto_kick import auto_kick  # noqa: F401
    from rcon.automods.tk_autoban import (  # noqa: F401
        auto_ban_if_tks_right_after_connection,
    )
    from rcon.discord_chat import (  # noqa: F401
        handle_on_chat,
        handle_on_kill,
        handle_on_tk,
    )
    from rcon.recent_actions import update_kills, update_tks  # noqa: F401
    from rcon.watchlist import watchdog  # noqa: F401

    _registered = True
