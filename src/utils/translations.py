import gettext
from typing import Optional

import polib

# Oldest first
TRANSLATORS = {
    "ar": {
        "flag_code": "🇸🇦",
        "user_ids": [595682186452271108, 631821494774923264, 588832324745953283],
    },
    "en_US": {"flag_code": "🇺🇸", "user_ids": [138751484517941259]},
    "da": {"flag_code": "🇩🇰", "user_ids": [135446225565515776, 420619125887467531]},
    "de": {
        "flag_code": "🇩🇪",
        "user_ids": [
            296573428293697536,
            394264447151243286,
            632485754643415053,
            285665580760170496,
            455816405791670285,
            549911100980723714,
            570323095542431786,
        ],
    },
    "es": {
        "flag_code": "🇪🇸",
        "user_ids": [
            500550140201926656,
            647608852883177492,
            632485754643415053,
            709131461374246932,
            549911100980723714,
        ],
    },
    "fr": {
        "flag_code": "🇫🇷",
        "user_ids": [
            138751484517941259,
            296573428293697536,
            465207298890006529,
            632485754643415053,
            668349394529157131,
            643504268267225118,
            119872860440231936,
            549911100980723714,
        ],
    },
    "hu": {"flag_code": "🇭🇺", "user_ids": [579324767216336923]},
    "id": {"flag_code": "🇮🇩", "user_ids": [856895619469672449]},
    "it": {"flag_code": "🇮🇹", "user_ids": [549911100980723714, 1062744087259791432]},
    "nl": {"flag_code": "🇳🇱", "user_ids": [296573428293697536, 394264447151243286]},
    "pl": {"flag_code": "🇵🇱", "user_ids": [498474233136152597]},
    "pt_BR": {"flag_code": "🇧🇷", "user_ids": [397254384662085634, 233950490151485441]},
    "ro": {"flag_code": "🇷🇴", "user_ids": [756802315532501002, 376777684102938636]},
    "ru": {"flag_code": "🇷🇺", "user_ids": [773527955401474058]},
    "sv": {"flag_code": "🇸🇪", "user_ids": [416847496573353985]},
    "sk": {"flag_code": "🇸🇰", "user_ids": [403500416631046145]},
    "tr": {"flag_code": "🇹🇷", "user_ids": [338362273376501770]},
    "uk": {"flag_code": "🇺🇦", "user_ids": [350955973311201282]},
    "zh": {
        "flag_code": "🇨🇳",
        "user_ids": [790758041356206101, 354349329076584459, 628542777692782611],
    },
    "zh-Hans": {
        "flag_code": "🇨🇳",
        "user_ids": [
            790758041356206101,
            354349329076584459,
            628542777692782611,
            570323095542431786,
        ],
    },
}


def get_translation(language_code):
    return gettext.translation(
        "messages", localedir="locales/", languages=[language_code], fallback=True
    )


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
            bot_or_ctx.logger.exception(
                f"Error formatting message {message} // {translated_message}"
            )
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
                bot_or_ctx.logger.exception(
                    f"Error formatting message (n={n}) {plural} // {translated_message}"
                )
                formatted_message = plural.format(**kwargs)
            else:
                bot_or_ctx.logger.exception(
                    f"Error formatting message (n={n}) {singular} // {translated_message}"
                )
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
        return float("NaN")

    return round(catalog.percent_translated())
