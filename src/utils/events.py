# Fake translation
from enum import Enum, unique


def _(string):
    return string

@unique
class Events(Enum):
    CALM       = _("Everything is calm"), \
                 _("Nothing is happening right now.")

    MIGRATING  = _("Ducks are migrating"), \
                 _("Prepare to see more ducks in the next hour.")

    STEROIDS   = _("Steroids in the lake"), \
                 _("A medical waste company dumped steroids in the lake. Ducks have mutated, and you'll see a lot more super ducks. But, be careful, and don't drink that water.")

    SAFETY     = _("Safety class canceled"), \
                 _("The safety class was canceled, beware not to shoot other hunters!")

    CONNECTION = _("Connection problem"), \
                 _("Ducks cant find your computer due to connection problems, and there will be less of them until it's repaired.")

    FLORIST    = _("A new florist in town"), \
                 _("A florist opened in town, and you can now find better 4-leaf-clovers. Go check them out!")

    MEGA_DUCKS = _("Mega-ducks"), \
                 _("Someone inflated a super duck, and now they are EVEN BIGGER!!")

    WINDY      = _("Windy weather"), \
                 _("Bullets are deflected by some strong wind.")

    UN_TREATY  = _("A UN treaty bans damaging ammo"), \
                 _("AP and Explosive ammo are disabled. Super ducks are worth more exp, since they are getting rare.")

