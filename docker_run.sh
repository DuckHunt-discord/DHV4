#!/usr/bin/env sh

python /generate_config_from_env.py /docker_config.toml /bot/config.toml
python /bot/main.py