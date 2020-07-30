import asyncio

from discord.ext import commands, tasks
from utils.cog_class import Cog
from utils import ducks
from time import time


class DucksSpawning(Cog):
    def __init__(self, bot, *args, **kwargs):
        super().__init__(bot, *args, **kwargs)
        self.index = 0
        self.background_loop = bot.loop.create_task(self.loop())
        self.interval = 1

    async def loop(self):
        await self.before()
        now = time()
        current_iteration = now
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

    async def spawn_ducks(self, now):
        pass

    def cog_unload(self):
        self.background_loop.cancel()

    async def before(self):
        await self.bot.wait_until_ready()


setup = DucksSpawning.setup
