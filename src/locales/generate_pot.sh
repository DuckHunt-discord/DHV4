#!/usr/bin/env bash
# pybabel extract -o messages.pot ../

# Just extract docstrings
python3 ./pygettext.py --docstrings --no-default-keywords --output=./messages.pot --verbose ../

# Add messages
xgettext --language=Python --add-comments=TRANSLATORS: --force-po -o ./messages.pot --join-existing -vv ../**/*.py

# pybabel init -l en -i ./messages.pot -d ./
# pybabel compile -d ./