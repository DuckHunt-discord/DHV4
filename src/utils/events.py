from enum import Enum, unique


# Fake translation
def _(string):
    return string


@unique
class Events(Enum):
    CALM = _("Everything is calm"), _("Nothing is happening right now.")

    MIGRATING = _("Ducks are migrating"), _(
        "Prepare to see more ducks in the next hour."
    )

    STEROIDS = _("Steroids in the lake"), _(
        "A medical waste company dumped steroids in the lake. Ducks have mutated, and you'll see a lot more super ducks. But, be careful, and don't drink that water."
    )

    SAFETY = _("Safety class canceled"), _(
        "The safety class was canceled, beware not to shoot other hunters!"
    )

    CONNECTION = _("Connection problem"), _(
        "Ducks cant find your computer due to connection problems, and there will be less of them until it's repaired."
    )

    FLORIST = _("A new florist in town"), _(
        "A florist opened in town, and you can now find better 4-leaf-clovers. Go check them out!"
    )

    MEGA_DUCKS = _("Mega-ducks"), _(
        "Someone inflated a super duck, and now they are EVEN BIGGER!!"
    )

    WINDY = _("Windy weather"), _("Bullets are deflected by some strong wind.")

    UN_TREATY = _("A UN treaty bans damaging ammo"), _(
        "AP and Explosive ammo are disabled. Super ducks are worth more exp, since they are getting rare."
    )

    EQUALIZER = _("Equalizer"), _(
        "Ducks are angered that long time hunters get prestige bonuses and are encouraged to kill even more of their families. "
        "They will steal some prestige bonuses when they can in order to ensure a fairer game for all."
    )

    HAUNTED_HOUSE = _("Haunted house"), _(
        "As it turns dark, the ducks also change with the times.  Be prepared to check if there’s a duck lurking in the corner!"
    )

    REVOLUTION = _("Duck revolution"), _("Beware! Ducks have obtained their own rifles, and will retaliate against hunters that shoot at them.")

    DUST_BOWL = _("Dust bowl"), _("A sandstorm has rolled in, causing the power of clovers to be weakened. "
                                  "It may also be difficult to buy new clovers due to the drought.")

    BONUS = _("Holiday bonus"), _("Claim your free gift! The first kill you do this hour will award you a lot of experience.")

    BLOSSOMING_FLOWERS = _("Blossoming flowers"), _("Flowers are blooming this season, so all four leaf clover values are increased for the hour. Enjoy the prosperity!")

    GARBAGE_COLLECTION = _("Garbage collection"), _("It's hunting season, and hunters left some items behind. "
                                                    "One person's trash can end up being your treasure, so enjoy the extra loot you find!")


