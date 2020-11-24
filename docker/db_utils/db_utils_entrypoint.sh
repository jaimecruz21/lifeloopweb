#!/bin/sh
if [[ -z "$ENVIRONMENT" ]]; then
    sh
else
    # Sometimes crond is slightly slow, so sleep a couple seconds
    /usr/sbin/crond -l 0 -L /var/log/cron.log && sleep 2 && tail -f /var/log/cron.log
fi
