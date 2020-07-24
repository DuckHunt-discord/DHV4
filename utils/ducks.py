import asyncio
import random
import time
from typing import Optional

import discord
from discord.utils import escape_markdown

from utils.bot_class import MyBot
from utils.interaction import get_webhook_if_possible, anti_bot_zero_width
from utils.models import DiscordMember, DiscordChannel, get_from_db, Player, get_player
from utils.translations import translate

DUCKS_IMAGES = {
    "emoji": "https://cdn.discordapp.com/attachments/734810933091762188/735588049596973066/duck.png",
    "glare": "https://cdn.discordapp.com/emojis/436542355257163777.png",
    "eyebrows": "https://cdn.discordapp.com/emojis/436542355504627712.png",
}


class Duck:
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

    async def get_spawn_message(self) -> str:
        _ = await self.get_translate_function()

        db_channel = await self.get_db_channel()

        traces = self.config['ascii'][self.ascii_art]['traces']

        if not db_channel.use_emojis:
            faces = self.config['ascii'][self.ascii_art]['faces']
        else:
            faces = self.config['ascii'][self.ascii_art]['emojis']

        shouts = self.config['ascii'][self.ascii_art]['shouts']

        trace = escape_markdown(random.choice(traces))
        if not db_channel.use_emojis:
            face = escape_markdown(random.choice(faces))
        else:
            face = random.choice(faces)

        shout = _(random.choice(shouts))

        return f"{anti_bot_zero_width(trace)} {face} {anti_bot_zero_width(shout)}"

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

    async def get_exp_value(self):
        db_channel = await self.get_db_channel()
        return db_channel.base_duck_exp + db_channel.per_life_exp * await self.get_lives()

    async def kill(self, damage:int):
        """The duck was killed by the current target player"""
        self.bot.ducks_spawned[self.channel].remove(self)

        killer = self.target_lock_by
        db_killer = self.db_target_lock_by

        await self.release()

        _ = await self.get_translate_function()

        # Increment killed by 1
        setattr(db_killer, self.get_killed_count_variable(), getattr(db_killer, self.get_killed_count_variable()) + 1)
        won_experience = await self.get_exp_value()
        db_killer.experience += won_experience + await db_killer.get_bonus_experience(won_experience)

        await db_killer.save()

        await self.send(_("{killer.mention} killed the duck blahblahblah", killer=killer))

    async def hurt(self, damage:int):
        hurter = self.target_lock_by
        db_hurter = self.db_target_lock_by

        await self.release()

        _ = await self.get_translate_function()

        await self.send(_("{hurter.mention} hurted the duck [SUPER DUCK fml, lives : -{damage}]",
                          hurter=hurter,
                          damage=damage))

    async def get_damage(self):
        return 1

    async def shoot(self):
        damage = await self.get_damage()

        if await self.damage(damage):
            await self.kill(damage)
        else:
            await self.hurt(damage)

    def get_killed_count_variable(self):
        return f"killed_{self.category}_ducks"


class SuperDuck(Duck):
    category = 'super'
    ascii_art = 'normal'

    def __init__(self, *args, lives: int = None, **kwargs):
        super().__init__(*args, **kwargs)

        self._lives = lives

    async def initial_set_lives(self):
        db_channel = await self.get_db_channel()
        self._lives = random.randint(db_channel.super_ducks_min_life, db_channel.super_ducks_max_life)

