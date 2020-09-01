import asyncio
import datetime
import random

import discord
from discord.ext import commands, tasks
from utils.cog_class import Cog
from utils import ducks
from time import time

from utils.models import get_enabled_channels, DiscordChannel, get_from_db


class DucksSpawning(Cog):
    def __init__(self, bot, *args, **kwargs):
        super().__init__(bot, *args, **kwargs)
        self.index = 0
        self.background_loop = bot.loop.create_task(self.loop())
        self.interval = 1

    async def loop(self):
        await self.before()
        now = time()
        current_iteration = int(now)
        while not self.background_loop.cancelled():
            # Precalculate timings
            now = time()
            current_iteration = current_iteration + self.interval
            delay = now - current_iteration
            if delay >= 30:
                self.bot.logger.error(f"Ignoring iterations to compensate for delays ({delay} seconds)!")
                current_iteration = now
            elif delay >= 5:
                self.bot.logger.warning(f"Loop running with severe delays ({delay} seconds)!")

            # Loop part
            try:
                await self.spawn_ducks(current_iteration)
            except Exception as e:
                self.bot.logger.exception("Ignoring exception inside loop and hoping for the best...")

            # Loop the loop
            now = time()
            next_iteration = current_iteration + self.interval
            await asyncio.sleep(max(0.0, next_iteration - now))

    async def spawn_ducks(self, now: int):
        SECONDS_SPENT_TODAY = now % 86400
        SECONDS_LEFT_TODAY = 86400 - SECONDS_SPENT_TODAY

        for channel, ducks_left_to_spawn in self.bot.enabled_channels.items():
            if random.randint(1, SECONDS_LEFT_TODAY) < ducks_left_to_spawn:
                asyncio.ensure_future(ducks.spawn_random_weighted_duck(self.bot, channel))
                self.bot.enabled_channels[channel] -= 1

        for channel, ducks_queue in self.bot.ducks_spawned.items():
            for duck in ducks_queue:
                asyncio.ensure_future(duck.maybe_leave())

    def cog_unload(self):
        self.background_loop.cancel()

    async def before(self):
        await self.bot.wait_until_ready()

        db_channels = await get_enabled_channels()
        for db_channel in db_channels:
            channel = self.bot.get_channel(db_channel.discord_id)

            if channel:
                self.bot.enabled_channels[channel] = await self.calculate_ducks_per_day(db_channel, now=int(time()))
            else:
                db_channel.enabled = False
                await db_channel.save()

    async def calculate_ducks_per_day(self, db_channel: DiscordChannel, now: int):
        # TODO : Really compute that
        return db_channel.ducks_per_day

    async def recompute_channel(self, channel: discord.TextChannel):
        db_channel = await get_from_db(channel)
        self.bot.enabled_channels[channel] = await self.calculate_ducks_per_day(db_channel, now=int(time()))


setup = DucksSpawning.setup
