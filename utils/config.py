# coding=utf-8
import toml


def load_config():
    with open("config.toml") as f:
        return toml.load(f)
