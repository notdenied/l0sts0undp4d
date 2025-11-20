#!/bin/sh
set -e

mkdir -p /app/data/uploads

chown -R ${APP_UID}:${APP_GID} /app/data

if [ ! -f /app/data/secret_key ]; then
    openssl rand -hex 32 > /app/data/secret_key
fi
export SECRET_KEY=$(cat /app/data/secret_key)

exec su -s /bin/sh -c "python3 /app/app.py" ${APP_UID}
