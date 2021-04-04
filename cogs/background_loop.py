# coding=utf-8
from discord.ext import tasks

from utils.cog_class import Cog


class BackgroundLoop(Cog):
    def __init__(self, bot, *args, **kwargs):
        super().__init__(bot, *args, **kwargs)
        self.index = 0
        self.background_loop.start()

    def cog_unload(self):
        self.background_loop.cancel()

    @tasks.loop(minutes=15)
    async def background_loop(self):
        pass

    @background_loop.before_loop
    async def before(self):
        await self.bot.wait_until_ready()


setup = BackgroundLoop.setup
