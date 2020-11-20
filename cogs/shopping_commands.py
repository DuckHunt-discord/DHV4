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
from utils.models import get_from_db, get_player, Player


class ShoppingCommands(Cog):
    @commands.group(aliases=["buy", "rent"])
    @checks.channel_enabled()
    async def shop(self, ctx: MyContext):
        """
        Buy items here
        """
        if not ctx.invoked_subcommand:
            await ctx.send_help(ctx.command)

    @shop.command(aliases=["1"])
    async def bullet(self, ctx: MyContext, target: Optional[discord.Member], *args):
        """
        Adds a bullet to your magazine
        """
        ITEM_COST = 7
        channel = ctx.channel

        _ = await ctx.get_translate_function()
        db_hunter: Player = await get_player(ctx.author, ctx.channel)

        db_hunter.experience -= ITEM_COST
        db_hunter.bullets += 1

        channel = ctx.channel

        await db_hunter.save()
        await channel.send(_("Something here..."))


setup = ShoppingCommands.setup
