import asyncio
import random
import time
from typing import Optional

import discord
from discord.utils import escape_markdown

from utils.bot_class import MyBot
from utils.interaction import get_webhook_if_possible, anti_bot_zero_width
from utils.models import DiscordMember, DiscordChannel, get_from_db, Player, get_player

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

    async def target(self, member: discord.Member):
        await self.target_lock.acquire()
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
        db_channel = await self.get_db_channel()

        traces = self.config['ascii'][self.category]['traces']

        if not db_channel.use_emojis:
            faces = self.config['ascii'][self.category]['faces']
        else:
            faces = self.config['ascii'][self.category]['emojis']

        shouts = self.config['ascii'][self.category]['shouts']

        trace = escape_markdown(random.choice(traces))
        if not db_channel.use_emojis:
            face = escape_markdown(random.choice(faces))
        else:
            face = random.choice(faces)

        shout = random.choice(shouts)

        return f"{anti_bot_zero_width(trace)} {face} {anti_bot_zero_width(shout)}"

    async def get_webhook_parameters(self) -> dict:
        return self._webhook_parameters

    async def set_lives(self):
        self._lives = 1

    async def get_lives(self):
        if not self._lives:
            await self.set_lives()
            self.lives_left = self._lives
        return self._lives

    async def get_time_left(self) -> float:
        db_channel = await self.get_db_channel()

        should_disappear_after = db_channel.ducks_time_to_live
        return should_disappear_after - self.spawned_for

    async def spawn(self):
        bot = self.bot
        channel = self.channel
        message = await self.get_spawn_message()
        webhook = await get_webhook_if_possible(bot, channel)

        await self.get_lives()


        if webhook:
            this_webhook_parameters = await self.get_webhook_parameters()
            await webhook.send(message, **this_webhook_parameters)
        else:
            await channel.send(message)

        self.spawned_at = time.time()

    async def get_exp_value(self):
        db_channel = await self.get_db_channel()
        return db_channel.base_duck_exp + db_channel.per_life_exp * await self.get_lives()

    async def kill(self):
        """The duck was killed by the current target player"""

        # Increment killed by 1
        setattr(self.db_target_lock_by, self.get_killed_count_variable(), getattr(self.db_target_lock_by, self.get_killed_count_variable()) + 1)
        won_experience = await self.get_exp_value()
        self.db_target_lock_by.experience += won_experience + await self.db_target_lock_by.get_bonus_experience(won_experience)

    def get_killed_count_variable(self):
        return f"killed_{self.category}_ducks"


class SuperDuck(Duck):
    category = 'super'
    ascii_art = 'normal'

    def __init__(self, *args, lives: int = None, **kwargs):
        super().__init__(*args, **kwargs)

        self._lives = lives

    async def set_lives(self):
        db_channel = await self.get_db_channel()
        self._lives = random.randint(db_channel.super_ducks_min_life, db_channel.super_ducks_max_life)




