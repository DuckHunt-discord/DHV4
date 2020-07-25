import asyncio
import random
import time
from typing import Optional

import discord
from discord.utils import escape_markdown

from utils.bot_class import MyBot
from utils.interaction import get_webhook_if_possible, anti_bot_zero_width
from utils.models import DiscordChannel, get_from_db, Player, get_player
from utils.translations import translate

DUCKS_IMAGES = {
    "emoji": "https://cdn.discordapp.com/attachments/734810933091762188/735588049596973066/duck.png",
    "glare": "https://cdn.discordapp.com/emojis/436542355257163777.png",
    "eyebrows": "https://cdn.discordapp.com/emojis/436542355504627712.png",
}


class Duck:
    """
    The standard duck. Kill it with the pan command
    """
    category = 'normal'
    ascii_art = category
    fake = False  # Fake ducks only exists when they are alone on a channel. They are used for taunt messages, mostly.

    def __init__(self, bot: MyBot, channel: discord.TextChannel):
        self.bot = bot
        self.config = bot.config['ducks']
        self.channel = channel
        self._db_channel: Optional[DiscordChannel] = None

        self._webhook_parameters = random.choice(self.config['webhooks_parameters'][self.category]).copy()
        self._webhook_parameters['avatar_url'] = self.config['images'][self._webhook_parameters['avatar_url']]
        self.spawned_at: Optional[int] = None
        self.target_lock = asyncio.Lock()
        self.target_lock_by: Optional[discord.Member] = None
        self.db_target_lock_by: Optional[Player] = None

        self._lives: Optional[int] = None
        self.lives_left: Optional[int] = self._lives

    async def get_translate_function(self):
        db_guild = await get_from_db(self.channel.guild)
        language = db_guild.language

        def _(message, **kwargs):
            return translate(message, language).format(**kwargs)

        return _

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

    async def get_db_channel(self):
        if not self._db_channel:
            self._db_channel = await get_from_db(self.channel)

        return self._db_channel

    @property
    def spawned_for(self):
        if self.spawned_at:
            return max(time.time() - self.spawned_at, 0)
        return None

    async def get_trace(self) -> str:
        traces = self.config['ascii'][self.ascii_art]['traces']
        trace = escape_markdown(random.choice(traces))

        return anti_bot_zero_width(trace)

    async def get_face(self) -> str:
        db_channel = await self.get_db_channel()

        if not db_channel.use_emojis:
            faces = self.config['ascii'][self.ascii_art]['faces']
            face = escape_markdown(random.choice(faces))
        else:
            faces = self.config['ascii'][self.ascii_art]['emojis']
            face = random.choice(faces)

        return face

    async def get_shout(self) -> str:
        _ = await self.get_translate_function()
        shouts = self.config['ascii'][self.ascii_art]['shouts']

        shout = _(random.choice(shouts))
        return anti_bot_zero_width(shout)

    async def get_spawn_message(self) -> str:
        trace = await self.get_trace()
        face = await self.get_face()
        shout = await self.get_shout()

        return f"{trace} {face} {shout}"

    async def get_kill_message(self, killer, db_killer):
        _ = await self.get_translate_function()

        return _("{killer.mention} killed the duck blahblahblah", killer=killer)

    async def get_hurt_message(self, hurter, db_hurter, damage):
        _ = await self.get_translate_function()

        return _("{hurter.mention} hurted the duck [SUPER DUCK fml, lives : -{damage}]",
                 hurter=hurter,
                 damage=damage)

    async def get_hug_message(self, hugger, db_hugger):
        _ = await self.get_translate_function()

        return _("{hugger.mention} hugged the duck and lost exp, I guess ?",
                 hugger=hugger
                 )

    async def get_webhook_parameters(self) -> dict:
        return self._webhook_parameters

    async def initial_set_lives(self):
        self._lives = 1

    async def get_lives(self):
        if not self._lives:
            await self.initial_set_lives()
            self.lives_left = self._lives
        return self._lives

    async def is_killed(self):
        return self.lives_left <= 0

    async def damage(self, lives):
        """
        This function remove lives from a duck and returns True if the duck was killed, False otherwise
        """
        self.lives_left = self.lives_left - lives
        return await self.is_killed()

    async def get_time_left(self) -> float:
        db_channel = await self.get_db_channel()

        should_disappear_after = db_channel.ducks_time_to_live
        return should_disappear_after - self.spawned_for

    async def send(self, message: str):
        webhook = await get_webhook_if_possible(self.bot, self.channel)

        if webhook:
            this_webhook_parameters = await self.get_webhook_parameters()
            await webhook.send(message, **this_webhook_parameters)
        else:
            await self.channel.send(message)

    async def spawn(self):
        total_lives = await self.get_lives()

        bot = self.bot
        message = await self.get_spawn_message()

        await self.send(message)

        bot.ducks_spawned[self.channel].append(self)

        self.spawned_at = time.time()

    def despawn(self):
        self.bot.ducks_spawned[self.channel].remove(self)

    async def get_exp_value(self):
        db_channel = await self.get_db_channel()
        return db_channel.base_duck_exp + db_channel.per_life_exp * await self.get_lives()

    async def post_kill(self):
        """
        Just in case youwant to do something after a duck died.
        """

    async def kill(self, damage: int, args):
        """The duck was killed by the current target player"""
        self.despawn()

        killer = self.target_lock_by
        db_killer = self.db_target_lock_by
        await self.increment_kills()
        await self.release()

        _ = await self.get_translate_function()

        # Increment killed by 1
        won_experience = await self.get_exp_value()
        db_killer.experience += won_experience + await db_killer.get_bonus_experience(won_experience)

        await db_killer.save()

        await self.send(await self.get_kill_message(killer, db_killer))
        await self.post_kill()

    async def hurt(self, damage: int, args):
        hurter = self.target_lock_by
        db_hurter = self.db_target_lock_by

        await self.increment_hurts()

        await self.release()

        _ = await self.get_translate_function()

        await self.send(await self.get_hurt_message(hurter, db_hurter, damage))

    async def get_damage(self):
        return 1

    async def hug(self, args):
        hugger = self.target_lock_by
        db_hugger = self.db_target_lock_by

        await self.increment_hugs()
        await self.release()

        _ = await self.get_translate_function()
        await self.send(await self.get_hug_message(hugger, db_hugger))

    async def shoot(self, args):
        damage = await self.get_damage()

        if await self.damage(damage):
            await self.kill(damage, args)
        else:
            await self.hurt(damage, args)

    async def increment_hurts(self):
        db_hurter = self.db_target_lock_by
        setattr(db_hurter, self.get_hurted_count_variable(), getattr(db_hurter, self.get_hurted_count_variable()) + 1)

    async def increment_kills(self):
        db_killer = self.db_target_lock_by
        setattr(db_killer, self.get_killed_count_variable(), getattr(db_killer, self.get_killed_count_variable()) + 1)

    async def increment_hugs(self):
        db_hugger = self.db_target_lock_by
        setattr(db_hugger, self.get_hugged_count_variable(), getattr(db_hugger, self.get_hugged_count_variable()) + 1)

    def get_hurted_count_variable(self):
        return f"hurted_{self.category}_ducks"

    def get_killed_count_variable(self):
        return f"killed_{self.category}_ducks"

    def get_hugged_count_variable(self):
        return f"hugged_{self.category}_ducks"


