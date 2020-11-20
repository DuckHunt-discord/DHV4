import random
from typing import Optional

import discord
from discord.ext import commands

from utils import checks

from utils.cog_class import Cog
from utils.ctx_class import MyContext
from utils.models import get_player, Player


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
    async def bullet(self, ctx: MyContext):
        """
        Adds a bullet to your magazine
        """
        ITEM_COST = 7

        _ = await ctx.get_translate_function()
        db_hunter: Player = await get_player(ctx.author, ctx.channel)

        level_info = db_hunter.level_info()

        max_bullets = level_info['bullets']
        if db_hunter.bullets >= max_bullets:
            await ctx.reply(_("❌ Whoops, you have too many bullets in your weapon already."))
            return False

        db_hunter.experience -= ITEM_COST
        db_hunter.bullets += 1
        db_hunter.bought_items['bullets'] += 1

        await db_hunter.save()
        await ctx.reply(_("💸 You added a bullet in your weapon."))

        if max_bullets > 1:
            await ctx.reply(_("💡 Next time, you might want to buy a magazine, it'll be cheaper for you 😁"))

    @shop.command(aliases=["2", "charger"])
    async def magazine(self, ctx: MyContext):
        """
        Adds a magazine in your backpack.
        """
        ITEM_COST = 12

        _ = await ctx.get_translate_function()
        db_hunter: Player = await get_player(ctx.author, ctx.channel, giveback=True)

        level_info = db_hunter.level_info()

        max_magazines = level_info['magazines']
        if db_hunter.bullets >= max_magazines:
            await ctx.reply(_("❌ Whoops, you have too many magazines in your backpack already... Try reloading !"))
            return False

        db_hunter.experience -= ITEM_COST
        db_hunter.magazines += 1
        db_hunter.bought_items['magazines'] += 1

        await db_hunter.save()
        await ctx.reply(_("💸 You added a magazine in your weapon. Time to reload!"))


setup = ShoppingCommands.setup
