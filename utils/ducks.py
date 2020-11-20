import asyncio
import random
import time
from typing import Optional

import discord
import typing
from discord.utils import escape_markdown

from utils import config
from utils.bot_class import MyBot
from utils.interaction import get_webhook_if_possible, anti_bot_zero_width
from utils.models import DiscordChannel, get_from_db, Player, get_player
from utils.translations import translate
import utils.ducks_config as ducks_config


class Duck:
    """
    The standard duck. Kill it with the pan command
    """
    category = 'normal'
    fake = False  # Fake ducks only exists when they are alone on a channel. They are used for taunt messages, mostly.
    use_bonus_exp = True
    leave_on_hug = False

    def __init__(self, bot: MyBot, channel: discord.TextChannel):
        self.bot = bot
        self.channel = channel
        self._db_channel: Optional[DiscordChannel] = None

        self._webhook_parameters = {'avatar_url': random.choice(self.get_cosmetics()['avatar_urls']),
                                    'username': random.choice(self.get_cosmetics()['usernames'])}

        self.spawned_at: Optional[int] = None
        self.target_lock = asyncio.Lock()
        self.target_lock_by: Optional[discord.Member] = None
        self.db_target_lock_by: Optional[Player] = None

        self._lives: Optional[int] = None
        self.lives_left: Optional[int] = self._lives

    def get_cosmetics(self):
        return getattr(ducks_config, self.category)

    @property
    def spawned_for(self):
        if self.spawned_at:
            return max(time.time() - self.spawned_at, 0)
        return None

    async def is_killed(self):
        await self.get_lives()
        return self.lives_left <= 0

    # Database #

    async def get_translate_function(self):
        db_guild = await get_from_db(self.channel.guild)
        language = db_guild.language

        def _(message, **kwargs):
            return translate(message, language).format(**kwargs)

        return _

    async def get_db_channel(self):
        if not self._db_channel:
            self._db_channel = await get_from_db(self.channel)

        return self._db_channel

    async def get_webhook_parameters(self) -> dict:
        _ = await self.get_translate_function()
        webhook = self._webhook_parameters
        webhook['username'] = _(webhook['username'])
        return webhook

    async def get_exp_value(self) -> int:
        db_channel = await self.get_db_channel()
        return db_channel.base_duck_exp + db_channel.per_life_exp * await self.get_lives()

    async def increment_hurts(self):
        db_hurter = self.db_target_lock_by
        db_hurter.hurted[self.category] += 1

    async def increment_kills(self):
        db_killer = self.db_target_lock_by
        db_killer.killed[self.category] += 1

    async def increment_hugs(self):
        db_hugger = self.db_target_lock_by
        db_hugger.hugged[self.category] += 1

    async def increment_resists(self):
        db_hurter = self.db_target_lock_by
        db_hurter.resisted[self.category] += 1

    async def increment_frightens(self):
        db_frightener = self.db_target_lock_by
        db_frightener.frightened[self.category] += 1

    async def set_best_time(self):
        db_hunter = self.db_target_lock_by
        db_hunter.best_times[self.category] = min(self.spawned_for, db_hunter.best_times[self.category])

    # Locks #

    async def target(self, member: discord.Member = None):
        await self.target_lock.acquire()
        if member:
            self.target_lock_by = member
            self.db_target_lock_by = await get_player(member, self.channel)

        await self.get_db_channel()

    async def release(self):
        self.target_lock_by = None
        self.db_target_lock_by = None
        self.target_lock.release()

    # Messages #

    async def get_trace(self) -> str:
        traces = self.get_cosmetics()['traces']
        trace = escape_markdown(random.choice(traces))

        return anti_bot_zero_width(trace)

    async def get_face(self) -> str:
        db_channel = await self.get_db_channel()

        if not db_channel.use_emojis:
            faces = self.get_cosmetics()['faces']
            face = escape_markdown(random.choice(faces))
        else:
            faces = self.get_cosmetics()['emojis']
            face = random.choice(faces)

        return face

    async def get_shout(self) -> str:
        _ = await self.get_translate_function()
        shouts = self.get_cosmetics()['shouts']

        shout = _(random.choice(shouts))
        if "http" in shout:
            return shout
        else:
            return anti_bot_zero_width(shout)

    async def get_bye_trace(self):
        _ = await self.get_translate_function()
        traces = self.get_cosmetics()['bye_traces']

        trace = _(random.choice(traces))

        return anti_bot_zero_width(discord.utils.escape_markdown(trace))

    async def get_bye_shout(self):
        _ = await self.get_translate_function()
        shouts = self.get_cosmetics()['bye_shouts']

        shout = _(random.choice(shouts))

        return anti_bot_zero_width(shout)

    async def get_spawn_message(self) -> str:
        trace = await self.get_trace()
        face = await self.get_face()
        shout = await self.get_shout()

        return f"{trace} {face} {shout}"

    async def get_kill_message(self, killer, db_killer: Player, won_experience: int):
        _ = await self.get_translate_function()

        return _("{killer.mention} killed the duck [**Killed**: +{won_experience} exp]",
                 killer=killer,
                 won_experience=won_experience)

    async def get_hurt_message(self, hurter, db_hurter, damage):
        _ = await self.get_translate_function()

        return _("{hurter.mention} hurted the duck [**SUPER DUCK detected**][**Damage** : -{damage}]",
                 hurter=hurter,
                 damage=damage)

    async def get_resists_message(self, hurter, db_hurter):
        _ = await self.get_translate_function()

        return _("{hurter.mention}, the duck RESISTED. [**ARMORED DUCK detected**]",
                 hurter=hurter, )

    async def get_hug_message(self, hugger, db_hugger, experience):
        _ = await self.get_translate_function()
        if experience > 0:
            return _("{hugger.mention} hugged the duck. So cute! [**Hug**: +{experience} exp]",
                     hugger=hugger,
                     experience=experience,
                     )
        else:
            return _("{hugger.mention} tried to hug the duck. So cute! Unfortunately, the duck hates you, because you killed all his family. [**FAIL**: {experience} exp]",
                     hugger=hugger,
                     experience=experience,
                     )

    async def get_left_message(self) -> str:
        trace = await self.get_bye_trace()
        shout = await self.get_bye_shout()

        return f"{trace} {shout}"

    async def send(self, message: str):
        webhook = await get_webhook_if_possible(self.bot, self.channel)

        if webhook:
            this_webhook_parameters = await self.get_webhook_parameters()
            try:
                await webhook.send(message, **this_webhook_parameters)
                return
            except discord.NotFound:
                db_channel: DiscordChannel = await get_from_db(self.channel)
                db_channel.webhook_urls.remove(webhook.url)
                await db_channel.save()

                pass
        await self.channel.send(message)

    # Parameters #

    async def get_time_left(self) -> float:
        db_channel = await self.get_db_channel()

        should_disappear_after = db_channel.ducks_time_to_live
        return should_disappear_after - self.spawned_for

    async def initial_set_lives(self):
        self._lives = 1

    async def get_lives(self):
        if not self._lives:
            await self.initial_set_lives()
            self.lives_left = self._lives
        return self._lives

    async def get_damage(self):
        db_hugger = self.db_target_lock_by
        if db_hugger.is_powerup_active('explosive_ammo'):
            return 3
        elif db_hugger.is_powerup_active('ap_ammo'):
            return 2
        else:
            return 1

    async def get_hug_experience(self):
        return -2

    async def will_frighten(self):
        db_channel = await self.get_db_channel()
        frighten_chance = db_channel.duck_frighten_chance
        return random.randint(1, 100) <= frighten_chance

    # Entry Points #

    async def spawn(self):
        total_lives = await self.get_lives()

        bot = self.bot
        message = await self.get_spawn_message()

        self.bot.logger.debug(f"Spawning {self}", guild=self.channel.guild, channel=self.channel)

        await self.send(message)

        bot.ducks_spawned[self.channel].append(self)

        self.spawned_at = time.time()

    async def shoot(self, args):
        if await self.will_frighten():
            return await self.frighten()

        damage = await self.get_damage()

        if await self.damage(damage):
            await self.kill(damage, args)
        else:
            await self.hurt(damage, args)

    async def hug(self, args):
        if self.leave_on_hug:
            self.despawn()
            await self.set_best_time()

        hugger = self.target_lock_by
        db_hugger = self.db_target_lock_by

        experience = await self.get_hug_experience()
        await self.increment_hugs()
        await self.release()

        db_hugger.experience += experience

        await db_hugger.save()

        _ = await self.get_translate_function()
        await self.send(await self.get_hug_message(hugger, db_hugger, experience))

    async def leave(self):
        self.bot.logger.debug(f"Leaving {self}", guild=self.channel.guild, channel=self.channel)

        await self.send(await self.get_left_message())
        self.despawn()

    async def maybe_leave(self):
        db_channel = await self.get_db_channel()
        if db_channel.ducks_time_to_live < self.spawned_for:
            await self.leave()
            return True
        else:
            return False

    # Actions #
    async def frighten(self):
        hunter = self.target_lock_by
        db_hunter = self.db_target_lock_by
        await self.increment_frightens()
        await self.release()

        await db_hunter.save()

    async def kill(self, damage: int, args):
        """The duck was killed by the current target player"""
        self.despawn()
        await self.set_best_time()

        killer = self.target_lock_by
        db_killer = self.db_target_lock_by
        await self.increment_kills()
        await self.release()

        _ = await self.get_translate_function()

        # Increment killed by 1
        won_experience = await self.get_exp_value()

        if self.use_bonus_exp:
            won_experience += await db_killer.get_bonus_experience(won_experience)

        db_killer.experience += won_experience

        await db_killer.save()

        await self.send(await self.get_kill_message(killer, db_killer, won_experience))
        await self.post_kill()

    async def hurt(self, damage: int, args):
        hurter = self.target_lock_by
        db_hurter = self.db_target_lock_by

        if damage:
            await self.increment_hurts()
            await self.send(await self.get_hurt_message(hurter, db_hurter, damage))
        else:
            await self.increment_resists()
            await self.send(await self.get_resists_message(hurter, db_hurter))

        await self.release()
        await db_hurter.save()

    # Utilities #

    def despawn(self):
        self.bot.ducks_spawned[self.channel].remove(self)

    async def damage(self, lives):
        """
        This function remove lives from a duck and returns True if the duck was killed, False otherwise
        """
        self.lives_left = self.lives_left - lives
        return await self.is_killed()

    async def post_kill(self):
        """
        Just in case you want to do something after a duck died.
        """

    def __repr__(self):
        attributes = []
        if self.lives_left <= 0:  # No await
            attributes.append("killed")
        if self in self.bot.ducks_spawned[self.channel]:
            attributes.append("spawned")

        total_lives = self._lives  # We can't await here, so try our best

        return f"<{type(self).__name__}{' '.join(attributes)} lives={self.lives_left}/{total_lives}>"


