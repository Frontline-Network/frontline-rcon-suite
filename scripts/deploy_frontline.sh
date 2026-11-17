#!/usr/bin/env bash

set -Eeuo pipefail

usage() {
  cat <<'EOF'
Usage: scripts/deploy_frontline.sh --check-only
       scripts/deploy_frontline.sh --deploy

Environment overrides:
  FRONTLINE_REMOTE   Git remote to deploy from (default: frontline)
  FRONTLINE_BRANCH   Branch to deploy (default: master)
  FRONTLINE_BACKGROUND_WORKER_MODE
                     Background worker topology: auto, combined or split
                     (default: auto; auto migrates to combined)
  FRONTLINE_SUPERVISOR_RUNTIME_MODE
                     Supervisor topology: auto, combined or split
                     (default: auto; auto migrates standard installs to combined)
EOF
}

mode="${1:-}"
if [[ "$mode" != "--check-only" && "$mode" != "--deploy" ]]; then
  usage >&2
  exit 2
fi

for command_name in git docker mktemp sha256sum python3; do
  if ! command -v "$command_name" >/dev/null 2>&1; then
    echo "Required command not found: $command_name" >&2
    exit 1
  fi
done

repo_root="$(git rev-parse --show-toplevel)"
cd "$repo_root"

remote_name="${FRONTLINE_REMOTE:-frontline}"
branch_name="${FRONTLINE_BRANCH:-master}"
expected_branch="$branch_name"

if [[ ! -f compose.yaml || ! -f compose.mobile-admin.yaml \
  || ! -f compose.combined-workers.yaml || ! -f .env ]]; then
  echo "compose.yaml, compose.mobile-admin.yaml, compose.combined-workers.yaml and .env must exist in $repo_root" >&2
  exit 1
fi

# The generated compose.yaml is installation-specific: a one-server host must
# not start backend_2/frontend_2/supervisor_2 merely because the shared
# Frontline override also knows how to customize those services. Start with
# only the services that exist in the generated base file. The optional mobile
# push worker is added below only when its relay is configured.
mapfile -t deployment_services < <(
  docker compose -f compose.yaml config --services
)
if ((${#deployment_services[@]} == 0)); then
  echo "No deployment services found in compose.yaml." >&2
  exit 1
fi

current_branch="$(git symbolic-ref --quiet --short HEAD || true)"
if [[ "$current_branch" != "$expected_branch" ]]; then
  echo "Refusing deployment from branch '$current_branch'; expected '$expected_branch'." >&2
  exit 1
fi

if [[ -n "$(git status --porcelain --untracked-files=normal)" ]]; then
  echo "Refusing deployment because the Git worktree is not clean:" >&2
  git status --short >&2
  exit 1
fi

if ! git remote get-url "$remote_name" >/dev/null 2>&1; then
  echo "Git remote '$remote_name' does not exist." >&2
  exit 1
fi

echo "Fetching $remote_name/$branch_name and release tags..."
git fetch --prune --tags "$remote_name" "$branch_name"

current_sha="$(git rev-parse HEAD)"
target_sha="$(git rev-parse FETCH_HEAD)"
current_short="${current_sha:0:12}"
target_short="${target_sha:0:12}"
target_version="$(git describe --tags --always "$target_sha")"

if ! git merge-base --is-ancestor "$current_sha" "$target_sha"; then
  echo "Refusing non-fast-forward deployment: $current_short -> $target_short" >&2
  exit 1
fi

git diff --check "$current_sha" "$target_sha"

target_override="$(mktemp "${TMPDIR:-/tmp}/crcon-compose.XXXXXX.yaml")"
target_worker_override="$(mktemp "${TMPDIR:-/tmp}/crcon-workers.XXXXXX.yaml")"
target_health_override="$(mktemp "${TMPDIR:-/tmp}/crcon-health.XXXXXX.json")"
target_health_generator="$(mktemp "${TMPDIR:-/tmp}/crcon-health-generator.XXXXXX.py")"
target_source_archive="$(mktemp "${TMPDIR:-/tmp}/crcon-runtime-source.XXXXXX.tar")"
trap 'rm -f "$target_override" "$target_worker_override" "$target_health_override" "$target_health_generator" "$target_source_archive"' EXIT
git show "$target_sha:compose.mobile-admin.yaml" > "$target_override"
git show "$target_sha:compose.combined-workers.yaml" > "$target_worker_override"
git show "$target_sha:scripts/backend_health_override.py" > "$target_health_generator"
python3 "$target_health_generator" "$target_health_override" "${deployment_services[@]}"

resolved_environment="$(
  docker compose \
    --profile mobile \
    -f compose.yaml \
    -f "$target_override" \
    -f "$target_worker_override" \
    -f "$target_health_override" \
    config --environment
)"
mobile_integration_enabled="$(
  awk -F= '$1 == "MOBILE_INTEGRATION_ENABLED" { print substr($0, index($0, "=") + 1) }' \
    <<<"$resolved_environment" | tail -n 1
)"
mobile_push_relay_url="$(
  awk -F= '$1 == "MOBILE_PUSH_RELAY_URL" { print substr($0, index($0, "=") + 1) }' \
    <<<"$resolved_environment" | tail -n 1
)"
discord_reports_enabled="$(
  awk -F= '$1 == "DISCORD_REPORTS_ENABLED" { print substr($0, index($0, "=") + 1) }' \
    <<<"$resolved_environment" | tail -n 1
)"
ai_moderation_enabled="$(
  awk -F= '$1 == "AI_MODERATION_ENABLED" { print substr($0, index($0, "=") + 1) }' \
    <<<"$resolved_environment" | tail -n 1
)"
mobile_push_loop_enabled=false
case "${mobile_integration_enabled,,}" in
  1|true|yes|on)
    if [[ -n "$mobile_push_relay_url" ]]; then
      mobile_push_loop_enabled=true
    fi
    ;;