class GhostDuck(Duck):
    """
    A rare duck that does *not* say anything when it spawns.
    """
    category = 'ghost'
    ascii_art = category
    fake = False  # Fake ducks only exists when they are alone on a channel. They are used for taunt messages, mostly.

    async def spawn(self):
        total_lives = await self.get_lives()

        bot = self.bot

        bot.ducks_spawned[self.channel].append(self)

        self.spawned_at = time.time()


class PrDuck(Duck):
    category = 'prof'
    ascii_art = 'normal'

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
            await self.send(_("{hurter.mention}, I asked you a question !",
                              hurter=hurter))
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
    ascii_art = 'normal'

    async def kill(self, damage: int, args):
        """
        You shouldn't kill a baby duck
        """
        self.despawn()

        killer = self.target_lock_by
        db_killer = self.db_target_lock_by

        await self.increment_kills()
        await self.release()

        _ = await self.get_translate_function()

        # Increment killed by 1
        setattr(db_killer, self.get_killed_count_variable(), getattr(db_killer, self.get_killed_count_variable()) + 1)
        won_experience = await self.get_exp_value()
        db_killer.experience -= won_experience

        await db_killer.save()

        await self.send(_("{killer.mention} killed the duck baby snif", killer=killer))
        await self.post_kill()

    async def hug(self, args):
        hugger = self.target_lock_by
        db_hugger = self.db_target_lock_by
        await self.increment_hugs()
        await self.release()

        _ = await self.get_translate_function()

        await self.send(_("{hugger.mention} hugged the duck and won exp, I guess ?",
                          hugger=hugger
                          ))


class SuperDuck(Duck):
    """
    A duck with many lives to spare.
    """
    category = 'super'
    ascii_art = 'normal'

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
            await spawn_random_weighted_duck(self.channel)


async def spawn_random_weighted_duck(channel: discord.TextChannel):
    pass
