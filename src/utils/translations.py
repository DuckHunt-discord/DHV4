import gettext
from typing import Iterable, Optional

from babel.messages import Catalog, Message
from babel.messages.mofile import read_mo

# Oldest first
TRANSLATORS = {
    "en_US": [138751484517941259],
    "fr": [138751484517941259, 465207298890006529],
    "nl": [394264447151243286],
    "de": [394264447151243286],
    "ro": [756802315532501002],
}


def get_translation(language_code):
    return gettext.translation('messages', localedir='locales/', languages=[language_code], fallback=True)


def translate(message, language_code):
    return get_translation(language_code).gettext(message)


def fake_translation(message, language_code=None):
    return message


def get_catalog(language_code) -> Optional[Catalog]:
    try:
        with open(f"locales/{language_code}/LC_MESSAGES/messages.mo", "rb") as f:
            return read_mo(f)
    except FileNotFoundError:
        return None


def get_pct_complete(language_code) -> float:
    catalog = get_catalog(language_code)

    if not catalog:
        return float('NaN')

    filled = 0

    for message in catalog:
        if len(message.string.strip()):
            filled += 1

    return round(filled / len(catalog) * 100)
