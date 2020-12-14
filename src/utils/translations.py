import gettext
from typing import Iterable, Optional

import polib

# Oldest first
TRANSLATORS = {
    "en_US": [138751484517941259],
    "fr": [138751484517941259, 296573428293697536, 465207298890006529],
    "nl": [296573428293697536, 394264447151243286],
    "de": [296573428293697536, 394264447151243286],
    "ro": [756802315532501002],
    "da": [135446225565515776],
    "pt_BR": [520228168209137684],
    "hu": [579324767216336923],
}


def get_translation(language_code):
    return gettext.translation('messages', localedir='locales/', languages=[language_code], fallback=True)


def translate(message, language_code):
    return get_translation(language_code).gettext(message)


def fake_translation(message, language_code=None):
    return message


def get_catalog(language_code) -> Optional[polib.POFile]:
    try:
        return polib.pofile(f"locales/{language_code}/LC_MESSAGES/messages.po")
    except FileNotFoundError:
        return None


def get_pct_complete(language_code) -> float:
    catalog = get_catalog(language_code)

    if not catalog:
        return float('NaN')

    return round(catalog.percent_translated())
