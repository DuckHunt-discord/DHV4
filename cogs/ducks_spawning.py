import asyncio
import json
import random

import discord
from utils.cog_class import Cog
from utils import ducks
from time import time

from utils.ducks import deserialize_duck
from utils.models import get_enabled_channels, DiscordChannel, get_from_db

SECOND = 1
MINUTE = 60 * SECOND
HOUR = 60 * MINUTE
DAY = 24 * HOUR


class DucksSpawning(Cog):
    def __init__(self, bot, *args, **kwargs):
        super().__init__(bot, *args, **kwargs)
        self.index = 0
        self.background_loop = bot.loop.create_task(self.loop())
        self.interval = 1

    async def loop(self):
        try:
            await self.before()
        except:
            self.bot.logger.exception("Error in before_loop")
            raise
        now = time()
        current_iteration = int(now)
        while not self.background_loop.cancelled():
            # Precalculate timings
            now = time()
            current_iteration = current_iteration + self.interval
            delay = now - current_iteration
            if delay >= 30:
                self.bot.logger.error(f"Ignoring iterations to compensate for delays ({delay} seconds)!")
                current_iteration = int(now)
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
            for duck in ducks_queue.copy():
                await duck.maybe_leave()

    def cog_unload(self):
        self.background_loop.cancel()

        self.bot.logger.info(f"Saving ducks to cache...")

        ducks_spawned = self.bot.ducks_spawned

        ducks_count = 0

        serialized = {}

        for channel, ducks in ducks_spawned.items():
            ducks_in_channel = []
            for duck in ducks:
                ducks_in_channel.append(duck.serialize())
                ducks_count += 1
            serialized[channel.id] = ducks_in_channel

        with open("ducks_spawned_cache.json", "w") as f:
            json.dump(serialized, f)

        self.bot.logger.info(f"Saved {ducks_count} to ducks_spawned_cache.json")

    async def before(self):
        self.bot.logger.info(f"Waiting for ready-ness to planify duck spawns...")

        await self.bot.wait_until_ready()

        self.bot.logger.info(f"Restoring ducks from cache...")

        ducks_count = 0

        with open("ducks_spawned_cache.json", "r") as f:
            serialized = json.load(f)

        for channel_id, ducks in serialized.items():
            channel = self.bot.get_channel(int(channel_id))

            if channel:
                for data in ducks:
                    ducks_count += 1
                    duck = deserialize_duck(self.bot, channel, data)
                    await duck.spawn(loud=False)

        self.bot.logger.info(f"{ducks_count} ducks restored!")

        db_channels = await get_enabled_channels()

        self.bot.logger.info(f"Planifying ducks spawns for the rest of the day")

        for db_channel in db_channels:
            channel = self.bot.get_channel(db_channel.discord_id)

            if channel:
                self.bot.enabled_channels[channel] = await self.calculate_ducks_per_day(db_channel, now=int(time()))
            else:
                db_channel.enabled = False
                await db_channel.save()

        self.bot.logger.info(f"Ducks spawning started")

    async def calculate_ducks_per_day(self, db_channel: DiscordChannel, now: int):
        # TODO : Compute ducks sleep
        ducks_per_day = db_channel.ducks_per_day

        seconds_elapsed = now % DAY
        seconds_left_in_day = DAY - seconds_elapsed

        pct_day = round(seconds_elapsed / DAY, 2) * 100

        ducks = int((seconds_left_in_day * ducks_per_day) / DAY)

        self.bot.logger.debug(f"Recomputing : {pct_day}% day done, {ducks}/{ducks_per_day} ducks to spawn today")

        return ducks

    async def recompute_channel(self, channel: discord.TextChannel):
        db_channel = await get_from_db(channel)
        self.bot.enabled_channels[channel] = await self.calculate_ducks_per_day(db_channel, now=int(time()))


setup = DucksSpawning.setup
