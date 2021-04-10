#!/usr/bin/env bash
# pybabel extract -o messages.pot ../
xgettext --language=Python --add-comments=TRANSLATORS: --force-po -o ./messages.pot -vv ../**/*.py

# pybabel init -l en -i ./messages.pot -d ./
# pybabel compile -d ./
