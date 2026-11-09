#!/bin/bash
set -eu

# Every active supervisor may run this task. The shared log volume owns both
# the lock and the state, so rotation also works when server 1 is retired.
# Never change ownership of a bind-mounted configuration file here.
log_directory="${LOGROTATE_LOG_DIR:-/logs}"
config_file="${LOGROTATE_CONFIG:-/config/logrotate.conf}"
exec 9>"$log_directory/.logrotate.lock"
flock -n -E 75 9 || {
    result=$?
    [ "$result" -eq 75 ] && exit 0
    exit "$result"
}
/usr/sbin/logrotate --state "$log_directory/.logrotate.status" "$config_file"
