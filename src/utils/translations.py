import gettext
from typing import Iterable, Optional

import polib

# Oldest first
TRANSLATORS = {
    "en_US": [138751484517941259],
    "da": [135446225565515776],
    "de": [296573428293697536, 394264447151243286, 632485754643415053],
    "es": [500550140201926656, 647608852883177492],
    "fr": [138751484517941259, 296573428293697536, 465207298890006529, 632485754643415053, 668349394529157131],
    "hu": [579324767216336923],
    "nl": [296573428293697536, 394264447151243286],
    "pt_BR": [520228168209137684],
    "ro": [756802315532501002],
    "ru": [773527955401474058],
    "zh": [750338409456992256, 354349329076584459],
    "zh-Hans": [750338409456992256, 354349329076584459],
}


def get_translation(language_code):
    return gettext.translation('messages', localedir='locales/', languages=[language_code], fallback=True)


def translate(message, language_code):
    return get_translation(language_code).gettext(message)


def ntranslate(singular, plural, n, language_code):
    return get_translation(language_code).ngettext(singular, plural, n)


def fake_translation(message, language_code=None):
    return message


def get_catalog(language_code) -> Optional[polib.POFile]:
    try:
        return polib.pofile(f"locales/{language_code}/LC_MESSAGES/messages.po")
    except FileNotFoundError:
        return None


def get_pct_complete(language_code) -> float:
    try:
        catalog = get_catalog(language_code)
    except OSError:
        catalog = None

    if not catalog:
        return float('NaN')

    return round(catalog.percent_translated())
