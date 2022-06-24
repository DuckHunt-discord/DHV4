# Fake translation
import time

from utils.images import get_random_image
from utils.models import DiscordMember, Player

SECOND = 1
MINUTE = 60 * SECOND
HOUR = 60 * MINUTE
DAY = 24 * HOUR



def _(string):
    return string


class BushObject:
    name = None
    db = 'trash'
    took_message = _('Searching the bushes around the duck, you found... **Some trash lying around**.')
    left_message = _('Searching the bushes around the duck, you found... **Some trash lying around**. '
                     'You didn\'t take it, you had already too many...')

    async def send_args(self, _, result: bool):
        if result:
            return {'content': _(self.took_message)}
        else:
            return {'content': _(self.left_message)}

    async def give(self, db_channel, db_hunter):
        """
        Try and give the item if possible, then returns True. If not possible (inventory full), return False
        """
        return True


class Nothing(BushObject):
    db = 'trash_nothing'
    took_message = _('Searching the bushes around the duck, you found... **Nothing**.')


class Bushes(BushObject):
    db = 'trash_bushes'
    took_message = _('Searching the bushes around the duck, you found... **A lot of bushes**.')


class USBCCharger(BushObject):
    db = 'trash_usbc_charger'
    # TRANSLATORS: This is a joke message that probably only works in French, but try to adapt anyway.
    #  When translating to french, a magazine is the same as a power supply/a charger,
    #  so this might make people happy for a second.
    #  Yes, I am indeed cruel.
    took_message = _('Searching the bushes around the duck, you found... **An USB-C charger**.')


class DuckPin(BushObject):
    db = 'trash_pin'
    took_message = _('Searching the bushes around the duck, you found... **A rare duck pin**.')


class Picture(BushObject):
    db = 'trash_picture'
    took_message = _('Searching the bushes around the duck, you found... **A picture of a duck**.')

    async def send_args(self, _, result: bool):
        return {'content': _(self.took_message), 'file': get_random_image()}


class Bullet(BushObject):
    db = 'bullet'
    took_message = _('Searching the bushes around the duck, you found... **A bullet**.')
    left_message = _('Searching the bushes around the duck, you found... **A bullet**. '
                     'You didn\'t take it, you had already too many in your magazine anyway...')

    async def give(self, db_channel, db_hunter):
        level_info = db_hunter.level_info()

        max_bullets = level_info['bullets']
        if db_hunter.bullets >= max_bullets:
            return False
        else:
            db_hunter.bullets += 1
            return True


class Magazine(BushObject):
    db = 'magazine'
    took_message = _('Searching the bushes around the duck, you found... **A magazine**.')
    left_message = _('Searching the bushes around the duck, you found... **A magazine**. '
                     'You didn\'t take it, you had already too many in your backpack...')

    async def give(self, db_channel, db_hunter):
        level_info = db_hunter.level_info()

        max_magazines = level_info['magazines']
        if db_hunter.magazines >= max_magazines:
            return False
        else:
            db_hunter.magazines += 1
            return True


class ExplosiveAmmo(BushObject):
    db = 'explosive_ammo'
    took_message = _('Searching the bushes around the duck, you found... **A box of explosive ammo**. 💥')

    async def give(self, db_channel, db_hunter):
        db_hunter.active_powerups["explosive_ammo"] = max(int(time.time()), db_hunter.active_powerups["explosive_ammo"]) + DAY
        return True


class PartialExplosiveAmmo(BushObject):
    db = 'partial_explosive_ammo'
    took_message = _('Searching the bushes around the duck, you found... **An almost empty box of explosive ammo**.')

    async def give(self, db_channel, db_hunter):
        db_hunter.active_powerups["explosive_ammo"] = max(int(time.time()), db_hunter.active_powerups["explosive_ammo"]) + 6 * HOUR
        return True


class Grease(BushObject):
    db = 'grease'
    took_message = _('Searching the bushes around the duck, you found... **Tons of Duck Grease**.')

    async def give(self, db_channel, db_hunter):
        db_hunter.active_powerups["grease"] = max(int(time.time()), db_hunter.active_powerups["grease"]) + 2 * DAY
        return True


class Silencer(BushObject):
    db = 'silencer'
    took_message = _('Searching the bushes around the duck, you found... **A new silencer**.')

    async def give(self, db_channel, db_hunter: Player):
        db_hunter.active_powerups["silencer"] = max(int(time.time()), db_hunter.active_powerups["silencer"]) + DAY
        if db_hunter.prestige >= 6:
            db_hunter.active_powerups["silencer"] += DAY
        return True


class InfraredDetector(BushObject):
    db = 'detector'
    took_message = _('Searching the bushes around the duck, you found... **An infrared detector**.')

    async def give(self, db_channel, db_hunter):
        db_hunter.active_powerups["detector"] += 6
        return True


del _

# noinspection PyInterpreter
bushes = {
    Nothing: 20, Bushes: 20, Picture: 15,  USBCCharger: 3, DuckPin: 1,
    Bullet: 20,
    Magazine: 15,
    ExplosiveAmmo: 2, PartialExplosiveAmmo: 6,
    Grease: 15,
    Silencer: 7,
    InfraredDetector: 7,
 }


bushes_objects = []
bushes_weights = []

for object_, weight in bushes.items():
    bushes_objects.append(object_)
    bushes_weights.append(weight)