# Standard ducks #


class GhostDuck(Duck):
    """
    A rare duck that does *not* say anything when it spawns.
    """
    category = 'ghost'
    fake = False  # Fake ducks only exists when they are alone on a channel. They are used for taunt messages, mostly.

    async def spawn(self):
        total_lives = await self.get_lives()

        bot = self.bot

        bot.ducks_spawned[self.channel].append(self)

        self.spawned_at = time.time()


class PrDuck(Duck):
    category = 'prof'

    def __init__(self, bot: MyBot, channel: discord.TextChannel):
        super().__init__(bot, channel)
        r1 = random.randint(0, 100)
        r2 = random.randint(0, 100)
        self.operation = f"{r1} + {r2}"
        self.answer = r1 + r2

    async def get_shout(self) -> str:
        _ = await self.get_translate_function()

        return _("Huh, quick question, what's {operation} ?", operation=self.operation)

    async def shoot(self, args: list):
        _ = await self.get_translate_function()
        hurter = self.target_lock_by

        try:
            result = int(args[0])
        except IndexError:
            await self.send(_("{hurter.mention}, I asked you a question ! What's {operation} ?",
                              hurter=hurter,
                              operation=self.operation))
            await self.release()
            return
        except ValueError:
            await self.send(_("{hurter.mention}, Just give me digits !",
                              hurter=hurter))
            await self.release()
            return

        if result != self.answer:
            await self.send(_("{hurter.mention}, that's not the correct answer !",
                              hurter=hurter))
            await self.release()
            return
        else:
            await super().shoot(args)


