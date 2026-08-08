#!/usr/bin/env bash

set -Eeuo pipefail

usage() {
  cat <<'EOF'
Usage: scripts/deploy_frontline.sh --check-only
       scripts/deploy_frontline.sh --deploy

Environment overrides:
  FRONTLINE_REMOTE   Git remote to deploy from (default: frontline)
  FRONTLINE_BRANCH   Branch to deploy (default: master)
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

if [[ ! -f compose.yaml || ! -f compose.mobile-admin.yaml || ! -f .env ]]; then
  echo "compose.yaml, compose.mobile-admin.yaml and .env must exist in $repo_root" >&2
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

echo "Fetching $remote_name/$branch_name..."
git fetch --prune "$remote_name" "$branch_name"

current_sha="$(git rev-parse HEAD)"
target_sha="$(git rev-parse FETCH_HEAD)"
current_short="${current_sha:0:12}"
target_short="${target_sha:0:12}"

if ! git merge-base --is-ancestor "$current_sha" "$target_sha"; then
  echo "Refusing non-fast-forward deployment: $current_short -> $target_short" >&2
  exit 1
fi

git diff --check "$current_sha" "$target_sha"

target_override="$(mktemp "${TMPDIR:-/tmp}/crcon-compose.XXXXXX.yaml")"
trap 'rm -f "$target_override"' EXIT
git show "$target_sha:compose.mobile-admin.yaml" > "$target_override"

CRCON_IMAGE_TAG="$target_short" docker compose \
  --profile mobile \
  -f compose.yaml \
  -f "$target_override" \
  config --quiet

resolved_environment="$(
  docker compose \
    --profile mobile \
    -f compose.yaml \
    -f "$target_override" \
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
mobile_push_worker_enabled=false
case "${mobile_integration_enabled,,}" in
  1|true|yes|on)
    if [[ -n "$mobile_push_relay_url" ]]; then
      mobile_push_worker_enabled=true
      deployment_services+=(mobile_push_worker)
    fi
    ;;
esac
if [[ "$mobile_push_worker_enabled" == false ]]; then
  echo "Mobile push worker disabled: integration or relay URL is not configured."
fi

echo "Preflight passed: $current_short -> $target_short"
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
  CRCON_IMAGE_TAG="$target_short" docker compose \
    --profile mobile \
    -f compose.yaml \
    -f compose.mobile-admin.yaml \
    "$@"
}

compose_target config --quiet
if [[ "$mobile_push_worker_enabled" == false ]]; then
  # A worker from an older deployment is a configured service, not an orphan,
  # so --remove-orphans will not remove it for us.
  compose_target rm --stop --force mobile_push_worker >/dev/null 2>&1 || true
fi
echo "Building immutable images for $target_short..."
compose_target build --pull "${deployment_services[@]}"

env_tmp="$(mktemp "$repo_root/.env.XXXXXX")"
if grep -q '^CRCON_IMAGE_TAG=' .env; then
  sed "s/^CRCON_IMAGE_TAG=.*/CRCON_IMAGE_TAG=$target_short/" .env > "$env_tmp"
else
  cp .env "$env_tmp"
  printf '\nCRCON_IMAGE_TAG=%s\n' "$target_short" >> "$env_tmp"
fi
chmod --reference=.env "$env_tmp"
mv "$env_tmp" .env

cat > "$state_dir/$timestamp.env" <<EOF
PREVIOUS_SHA=$current_sha
DEPLOYED_SHA=$target_sha
DATABASE_BACKUP=$backup_file
BACKEND_ROLLBACK_TAG=frontline/hll_rcon_tool:rollback-$current_short
FRONTEND_ROLLBACK_TAG=frontline/hll_rcon_tool_frontend:rollback-$current_short
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