esac

discord_reports_loop_enabled=false
case "${discord_reports_enabled,,}" in
  1|true|yes|on)
    discord_reports_loop_enabled=true
    ;;
esac

ai_moderation_loop_enabled=false
case "${ai_moderation_enabled,,}" in
  1|true|yes|on)
    if [[ "$discord_reports_loop_enabled" == true ]]; then
      ai_moderation_loop_enabled=true
    fi
    ;;
esac

configured_worker_mode="${FRONTLINE_BACKGROUND_WORKER_MODE:-$(
  awk -F= '$1 == "FRONTLINE_BACKGROUND_WORKER_MODE" { print substr($0, index($0, "=") + 1) }' \
    .env | tail -n 1
)}"
configured_worker_mode="${configured_worker_mode:-auto}"
case "${configured_worker_mode,,}" in
  auto)
    background_worker_mode=combined
    ;;
  combined|split)
    background_worker_mode="${configured_worker_mode,,}"
    ;;
  *)
    echo "Invalid FRONTLINE_BACKGROUND_WORKER_MODE '$configured_worker_mode'; expected auto, combined or split." >&2
    exit 1
    ;;
esac

configured_supervisor_mode="${FRONTLINE_SUPERVISOR_RUNTIME_MODE:-$(
  awk -F= '$1 == "FRONTLINE_SUPERVISOR_RUNTIME_MODE" { print substr($0, index($0, "=") + 1) }' \
    .env | tail -n 1
)}"
configured_supervisor_mode="${configured_supervisor_mode:-auto}"
existing_supervisor_config="$(
  awk -F= '$1 == "HLL_SUPERVISOR_CONFIG" { print substr($0, index($0, "=") + 1) }' \
    .env | tail -n 1
)"
case "${configured_supervisor_mode,,}" in
  auto)
    case "$existing_supervisor_config" in
      ""|/config/supervisord.conf|/config/supervisord_combined.conf)
        supervisor_runtime_mode=combined
        persisted_supervisor_mode=combined
        target_supervisor_config=/config/supervisord_combined.conf
        ;;
      *)
        supervisor_runtime_mode=custom
        persisted_supervisor_mode=auto
        target_supervisor_config="$existing_supervisor_config"
        echo "Preserving custom supervisor configuration: $target_supervisor_config"
        ;;
    esac
    ;;
  combined)
    supervisor_runtime_mode=combined
    persisted_supervisor_mode=combined
    target_supervisor_config=/config/supervisord_combined.conf
    ;;
  split)
    supervisor_runtime_mode=split
    persisted_supervisor_mode=split
    target_supervisor_config=/config/supervisord.conf
    ;;
  *)
    echo "Invalid FRONTLINE_SUPERVISOR_RUNTIME_MODE '$configured_supervisor_mode'; expected auto, combined or split." >&2
    exit 1
    ;;
