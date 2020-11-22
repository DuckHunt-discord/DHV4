import asyncio
import time

import discord
from discord.ext import commands

from utils import checks, models
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


    def add_fields_for_every_duck(self, _, embed, from_dict, not_found_message):
        fields = [
            (_("Normal ducks"), 'normal'),
            (_("Ghost ducks"), 'ghost'),
            (_("Professor ducks"), 'prof'),

            (_("Baby ducks"), 'baby'),
            (_("Golden ducks"), 'golden'),
            (_("Plastic ducks"), 'plastic'),

            (_("Kamikaze ducks"), 'kamikaze'),
            (_("Mechanical ducks"), 'mechanical'),
            (_("Super ducks"), 'super'),

            (_("Mother of all ducks"), 'moad'),
            (_("Armored ducks"), 'armored'),
        ]

        for field_name, field_key in fields:

            value = from_dict.get(field_key, None)
            if value:
                embed.add_field(name=field_name, value=str(value), inline=True)
            elif not_found_message:
                embed.add_field(name=field_name, value=str(not_found_message), inline=True)

    @commands.command(aliases=["times", "besttimes"])
    @checks.channel_enabled()
    async def best_times(self, ctx: MyContext, target: discord.Member = None):
        """
        Get best times to kill of ducks (for you or someone else).
        """
        if not target:
            target = ctx.author

        _ = await ctx.get_translate_function()
        db_hunter: Player = await get_player(target, ctx.channel)

        embed = discord.Embed(colour=discord.Color.blurple(),
                              title=_("{target.name} best times.", target=target))

        bt = db_hunter.best_times

        bt = {k: str(round(v, 2)) + " s" for k, v in bt.items()}

        no_kill_message = _("Never killed any")

        self.add_fields_for_every_duck(_, embed, bt, no_kill_message)

        await ctx.send(embed=embed)

    @commands.command(aliases=["kills", "killsstats", "killcounts", "kills_count", "kill_count", "killed"])
    @checks.channel_enabled()
    async def kills_stats(self, ctx: MyContext, target: discord.Member = None):
        """
        Get number of each type of duck killed (for you or someone else).
        """
        if not target:
            target = ctx.author

        _ = await ctx.get_translate_function()
        db_hunter: Player = await get_player(target, ctx.channel)

        embed = discord.Embed(colour=discord.Color.blurple(),
                              title=_("{target.name} kill counts.", target=target))

        killed = db_hunter.killed

        no_kill_message = 0

        self.add_fields_for_every_duck(_, embed, killed, no_kill_message)

        await ctx.send(embed=embed)

    @commands.command(aliases=["hugs", "hugsstats", "hugged"])
    @checks.channel_enabled()
    async def hugs_stats(self, ctx: MyContext, target: discord.Member = None):
        """
        Get number of each type of duck hugged (for you or someone else).
        """
        if not target:
            target = ctx.author

        _ = await ctx.get_translate_function()
        db_hunter: Player = await get_player(target, ctx.channel)

        embed = discord.Embed(colour=discord.Color.blurple(),
                              title=_("{target.name} hugs counts.", target=target))

        self.add_fields_for_every_duck(_, embed, db_hunter.hugged, None)

        await ctx.send(embed=embed)

    @commands.command(aliases=["hurted", "hurtstats"])
    @checks.channel_enabled()
    async def hurt_stats(self, ctx: MyContext, target: discord.Member = None):
        """
        Get number of each type of duck hurted (for you or someone else).
        """
        if not target:
            target = ctx.author

        _ = await ctx.get_translate_function()
        db_hunter: Player = await get_player(target, ctx.channel)

        embed = discord.Embed(colour=discord.Color.blurple(),
                              title=_("{target.name} hurt counts.", target=target))

        self.add_fields_for_every_duck(_, embed, db_hunter.hurted, None)

        await ctx.send(embed=embed)

    @commands.command(aliases=["resisted", "resiststats"])
    @checks.channel_enabled()
    async def resist_stats(self, ctx: MyContext, target: discord.Member = None):
        """
        Get number of each type of duck that resisted a shot (for you or someone else).
        """
        if not target:
            target = ctx.author

        _ = await ctx.get_translate_function()
        db_hunter: Player = await get_player(target, ctx.channel)

        embed = discord.Embed(colour=discord.Color.blurple(),
                              title=_("{target.name} resisted counts.", target=target))

        self.add_fields_for_every_duck(_, embed, db_hunter.resisted, None)

        await ctx.send(embed=embed)

    @commands.command(aliases=["fightened", "fightenstats", "fightened_stats", "fightenedstats", "frighten"])
    @checks.channel_enabled()
    async def frighten_stats(self, ctx: MyContext, target: discord.Member = None):
        """
        Get number of each type of duck that fled following a shot (for you or someone else).
        """
        if not target:
            target = ctx.author

        _ = await ctx.get_translate_function()
        db_hunter: Player = await get_player(target, ctx.channel)

        embed = discord.Embed(colour=discord.Color.blurple(),
                              title=_("{target.name} scared ducks.", target=target))

        self.add_fields_for_every_duck(_, embed, db_hunter.frightened, None)

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

    @commands.command(aliases=["giveexp", "givexp", "give_xp"])
    @checks.channel_enabled()
    @checks.needs_access_level(models.AccessLevel.ADMIN)
    async def give_exp(self, ctx: MyContext, target: discord.Member, amount: int):
        """
        Give some experience to another player. This is a cheat.
        """
        _, db_reciver = await asyncio.gather(ctx.get_translate_function(), get_player(target, ctx.channel))

        if target.bot:
            await ctx.reply(_("❌ I'm not sure that {target.mention} can play DuckHunt.", target=target))
            return False

        db_reciver.experience += amount

        await db_reciver.save()

        await ctx.reply(_("💰️ You gave {amount} experience to {reciver.mention}. ",
                          amount=amount,
                          reciver=target,))


setup = StatisticsCommands.setup