class BabyDuck(Duck):
    """
    A baby duck. You shouldn't kill a baby duck. If you do, your exp will suffer.
    """
    category = 'baby'
    leave_on_hug = True

    async def get_kill_message(self, killer, db_killer: Player, won_experience: int):
        _ = await self.get_translate_function()
        return _("{killer.mention} killed the duck baby snif", killer=killer)

    async def get_exp_value(self):
        return - await super().get_exp_value()

    async def get_hug_experience(self):
        return 5


class GoldenDuck(Duck):
    category = 'golden'

    async def get_exp_value(self):
        return await super().get_exp_value() * 2


class PlasticDuck(Duck):
    category = 'plastic'

    async def get_exp_value(self):
        return await super().get_exp_value() * 0.5


class KamikazeDuck(Duck):
    category = 'kamikaze'

    async def leave(self):
        await self.send(await self.get_left_message())
        self.bot.ducks_spawned[self.channel].clear()


class MechanicalDuck(Duck):
    category = 'mechanical'
    fake = True
    use_bonus_exp = False

    def __init__(self, *args, creator: Optional[discord.Member] = None, **kwargs):
        super().__init__(*args, **kwargs)

        self.creator = creator

    async def get_exp_value(self):
        return -10

    async def get_kill_message(self, killer, db_killer, won_experience):
        _ = await self.get_translate_function()

        creator = self.creator
        if not creator:
            return _("Damn, {killer.mention}, you suck! You killed a mechanical duck! I wonder who made it? [exp: {won_experience}]",
                     killer=killer,
                     won_experience=won_experience)
        else:
            return _("Damn, {killer.mention}, you suck! You killed a mechanical duck! All of this is {creator.mention}'s fault! [exp: {won_experience}]",
                     killer=killer,
                     won_experience=won_experience,
                     creator=creator)


