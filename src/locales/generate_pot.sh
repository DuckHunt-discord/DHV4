#!/usr/bin/env bash
# pybabel extract -o messages.pot ../

# Just extract docstrings from cogs and only cogs
python3 ./pygettext.py -X EXCLUDES --docstrings --no-default-keywords --output=./messages.pot --verbose ../cogs/

# Add messages
xgettext --omit-header --language=Python --add-comments=TRANSLATORS: --force-po -o ./messages.pot --join-existing -vvv ../cogs/*.py
xgettext --omit-header --language=Python --add-comments=TRANSLATORS: --force-po -o ./messages.pot --join-existing -vvv ../utils/*.py
xgettext --omit-header --language=Python --add-comments=TRANSLATORS: --force-po -o ./messages.pot --join-existing -vvv ../main.py

mv ./messages.pot ./en_US/LC_MESSAGES/messages.pot
#cp ./en_US/LC_MESSAGES/messages.pot ./en_US/LC_MESSAGES/messages.po

# pybabel init -l en -i ./messages.pot -d ./
# pybabel compile -d ./