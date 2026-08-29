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
                     (default: auto; existing combined installs stay combined)
EOF
}

mode="${1:-}"
if [[ "$mode" != "--check-only" && "$mode" != "--deploy" ]]; then
  usage >&2
  exit 2
fi

for command_name in git docker mktemp sha256sum; do
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
trap 'rm -f "$target_override" "$target_worker_override"' EXIT
git show "$target_sha:compose.mobile-admin.yaml" > "$target_override"
git show "$target_sha:compose.combined-workers.yaml" > "$target_worker_override"

resolved_environment="$(
  docker compose \
    --profile mobile \
    -f compose.yaml \
    -f "$target_override" \
    -f "$target_worker_override" \
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
existing_combined_worker_container="$(
  docker compose \
    --profile mobile \
    --profile combined-workers \
    -f compose.yaml \
    -f compose.mobile-admin.yaml \
    ps -q frontline_background_worker
)"
case "${configured_worker_mode,,}" in
  auto)
    if [[ -n "$existing_combined_worker_container" ]]; then
      background_worker_mode=combined
    else
      background_worker_mode=split
    fi
    ;;
  combined|split)
    background_worker_mode="${configured_worker_mode,,}"
    ;;
  *)
    echo "Invalid FRONTLINE_BACKGROUND_WORKER_MODE '$configured_worker_mode'; expected auto, combined or split." >&2
    exit 1
    ;;
esac

target_profiles=(--profile mobile)
if [[ "$background_worker_mode" == combined ]]; then
  target_profiles+=(--profile combined-workers)
else
  target_profiles+=(--profile split-background-workers)
fi

CRCON_IMAGE_TAG="$target_short" CRCON_VERSION="$target_version" docker compose \
  "${target_profiles[@]}" \
  -f compose.yaml \
  -f "$target_override" \
  -f "$target_worker_override" \
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
echo "Deployment services: ${deployment_services[*]}"
if [[ "$mode" == "--check-only" ]]; then
  exit 0
fi

if [[ "$current_sha" == "$target_sha" ]]; then
  echo "Already deployed at $target_short."
  exit 0
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
  CRCON_IMAGE_TAG="$target_short" CRCON_VERSION="$target_version" docker compose \
    "${target_profiles[@]}" \
    -f compose.yaml \
    -f compose.mobile-admin.yaml \
    -f compose.combined-workers.yaml \
    "$@"
}

compose_target config --quiet
compose_all_worker_profiles() {
  CRCON_IMAGE_TAG="$target_short" CRCON_VERSION="$target_version" docker compose \
    --profile mobile \
    --profile combined-workers \
    --profile split-background-workers \
    -f compose.yaml \
    -f compose.mobile-admin.yaml \
    -f compose.combined-workers.yaml \
    "$@"
}
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
echo "Building immutable images for $target_short..."
compose_target build --pull "${deployment_services[@]}"

env_tmp="$(mktemp "$repo_root/.env.XXXXXX")"
awk -v image_tag="$target_short" -v release_version="$target_version" \
  -v worker_mode="$background_worker_mode" '
  BEGIN { image_written = 0; version_written = 0; worker_mode_written = 0 }
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
  { print }
  END {
    if (!image_written) print "CRCON_IMAGE_TAG=" image_tag
    if (!version_written) print "CRCON_VERSION=" release_version
    if (!worker_mode_written) print "FRONTLINE_BACKGROUND_WORKER_MODE=" worker_mode
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
