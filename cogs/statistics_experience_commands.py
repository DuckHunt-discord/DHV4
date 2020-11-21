import asyncio
import time

import discord
from discord.ext import commands

from utils import checks
from utils.cog_class import Cog
from utils.ctx_class import MyContext
from utils.models import Player, get_player, get_from_db


class StatisticsCommands(Cog):
    @commands.command(aliases=["quick_stats", "quickstats"])
    @checks.channel_enabled()
    async def me(self, ctx: MyContext, target: discord.Member = None):
        """
        Get some quickstats about yourself (or someone else).
        """
        if not target:
            target = ctx.author

        _ = await ctx.get_translate_function()
        db_hunter: Player = await get_player(target, ctx.channel)

        embed = discord.Embed(colour=discord.Color.blurple(),
                              title=_("{target.name} statistics.", target=target))

        level_info = db_hunter.level_info()

        embed.add_field(name=_("Bullets"), value=f"{db_hunter.bullets}/{level_info['bullets']}", inline=True)
        embed.add_field(name=_("Magazines"), value=f"{db_hunter.magazines}/{level_info['magazines']}", inline=True)
        embed.add_field(name=_("Experience"), value=db_hunter.experience, inline=True)
        embed.add_field(name=_("Level"), value=str(level_info['level']) + " - " + _(level_info['name']).title(), inline=True)
        embed.add_field(name=_("Accuracy"), value=_("{level_reliability} % (Real: {real_reliability} %)", level_reliability=level_info['accuracy'], real_reliability=db_hunter.real_accuracy), inline=True)
        embed.add_field(name=_("Reliability"), value=_("{level_reliability} % (Real: {real_reliability} %)", level_reliability=level_info['reliability'], real_reliability=db_hunter.real_reliability), inline=True)

        await ctx.send(embed=embed)

    @commands.command(aliases=["sendexp", "sendxp", "send_xp"])
    @checks.channel_enabled()
    async def send_exp(self, ctx: MyContext, target: discord.Member, amount: int):
        """
        Send some of your experience to another player.
        """
        _, db_channel, db_sender, db_reciver = await asyncio.gather(ctx.get_translate_function(), get_from_db(ctx.channel), get_player(ctx.author, ctx.channel), get_player(target, ctx.channel))

        if target.id == ctx.author.id:
            await ctx.reply(_("❌ You cant send experience to yourself."))
            return False

        elif target.bot:
            await ctx.reply(_("❌ I'm not sure that {target.mention} can play DuckHunt.", target=target))
            return False

        elif amount < 10:
            await ctx.reply(_("❌ You need to send more experience than this."))
            return False

        elif db_sender.experience < amount:
            await ctx.reply(_("❌ You don't have enough experience 🤣."))
            return False

        tax = int(amount * (db_channel.tax_on_user_send/100)+0.5)

        db_sender.experience -= amount
        db_reciver.experience += amount - tax

        await asyncio.gather(db_sender.save(), db_reciver.save())

        await ctx.reply(_("🏦 You sent {recived} experience to {reciver.mention}. "
                          "A tax of {db_channel.tax_on_user_send}% was applied to this transaction (taking {tax} exp out of the total sent).",

                          amount=amount,
                          recived=amount - tax,
                          tax=tax,
                          reciver=target,
                          db_channel=db_channel))


setup = StatisticsCommands.setup
