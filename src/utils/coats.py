import random
from enum import Enum, unique


# Fake translation
from babel.lists import format_list
from discord.ext import commands


def _(string):
    return string


def get_random_coat_type():
    return random.choice(list(Coats))


@unique
class Coats(Enum):
    DEFAULT    = _("White"), \
                 _("A useful coat when it rains.")

    ORANGE     = _("Orange"), \
                 _("Better visibility: Increase your chance to frighten ducks, and reduce your chance to get shot by another hunter.")

    CAMO       = _("Camo"), \
                 _("Lower visibility: Less chance to frighten ducks.")

    BLUE       = _("Blue"), \
                 _("Lucky find: Increase your chance to find items in bushes.")

    RED        = _("Red"), \
                 _("Hungry for blood: Increase your murder skills, reduce murder penalties.")

    YELLOW     = _("Yellow"), \
                 _("Sun powers: Mirrors are less effective against you.")

    DARK_GREEN = _("Dark green"), \
                 _("Farming skills: Clovers give you one more experience point.")

    BLACK      = _("Black"), \
                 _("Secret service: Sabotages are cheaper.")

    # LMAO this is useless
    LIGHT_BLUE = _("Light blue"), \
                 _("Sea powers: You are immune to water buckets.")

    PINK       = _("Pink"), \
                 _("Power of love: You can't kill players with the same coat color.")

    @classmethod
    async def convert(cls, ctx, argument: str):
        if argument.upper() == "RANDOM":
            return None
        try:
            return getattr(cls, argument.upper().replace(' ', '_'))
        except AttributeError:
            _ = await ctx.get_translate_function()
            raise commands.BadArgument(_("This is not a valid color. "
                                         "You can choose between {colors}, or `random` for a random color.",
                                         colors=format_list(list(cls.__members__),
                                                            locale=await ctx.get_language_code())))