# Super ducks #

class SuperDuck(Duck):
    """
    A duck with many lives to spare.
    """
    category = 'super'

    def __init__(self, *args, lives: int = None, **kwargs):
        super().__init__(*args, **kwargs)

        self._lives = lives

    async def initial_set_lives(self):
        db_channel = await self.get_db_channel()
        self._lives = random.randint(db_channel.super_ducks_min_life, db_channel.super_ducks_max_life)


class MotherOfAllDucks(SuperDuck):
    """
    This duck will spawn two more when she dies.
    """
    category = 'moad'

    async def post_kill(self):
        for i in range(2):
            await spawn_random_weighted_duck(self.bot, self.channel)


class ArmoredDuck(SuperDuck):
    category = 'armored'

    async def get_damage(self):
        minus = 0
        if random.randint(0, 100) < 90:
            minus = 1

        return await super().get_damage() - minus


RANDOM_SPAWN_DUCKS_CLASSES = [Duck, GhostDuck, PrDuck, BabyDuck, GoldenDuck, PlasticDuck, KamikazeDuck, MechanicalDuck, SuperDuck, MotherOfAllDucks, ArmoredDuck]
DUCKS_CATEGORIES_TO_CLASSES = {dc.category: dc for dc in RANDOM_SPAWN_DUCKS_CLASSES}
DUCKS_CATEGORIES = [dc.category for dc in RANDOM_SPAWN_DUCKS_CLASSES]


async def spawn_random_weighted_duck(bot: MyBot, channel: discord.TextChannel):
    duck = await get_random_weighted_duck(bot, channel)
    await duck.spawn()
    return duck


async def get_random_weighted_duck(bot: MyBot, channel: discord.TextChannel):
    db_channel = await get_from_db(channel)
    weights = [getattr(db_channel, f"spawn_weight_{category}_ducks") for category in DUCKS_CATEGORIES]
    # noinspection PyPep8Naming
    DuckClass: typing.Type[Duck] = random.choices(RANDOM_SPAWN_DUCKS_CLASSES, weights)[0]

    return DuckClass(bot, channel)


