import gettext


def get_translation(language_code):
    return gettext.translation('messages', localedir='locales/', languages=[language_code], fallback=True)


def translate(message, language_code):
    return get_translation(language_code).gettext(message)


def fake_translation(message, language_code=None):
    return message
