#!/usr/bin/env bash
# pybabel extract -o messages.pot ../

# Just extract docstrings
python3 ./pygettext.py -X EXCLUDES --docstrings --no-default-keywords --output=./messages.pot --verbose ../

# Add messages
xgettext --language=Python --add-comments=TRANSLATORS: --force-po -o ./messages.pot --join-existing -vvv ../cogs/*.py
xgettext --language=Python --add-comments=TRANSLATORS: --force-po -o ./messages.pot --join-existing -vvv ../utils/*.py
xgettext --language=Python --add-comments=TRANSLATORS: --force-po -o ./messages.pot --join-existing -vvv ../main.py

# pybabel init -l en -i ./messages.pot -d ./
# pybabel compile -d ./