import gettext


def get_translation(language_code):
    return gettext.translation('bot', localedir='locales/', languages=[language_code], fallback=True)


def _(message, language_code):
    return get_translation(language_code).gettext(message)


def fake_translation(message, language_code=None):
    return message
