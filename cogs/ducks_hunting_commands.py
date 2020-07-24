import random
from typing import Optional

import discord
from discord.ext import commands

from utils import checks, permissions
from utils.bot_class import MyBot
from utils.interaction import get_webhook_if_possible

from utils.ducks import Duck, SuperDuck

from utils.cog_class import Cog
from utils.ctx_class import MyContext


class DucksHuntingCommands(Cog):
    @commands.command(aliases=["pan", "kill"])
    async def bang(self, ctx: MyContext, target: Optional[discord.Member], *args):
        """
        Shoot at the duck that appeared first on the channel.
        """
        _ = await ctx.get_translate_function()

        channel = ctx.channel
        duck = await ctx.target_next_duck()
        if duck:
            await duck.shoot(*args)
        else:
            await channel.send(_("No duck, bruh"))

    @commands.command()
    async def hug(self, ctx: MyContext, target: Optional[discord.Member], *args):
        """
        Hug the duck that appeared first on the channel.
        """
        _ = await ctx.get_translate_function()

        channel = ctx.channel
        duck = await ctx.target_next_duck()
        if duck:
            await duck.hug(*args)
        else:
            await channel.send(_("No duck, bruh. Tree."))


setup = DucksHuntingCommands.setup