esac

target_profiles=(--profile mobile)
if [[ "$background_worker_mode" == combined ]]; then
  target_profiles+=(--profile combined-workers)
else
  target_profiles+=(--profile split-background-workers)
fi

HLL_SUPERVISOR_CONFIG="$target_supervisor_config" \
  CRCON_IMAGE_TAG="$target_short" CRCON_VERSION="$target_version" docker compose \
  "${target_profiles[@]}" \
  -f compose.yaml \
  -f "$target_override" \
  -f "$target_worker_override" \
  -f "$target_health_override" \
  config --quiet

combined_worker_enabled=false
if [[ "$background_worker_mode" == combined ]]; then
  if [[ "$mobile_push_loop_enabled" == true \
    || "$discord_reports_loop_enabled" == true ]]; then
    combined_worker_enabled=true
    deployment_services+=(frontline_background_worker)
  else
    echo "Combined background worker disabled: no delivery integration is configured."
  fi
else
  if [[ "$mobile_push_loop_enabled" == true ]]; then
    deployment_services+=(mobile_push_worker)
  else
    echo "Mobile push worker disabled: integration or relay URL is not configured."
  fi

  if [[ "$discord_reports_loop_enabled" == true ]]; then
    deployment_services+=(discord_report_worker)
  fi
  if [[ "$ai_moderation_loop_enabled" == true ]]; then
    deployment_services+=(discord_moderation_worker)
  fi
fi

echo "Preflight passed: $current_short -> $target_short ($target_version)"
echo "Background worker topology: $background_worker_mode"
echo "Supervisor runtime topology: $supervisor_runtime_mode ($target_supervisor_config)"
echo "Deployment services: ${deployment_services[*]}"
if [[ "$mode" == "--check-only" ]]; then
  exit 0
fi

if [[ "$current_sha" == "$target_sha" ]]; then
  echo "Already deployed at $target_short."
  python3 scripts/discover_backend_readiness.py
  exit 0
fi

verify_readiness_images() {
  local images="$1" backend_image
  while IFS= read -r backend_image; do
    [[ -n "$backend_image" ]] || continue
    if ! docker image inspect "$backend_image" >/dev/null 2>&1; then
      docker pull "$backend_image"
    fi
    if ! docker run --rm --network none --entrypoint python "$backend_image" -c \
      'import sys; from pathlib import Path; p=Path("/code/scripts/backend_healthcheck.py"); u=Path("/code/rconweb/rconweb/urls.py"); sys.exit(0 if p.is_file() and u.is_file() and "healthz" in u.read_text() else 1)'; then
      echo "Backend image is missing the required readiness probe or endpoint; deployment stopped." >&2
      return 1
    fi
  done <<< "$images"
}

# Backends above 4 may retain a separately configured legacy image. Verify
# those images before checkout or worker changes; unlike the managed images,
# they are not guaranteed to be built by the Frontline override below.
extra_backend_services=()
for service in "${deployment_services[@]}"; do
  if [[ "$service" =~ ^backend_([1-9][0-9]*)$ ]]; then
    number="${BASH_REMATCH[1]}"
    if [[ "$number" != [1234] ]]; then
      extra_backend_services+=("$service")
    fi
  fi
