import asyncio
import collections
import datetime
from typing import Optional

import aiohttp
import discord
from discord.ext.commands.bot import AutoShardedBot
from discord.ext import commands

from utils import config as config
from utils.ctx_class import MyContext
from utils.logger import FakeLogger
from utils.models import get_from_db


class MyBot(AutoShardedBot):
    def __init__(self, *args, **kwargs):
        self.logger = FakeLogger()
        self.config: dict = {}
        self.reload_config()
        activity = discord.Game(self.config["bot"]["playing"])
        super().__init__(*args, command_prefix=get_prefix, activity=activity, case_insensitive=self.config["bot"]["commands_are_case_insensitive"], **kwargs)
        self.commands_used = collections.Counter()
        self.uptime = datetime.datetime.utcnow()
        self.shards_ready = set()
        self._client_session: Optional[aiohttp.ClientSession] = None
        asyncio.ensure_future(self.async_setup())

    @property
    def client_session(self):
        if self._client_session:
            return self._client_session
        else:
            raise RuntimeError("The bot haven't been setup yet. Ensure you call bot.async_setup asap.")

    def reload_config(self):
        self.config = config.load_config()

    async def async_setup(self):
        """
        This funtcion is run once, and is used to setup the bot async features, like the ClientSession from aiohttp.
        """
        self._client_session = aiohttp.ClientSession()  # There is no need to call __aenter__, since that does nothing in that case

    async def on_message(self, message):
        if not self.is_ready():
            return  # Ignoring messages when not ready

        if message.author.bot:
            return  # ignore messages from other bots

        ctx = await self.get_context(message, cls=MyContext)
        if ctx.prefix is not None:
            await self.invoke(ctx)

    async def on_command(self, ctx: MyContext):
        self.commands_used[ctx.command.name] += 1
        ctx.logger.info(f"{ctx.message.clean_content}")

    async def on_shard_ready(self, shard_id):
        self.shards_ready.add(shard_id)

    async def on_disconnect(self):
        self.shards_ready = set()

    async def on_ready(self):
        messages = ["-----------", f"The bot is ready.", f"Logged in as {self.user.name} ({self.user.id})."]
        total_members = len(self.users)
        messages.append(f"I see {len(self.guilds)} guilds, and {total_members} members.")
        messages.append(f"To invite your bot to your server, use the following link: https://discordapp.com/api/oauth2/authorize?client_id={self.user.id}&scope=bot&permissions=0")
        cogs_count = len(self.cogs)
        messages.append(f"{cogs_count} cogs are loaded")
        messages.append("-----------")
        for message in messages:
            self.logger.info(message)

        for message in messages:
            print(message)


async def get_prefix(bot: MyBot, message: discord.Message):
    forced_prefixes = bot.config["bot"]["prefixes"]

    if not message.guild:
        # Need no prefix when in DMs
        return commands.when_mentioned_or(*forced_prefixes, "")(bot, message)

    else:

        if bot.config["database"]["enable"]:
            db_guild = await get_from_db(message.guild)
            guild_prefix = db_guild.prefix
            if guild_prefix:
                forced_prefixes.append(guild_prefix)

        return commands.when_mentioned_or(*forced_prefixes)(bot, message)
