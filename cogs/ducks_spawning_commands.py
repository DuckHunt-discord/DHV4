import random

import discord
from discord.ext import commands

from utils.bot_class import MyBot
from utils.interaction import get_webhook_if_possible

from utils.ducks import Duck, SuperDuck

from utils.cog_class import Cog
from utils.ctx_class import MyContext


class DucksSpawningCommands(Cog):
    @commands.group(aliases=["spawn", "spawnduck"])
    async def coin(self, ctx: MyContext):
        """
        Spawns a duck
        """
        if not ctx.invoked_subcommand:
            myduck = Duck(ctx.bot, ctx.channel)
            await myduck.spawn()

    @coin.command()
    async def super(self, ctx: MyContext, lives: int):
        """
        Spawns a super duck
        """
        if not ctx.invoked_subcommand:
            myduck = SuperDuck(ctx.bot, ctx.channel)
            await myduck.spawn()

setup = DucksSpawningCommands.setup
