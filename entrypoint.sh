#!/usr/bin/env bash

set -e
# Do not trace expanded environment values (including database credentials).

# Only run the database migrations in the maintenance container
if [ "$1" == 'maintenance' ]
then
  # A restarted maintenance container must not retain a previous success marker.
  rm -f rconweb/maintenance-container-healthy
  alembic upgrade head
  # Convert old stye player IDs to new style (md5 hash)
  # TODO: we can eventually remove this in a few releases once old installs have updated their game servers and CRCON
  # SERVER_NUMBER is mandatory and not otherwise set in the maintenance container; only want it to run once
  # LOGGING_PATH and LOGGING_FILENAME need to be passed to get it to log to the directory that is bind mounted
  # A historical player record can still be referenced by an account.  Do not
  # block every subsequent deployment (including schema migrations) on that
  # legacy cleanup; the command remains safe to retry after the reference has
  # been resolved.
  if ! SERVER_NUMBER=1 LOGGING_PATH=/logs/ LOGGING_FILENAME=startup.log python -m rcon.cli merge_duplicate_player_ids
  then
    echo "WARNING: legacy duplicate-player-id cleanup was deferred; see startup.log" >&2
  fi
  SERVER_NUMBER=1 LOGGING_PATH=/logs/ LOGGING_FILENAME=startup.log python -m rcon.cli convert_win_player_ids
  # Upgrade durable Redis structures before any server-specific container starts.
  # The command discovers every populated logical Redis database so multi-server
  # installations are migrated in the same maintenance pass.
  SERVER_NUMBER=1 LOGGING_PATH=/logs/ LOGGING_FILENAME=startup.log python -m rcon.cache_migrations
  cd rconweb
  # Customer upgrades apply only migrations shipped and tested with the image.
  # Model drift must fail instead of generating installation-specific history.
  ./manage.py makemigrations --check --dry-run --no-input
  ./manage.py migrate --noinput
  # Create this file after migrations which is how Docker determines the container is healthy
  touch maintenance-container-healthy
  # Keep the container running until it's explicitly created again
  sleep infinity
fi

# Check if we're in the webhook_service container
if [ "$1" == 'webhook_service' ]
then
  LOGGING_PATH=/logs/ LOGGING_FILENAME=webhook_service.log python -m rcon.webhook_service
fi

if [ "$1" == 'mobile_push_worker' ]
then
  cd rconweb
  exec python manage.py mobile_push_worker
fi

if [ "$1" == 'discord_report_worker' ]
then
  cd rconweb
  exec python manage.py discord_report_worker
fi

if [ "$1" == 'discord_event_worker' ]
then
  cd rconweb
  exec python manage.py discord_report_worker --events-only
fi

if [ "$1" == 'discord_moderation_worker' ]
then
  cd rconweb
  exec python manage.py discord_report_worker --moderation-only
fi

if [ "$1" == 'frontline_background_worker' ]
then
  cd rconweb
  exec python manage.py frontline_background_worker
fi