done
if ((${#extra_backend_services[@]})); then
  extra_backend_images="$(
    HLL_SUPERVISOR_CONFIG="$target_supervisor_config" \
      CRCON_IMAGE_TAG="$target_short" CRCON_VERSION="$target_version" docker compose \
      "${target_profiles[@]}" -f compose.yaml -f "$target_override" \
      -f "$target_worker_override" -f "$target_health_override" config --format json |
      python3 "$target_health_generator" --images "${extra_backend_services[@]}"
  )"
  verify_readiness_images "$extra_backend_images"
fi

timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
backup_dir="$repo_root/.deploy-backups"
state_dir="$repo_root/.deploy-state"
mkdir -p "$backup_dir" "$state_dir"
chmod 700 "$backup_dir" "$state_dir"

compose_current=(
  docker compose --profile mobile -f compose.yaml -f compose.mobile-admin.yaml
)
postgres_container="$("${compose_current[@]}" ps -q postgres)"
if [[ -z "$postgres_container" ]]; then
  echo "PostgreSQL container is not running; aborting before checkout." >&2
  exit 1
fi

backup_file="$backup_dir/postgres-${timestamp}-${current_short}-to-${target_short}.dump"
echo "Creating PostgreSQL backup: $backup_file"
docker exec "$postgres_container" sh -c \
  'exec pg_dump --format=custom --username="$POSTGRES_USER" "$POSTGRES_DB"' \
  > "$backup_file"
if [[ ! -s "$backup_file" ]]; then
  echo "Database backup is empty; aborting." >&2
  exit 1
fi
chmod 600 "$backup_file"
sha256sum "$backup_file" > "$backup_file.sha256"

backend_container="$("${compose_current[@]}" ps -q backend_1)"
frontend_container="$("${compose_current[@]}" ps -q frontend_1)"
if [[ -n "$backend_container" ]]; then
  backend_image="$(docker inspect --format '{{.Image}}' "$backend_container")"
  docker image tag "$backend_image" "frontline/hll_rcon_tool:rollback-$current_short"
fi
if [[ -n "$frontend_container" ]]; then
  frontend_image="$(docker inspect --format '{{.Image}}' "$frontend_container")"
  docker image tag "$frontend_image" \
    "frontline/hll_rcon_tool_frontend:rollback-$current_short"
fi

git merge --ff-only "$target_sha"

compose_target() {
  HLL_SUPERVISOR_CONFIG="$target_supervisor_config" \
    CRCON_IMAGE_TAG="$target_short" CRCON_VERSION="$target_version" docker compose \
    "${target_profiles[@]}" \
    -f compose.yaml \
    -f compose.mobile-admin.yaml \
    -f compose.combined-workers.yaml \
    -f "$target_health_override" \
    "$@"
}

compose_target config --quiet
compose_all_worker_profiles() {
  HLL_SUPERVISOR_CONFIG="$target_supervisor_config" \
    CRCON_IMAGE_TAG="$target_short" CRCON_VERSION="$target_version" docker compose \
    --profile mobile \
    --profile combined-workers \
    --profile split-background-workers \
    -f compose.yaml \
    -f compose.mobile-admin.yaml \
    -f compose.combined-workers.yaml \
    -f "$target_health_override" \
    "$@"
}

# Build and validate every configured backend image before stopping workers.
# Some generated installations use a different image for backend 5 and up;
# do not apply a probe that such an image cannot possibly satisfy.
abort_before_service_change() {
  echo "Deployment stopped before changing running services." >&2
  if git diff --quiet && git diff --cached --quiet && git reset --keep "$current_sha"; then
    echo "Restored the previous checkout; runtime and environment were not changed." >&2
  else
    echo "Could not safely restore the previous checkout; inspect the worktree before retrying." >&2
  fi
  exit 1
}
echo "Building immutable images for $target_short..."
if ! compose_target build --pull "${deployment_services[@]}"; then
  abort_before_service_change
fi
if ! backend_images="$(
  compose_target config --format json |
    python3 "$target_health_generator" --images "${deployment_services[@]}"
)"; then
  abort_before_service_change
fi
if ! verify_readiness_images "$backend_images"; then
  abort_before_service_change
fi
if ! git archive --format=tar "$target_sha" rcon rconweb alembic scripts docs/releases \
  alembic.ini entrypoint.sh manage.py LICENSE requirements.lock requirements-vcs.txt > "$target_source_archive"; then
  abort_before_service_change
fi
while IFS= read -r backend_image; do
  [[ -n "$backend_image" ]] || continue
  if ! docker run --rm --network none --entrypoint python \
    -v "$target_source_archive:/tmp/frontline-target-source.tar:ro" \
    -v "$repo_root/scripts/verify_backend_source.py:/tmp/frontline-verify-source.py:ro" \
    "$backend_image" /tmp/frontline-verify-source.py /tmp/frontline-target-source.tar; then
    echo "Backend image $backend_image does not match target $target_short." >&2
    abort_before_service_change
  fi
done <<< "$backend_images"

if [[ "$background_worker_mode" == combined ]]; then
  # Configured services from the inactive split profile are not orphans. Stop
  # them explicitly so a host can never poll the same outbox twice.
  compose_all_worker_profiles rm --stop --force \
    mobile_push_worker discord_report_worker discord_moderation_worker \
    >/dev/null 2>&1 || true
  if [[ "$combined_worker_enabled" == false ]]; then
    compose_all_worker_profiles rm --stop --force frontline_background_worker \
      >/dev/null 2>&1 || true
  fi
else
  compose_all_worker_profiles rm --stop --force frontline_background_worker \
    >/dev/null 2>&1 || true
  if [[ "$mobile_push_loop_enabled" == false ]]; then
    compose_all_worker_profiles rm --stop --force mobile_push_worker \
      >/dev/null 2>&1 || true
  fi
  if [[ "$discord_reports_loop_enabled" == false ]]; then
    compose_all_worker_profiles rm --stop --force discord_report_worker \
      >/dev/null 2>&1 || true
  fi
  if [[ "$ai_moderation_loop_enabled" == false ]]; then
    compose_all_worker_profiles rm --stop --force discord_moderation_worker \
      >/dev/null 2>&1 || true
  fi
fi

env_tmp="$(mktemp "$repo_root/.env.XXXXXX")"
awk -v image_tag="$target_short" -v release_version="$target_version" \
  -v worker_mode="$background_worker_mode" \
  -v supervisor_mode="$persisted_supervisor_mode" \
  -v supervisor_config="$target_supervisor_config" '
  BEGIN {
    image_written = 0
    version_written = 0
    worker_mode_written = 0
    supervisor_mode_written = 0
    supervisor_config_written = 0
  }
  /^CRCON_IMAGE_TAG=/ {
    if (!image_written) {
      print "CRCON_IMAGE_TAG=" image_tag
      image_written = 1
    }
    next
  }
  /^CRCON_VERSION=/ {
    if (!version_written) {
      print "CRCON_VERSION=" release_version
      version_written = 1
    }
    next
  }
  /^FRONTLINE_BACKGROUND_WORKER_MODE=/ {
    if (!worker_mode_written) {
      print "FRONTLINE_BACKGROUND_WORKER_MODE=" worker_mode
      worker_mode_written = 1
    }
    next
  }
  /^FRONTLINE_SUPERVISOR_RUNTIME_MODE=/ {
    if (!supervisor_mode_written) {
      print "FRONTLINE_SUPERVISOR_RUNTIME_MODE=" supervisor_mode
      supervisor_mode_written = 1
    }
    next
  }
  /^HLL_SUPERVISOR_CONFIG=/ {
    if (!supervisor_config_written) {
      print "HLL_SUPERVISOR_CONFIG=" supervisor_config
      supervisor_config_written = 1
    }
    next
  }
  { print }
  END {
    if (!image_written) print "CRCON_IMAGE_TAG=" image_tag
    if (!version_written) print "CRCON_VERSION=" release_version
    if (!worker_mode_written) print "FRONTLINE_BACKGROUND_WORKER_MODE=" worker_mode
    if (!supervisor_mode_written) print "FRONTLINE_SUPERVISOR_RUNTIME_MODE=" supervisor_mode
    if (!supervisor_config_written) print "HLL_SUPERVISOR_CONFIG=" supervisor_config
  }
' .env > "$env_tmp"
chmod --reference=.env "$env_tmp"
mv "$env_tmp" .env

cat > "$state_dir/$timestamp.env" <<EOF
PREVIOUS_SHA=$current_sha
DEPLOYED_SHA=$target_sha
DATABASE_BACKUP=$backup_file
BACKEND_ROLLBACK_TAG=frontline/hll_rcon_tool:rollback-$current_short
FRONTEND_ROLLBACK_TAG=frontline/hll_rcon_tool_frontend:rollback-$current_short
BACKGROUND_WORKER_MODE=$background_worker_mode
SUPERVISOR_RUNTIME_MODE=$supervisor_runtime_mode
SUPERVISOR_CONFIG=$target_supervisor_config
EOF
chmod 600 "$state_dir/$timestamp.env"

echo "Starting CRCON at $target_short..."
compose_target up -d --remove-orphans --wait --wait-timeout 300 \
  "${deployment_services[@]}"

maintenance_container="$(compose_target ps -q maintenance)"
docker exec "$maintenance_container" sh -lc 'cd /code && alembic current'
docker exec "$maintenance_container" sh -lc \
  'cd /code && python rconweb/manage.py showmigrations api --plan | tail -n 12'
compose_target ps

echo "Deployment completed: $current_short -> $target_short"
echo "Database backup: $backup_file"
