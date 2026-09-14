# Retiring a game-server instance without stopping shared services

Treat the first numbered server as an ordinary instance, not as the owner of the
whole installation. Before retirement, inspect actual compose dependencies and
verify that the shared Discord callback points to a reachable, retained backend
of the same installation. Keep incident forwarding to the original server intact.

1. Identify only `backend_N`, `frontend_N` and `supervisor_N`. Check for open votes
   and additional dependent services before stopping them.
2. Back up the active compose manifests and current restart policies. Retain the
   database, configuration, game history, logs and volumes.
3. Set the three retired services to `restart: "no"`, `scale: 0` and an explicit
   retired profile in the active deployment manifests. A profile alone is not
   sufficient when deployment scripts use `--profile '*'`.
4. Disable the containers' Docker restart policy. Run the owning backend's
   `python -m rcon.cli unregister_api` before stopping it; this removes only its
   own discovery registration. Never clear shared Redis to remove a server.
5. Stop only those three containers. Do not run compose `down`, delete volumes,
   or stop installation-wide maintenance, PostgreSQL, Redis, webhook, Discord,
   callback, or background-worker services. A shared worker may still use
   `SERVER_NUMBER=1` for installation metadata without needing backend 1 alive.
6. Verify unchanged identities and running state of retained containers, active
   discovery registrations and authenticated Discord diagnostic callbacks.

Record retired instances in the deployment's operations notes and preserve their
retirement flags when generating later releases. Reactivation requires explicit
operator approval: restore only that instance's service definitions and restart
policies, then start it normally to regenerate discovery. Do not restore an old
database or revert newer versions of unrelated services just to reactivate it.

Stopping the instance does not remove DNS, certificates, or historical reports.
Changing those is a separate task.
