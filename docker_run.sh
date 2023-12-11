#!/usr/bin/env sh

python /duckhunt/generate_config_from_env.py /duckhunt/docker_config.toml /duckhunt/src/config.toml

echo "Setting current branch..."
git pull origin master || true

git status

echo "Waiting a few seconds before starting..."
sleep 5
echo "Starting..."

exec python /duckhunt/src/main.py