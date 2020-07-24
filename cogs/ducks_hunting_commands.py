import random

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
    async def bang(self, ctx: MyContext):
        """
        Shoot at the duck that appeared first on the channel.
        """
        _ = await ctx.get_translate_function()

        channel = ctx.channel
        duck = await ctx.target_next_duck()
        if duck:
            await duck.shoot()
        else:
            await channel.send(_("No duck, bruh"))




setup = DucksHuntingCommands.setup
