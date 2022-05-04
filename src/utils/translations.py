import gettext
from typing import Iterable, Optional

import polib

# Oldest first
TRANSLATORS = {
    "ar": [595682186452271108, 631821494774923264],
    "en_US": [138751484517941259],
    "da": [135446225565515776, 420619125887467531],
    "de": [296573428293697536, 394264447151243286, 632485754643415053, 285665580760170496, 455816405791670285, 549911100980723714, 570323095542431786],
    "es": [500550140201926656, 647608852883177492, 632485754643415053, 709131461374246932, 549911100980723714],
    "fr": [138751484517941259, 296573428293697536, 465207298890006529, 632485754643415053, 668349394529157131, 643504268267225118, 119872860440231936, 549911100980723714],
    "hu": [579324767216336923],
    "id": [856895619469672449],
    "it": [549911100980723714],
    "nl": [296573428293697536, 394264447151243286],
    "pt_BR": [397254384662085634, 233950490151485441],
    "ro": [756802315532501002, 376777684102938636],
    "ru": [773527955401474058],
    "sv": [416847496573353985],
    "sk": [403500416631046145],
    "tr": [338362273376501770],
    "zh": [790758041356206101, 354349329076584459, 628542777692782611],
    "zh-Hans": [790758041356206101, 354349329076584459, 628542777692782611, 570323095542431786],
}


def get_translation(language_code):
    return gettext.translation('messages', localedir='locales/', languages=[language_code], fallback=True)


def translate(message, language_code):
    return get_translation(language_code).gettext(message)


def ntranslate(singular, plural, n, language_code):
    return get_translation(language_code).ngettext(singular, plural, n)


def get_translate_function(bot_or_ctx, language_code, additional_kwargs=None):
    if additional_kwargs is None:
        additional_kwargs = {}

    def _(message, **kwargs):
        kwargs = {**additional_kwargs, **kwargs}
        translated_message = translate(message, language_code)
        try:
            formatted_message = translated_message.format(**kwargs)
        except KeyError:
            bot_or_ctx.logger.exception(f"Error formatting message {message} // {translated_message}")
            formatted_message = message.format(**kwargs)
        return formatted_message

    return _


def get_ntranslate_function(bot_or_ctx, language_code, additional_kwargs=None):
    if additional_kwargs is None:
        additional_kwargs = {}

    def ngettext(singular, plural, n, **kwargs):
        kwargs = {**additional_kwargs, "n": n, **kwargs}
        translated_message = ntranslate(singular, plural, n, language_code)
        try:
            formatted_message = translated_message.format(**kwargs)
        except KeyError:
            if n > 1:
                bot_or_ctx.logger.exception(f"Error formatting message (n={n}) {plural} // {translated_message}")
                formatted_message = plural.format(**kwargs)
            else:
                bot_or_ctx.logger.exception(f"Error formatting message (n={n}) {singular} // {translated_message}")
                formatted_message = singular.format(**kwargs)

        return formatted_message

    return ngettext


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
