#!/usr/bin/env bash
pybabel extract -o messages.pot ../

# pybabel init -l en -i ./messages.pot -d ./
# pybabel compile -d ./