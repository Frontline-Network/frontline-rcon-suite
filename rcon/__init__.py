import os

import rcon.settings

# Maintenance, webhook and dedicated supervisor processes do not all need the
# log event handlers. Importing them eagerly adds tens of MiB to every Python
# process. The log loop registers them explicitly before it starts.
if not any(
    os.getenv(name)
    for name in (
        "HLL_MAINTENANCE_CONTAINER",
        "HLL_WH_SERVICE_CONTAINER",
        "HLL_SUPERVISOR_PROCESS",
    )
):
    from rcon.log_hooks import register_log_hooks

    register_log_hooks()
