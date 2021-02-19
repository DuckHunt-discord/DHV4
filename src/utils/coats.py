from enum import Enum, unique

# Fake translation
def _(string):
    return string


@unique
class Coats(Enum):
    DEFAULT    = _("Basic"), \
                 _("A useful coat when it rains.")

    ORANGE     = _("Orange"), \
                 _("Better visibility: Increase your chance to frighten ducks, and reduce your chance to get shot by another hunter.")

    CAMO       = _("Camo"), \
                 _("Lower visibility: Increase your chance to get shot by another hunter, but less chance to frighten ducks.")

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