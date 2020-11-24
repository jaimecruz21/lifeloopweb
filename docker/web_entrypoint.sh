#!/bin/sh
echo '/tmp/core.%h.%e.%t' > /proc/sys/kernel/core_pattern
ulimit -c unlimited
if [[ $FLASK_DEBUG ]]
  then yarn build_dev
fi
dockerize -timeout 60s -wait tcp://database:3306 flask run -h 0.0.0.0 -p5000 --reload
