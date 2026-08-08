if [ "$SERVER_NUMBER" = '1' ]
then
# The config directory is bind-mounted from the Git worktree. Its committed
# 0644 permissions are already safe for logrotate; changing ownership here
# makes the non-root deployment user unable to inspect or update the checkout.
/usr/sbin/logrotate /config/logrotate.conf
fi
