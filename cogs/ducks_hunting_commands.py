import random
from typing import Optional

import discord
from discord.ext import commands

from utils import checks
from utils.bot_class import MyBot
from utils.interaction import get_webhook_if_possible

from utils.ducks import Duck, SuperDuck

from utils.cog_class import Cog
from utils.ctx_class import MyContext
from utils.models import get_from_db, get_player, Player


class DucksHuntingCommands(Cog):
    @commands.command(aliases=["pan", "kill"])
    async def bang(self, ctx: MyContext, target: Optional[discord.Member], *args):
        """
        Shoot at the duck that appeared first on the channel.
        """
        _ = await ctx.get_translate_function()
        db_hunter: Player = await get_player(ctx.author, ctx.channel)

        channel = ctx.channel
        duck = await ctx.target_next_duck()
        if duck:
            await duck.shoot(args)
        else:
            await channel.send(_("What are you trying to kill exactly ? There are no ducks here."))
            db_hunter.shots_without_ducks += 1
            await db_hunter.save()

    @commands.command()
    async def hug(self, ctx: MyContext, target: Optional[discord.Member], *args):
        """
        Hug the duck that appeared first on the channel.
        """
        _ = await ctx.get_translate_function()
        db_hunter: Player = await get_player(ctx.author, ctx.channel)

        channel = ctx.channel

        if target:
            db_hunter.hugged['players'] += 1
            await db_hunter.save()
            await channel.send(_("{you.mention} hugged {other.mention}. They feel loved.", you=ctx.author, other=target))
            return

        duck = await ctx.target_next_duck()
        if duck:
            await duck.hug(args)
        else:
            await channel.send(_("What are you trying to hug, exactly? A tree?"))
            db_hunter.hugged["nothing"] += 1
            await db_hunter.save()



setup = DucksHuntingCommands.setup
