#!/usr/bin/env sh

python /duckhunt/generate_config_from_env.py /duckhunt/docker_config.toml /duckhunt/src/config.toml

echo "Waiting a few seconds before starting"
sleep 10
echo "Starting..."

exec python /duckhunt/src/main.py