#!/bin/sh
mkdir -p /etc/nginx/sites-enabled
cp /etc/nginx/sites-available/default /etc/nginx/sites-enabled/default
sed -i "s/PROXY_HOST/$PROXY_HOST/" /etc/nginx/sites-enabled/default
nginx -g 'daemon off;'