# Check if we're in a backend container
if [ "$1" == 'web' ]
then
  # A container restart may preserve this file through an image layer or
  # mounted working directory. Health must describe the current process only.
  rm -f /code/rconweb/gunicorn.pid
  # If the database password isn't set, bail early
  if [ "$HLL_DB_PASSWORD" == '' ]
  then
      echo "HLL_DB_PASSWORD not set"
      exit 0
  fi
  if [ "$HLL_HOST" == '' ]
  then
      exit 0
  fi

  python -m rcon.user_config.seed_db
  # TODO: Temporarily handle converting users old scorebot URLs to the new format; remove in a few releases
  SERVER_NUMBER=${SERVER_NUMBER} LOGGING_PATH=/logs/ LOGGING_FILENAME=api_${SERVER_NUMBER}.log python -m rcon.cli port_legacy_scorebot_urls
  # Map cleanup depends on the game server being reachable.  An offline RCON
  # endpoint must not prevent the independent web API (including login) from
  # starting; the cleanup is safe to retry on the next container start.
  if ! SERVER_NUMBER=${SERVER_NUMBER} LOGGING_PATH=/logs/ LOGGING_FILENAME=api_${SERVER_NUMBER}.log python -m rcon.cli remove_orphaned_map_ids
  then
    echo "WARNING: orphaned-map-id cleanup was deferred because the HLL RCON endpoint is unavailable" >&2
  fi
  SERVER_NUMBER=${SERVER_NUMBER} LOGGING_PATH=/logs/ LOGGING_FILENAME=api_${SERVER_NUMBER}.log python -m rcon.cli clear_maps_cache
  ./manage.py register_api
  cd rconweb
  ./manage.py collectstatic --noinput
  # If DONT_SEED_ADMIN_USER is not set to any value
  if [[ -z "$DONT_SEED_ADMIN_USER" ]]
  then
    echo "from django.contrib.auth.models import User; User.objects.create_superuser('admin', 'admin@example.com', 'admin') if not User.objects.filter(username='admin').first() else None" | python manage.py shell
  fi
  export LOGGING_FILENAME=api_$SERVER_NUMBER.log
  API_SERVER_MODE="${HLL_API_SERVER_MODE:-auto}"
  if [[ "$API_SERVER_MODE" == "auto" ]]
  then
    # A single Daphne process can serve both HTTP and WebSockets without
    # loading Django twice. Keep the split topology for explicit scale-out.
    if [[ "$NB_API_WORKERS" =~ ^[0-9]+$ && "$NB_API_WORKERS" -eq 1 ]]
    then
      API_SERVER_MODE="unified"
    else
      API_SERVER_MODE="split"
    fi
  fi
  if ! [[ "$API_SERVER_MODE" =~ ^(unified|split)$ ]]
  then
    echo "ERROR: HLL_API_SERVER_MODE must be auto, unified or split" >&2
    exit 2
  fi
  echo "Starting API server in $API_SERVER_MODE mode ($NB_API_WORKERS configured worker(s))"
  if [[ "$API_SERVER_MODE" == "unified" ]]
  then
    # Daphne serves the same ASGI application over both ports expected by the
    # existing Nginx config. With one API worker this avoids loading Django in
    # separate Gunicorn and Daphne processes while preserving WebSockets.
    # Daphne replaces this shell via exec, so the current PID remains valid.
    echo $$ > gunicorn.pid
    exec daphne \
      -e tcp:port=8000:interface=0.0.0.0 \
      -e tcp:port=8001:interface=0.0.0.0 \
      -t 120 \
      rconweb.asgi:application
  else
    daphne -b 0.0.0.0 -p 8001 rconweb.asgi:application &
    # Successfully running gunicorn will create the pid file which is how Docker determines the container is healthy
    GUNICORN_PRELOAD_ARGS=()
    GUNICORN_PRELOAD_MODE="${HLL_GUNICORN_PRELOAD:-auto}"
    if [[ "$GUNICORN_PRELOAD_MODE" =~ ^(1|true|yes)$ ]] || \
       [[ "$GUNICORN_PRELOAD_MODE" == "auto" && "$NB_API_WORKERS" =~ ^[0-9]+$ && "$NB_API_WORKERS" -gt 1 ]]
    then
      GUNICORN_PRELOAD_ARGS=(--preload)
    fi
    GUNICORN_RECYCLE_ARGS=()
    GUNICORN_MAX_REQUESTS="${HLL_GUNICORN_MAX_REQUESTS:-1000}"
    GUNICORN_MAX_REQUESTS_JITTER="${HLL_GUNICORN_MAX_REQUESTS_JITTER:-100}"
    if [[ "$GUNICORN_MAX_REQUESTS" =~ ^[0-9]+$ && "$GUNICORN_MAX_REQUESTS" -gt 0 ]]
    then
      if ! [[ "$GUNICORN_MAX_REQUESTS_JITTER" =~ ^[0-9]+$ ]]
      then
        GUNICORN_MAX_REQUESTS_JITTER=100
      fi
      GUNICORN_RECYCLE_ARGS=(
        --max-requests "$GUNICORN_MAX_REQUESTS"
        --max-requests-jitter "$GUNICORN_MAX_REQUESTS_JITTER"
      )
    fi
    # Gunicorn 25.1 enables a threaded control socket before forking workers.
    # The inherited thread state can deadlock gthread workers during startup.
    gunicorn --no-control-socket "${GUNICORN_PRELOAD_ARGS[@]}" "${GUNICORN_RECYCLE_ARGS[@]}" --pid gunicorn.pid -w "$NB_API_WORKERS" -k gthread --threads "$NB_API_THREADS" -t 120 -b 0.0.0.0 rconweb.wsgi
  fi
  cd ..
  ./manage.py unregister_api
else
if [ "$1" == 'debug' ]
then
  tail -f manage.py
fi
if [ "$HLL_HOST" == '' ]
then
    exit 0
fi
  sleep 10
  env >> /etc/environment
  export LOGGING_FILENAME=supervisor_$SERVER_NUMBER.log
  if [[ -n "${HLL_SUPERVISOR_CONFIG:-}" ]]
  then
    exec supervisord -c "$HLL_SUPERVISOR_CONFIG"
  else
    # A later switch to the shared runtime must not inherit stale STOPPED
    # controls from an earlier canary. Shared-to-shared restarts preserve those
    # controls; only a real split-to-shared transition resets them.
    HLL_SUPERVISOR_PROCESS=1 /code/manage.py supervisor_runtime_mode split
    if [[ -f "/config/supervisord_$SERVER_NUMBER.conf" ]]
    then
      exec supervisord -c "/config/supervisord_$SERVER_NUMBER.conf"
    else
      exec supervisord -c /config/supervisord.conf
    fi
  fi
fi
