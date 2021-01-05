#!/usr/bin/env sh

python /generate_config_from_env.py /docker_config.toml /bot/config.toml

echo "Waiting a few seconds before starting"
sleep 10
echo "Starting..."

exec python /bot/main.py