"""
Some example of commands that can be used only in the bot support server.
"""
import asyncio
import datetime
import time

import discord
import pytz
from discord.ext import commands, tasks, menus
from tortoise import timezone

from utils import checks
from utils.cog_class import Cog
from utils.ctx_class import MyContext
from utils.interaction import purge_channel_messages, EmbedCounterPaginator
from babel import dates

from utils.models import AccessLevel, get_from_db


def _(message):
    return message


class SupportServerCommands(Cog):
    display_name = _("Support team: misc")
    help_priority = 15
    help_color = 'red'

    def __init__(self, bot, *args, **kwargs):
        super().__init__(bot, *args, **kwargs)
        self.index = 0
        self.background_loop.start()

    def cog_unload(self):
        self.background_loop.cancel()

    # async def cog_check(self, ctx):
    #    ret = super().cog_check(ctx)
    #    ret = ret and ctx.guild.id == self.config()["support_server_id"]
    #    return ret

    def get_bot_uptime(self):
        return dates.format_timedelta(self.bot.uptime - timezone.now(), locale='en')

    @tasks.loop(seconds=30)
    async def background_loop(self):
        status_channel = self.bot.get_channel(self.config()["status_channel_id"])
        if not status_channel or not isinstance(status_channel, discord.TextChannel):
            self.bot.logger.warning("The status channel for the support server command is misconfigured.")
            return

        self.bot.logger.debug("Updating status message", guild=status_channel.guild, channel=status_channel)

        embed = discord.Embed(colour=discord.Colour.blurple(),
                              title=f"{self.bot.user.name}'s status")

        embed.add_field(name="Guilds Count", value=f"{len(self.bot.guilds)}", inline=True)
        embed.add_field(name="Users Count", value=f"{len(self.bot.users)}", inline=True)
        embed.add_field(name="Messages in cache", value=f"{len(self.bot.cached_messages)}", inline=True)

        ping_f = status_channel.typing()
        t_1 = time.perf_counter()
        await ping_f  # tell Discord that the bot is "typing", which is a very simple request
        t_2 = time.perf_counter()
        ping = round((t_2 - t_1) * 1000)  # calculate the time needed to trigger typing

        embed.add_field(name="Average Latency", value=f"{round(self.bot.latency, 2)}ms", inline=True)
        embed.add_field(name="Current ping", value=f"{ping}ms", inline=True)
        embed.add_field(name="Shards Count", value=f"{self.bot.shard_count}", inline=True)

        embed.add_field(name="Cogs loaded", value=f"{len(self.bot.cogs)}", inline=True)
        embed.add_field(name="Commands loaded", value=f"{len(self.bot.commands)}", inline=True)
        embed.add_field(name="Uptime", value=f"{self.get_bot_uptime()}", inline=True)

        try:
            mc_command_name, mc_command_uses = self.bot.commands_used.most_common(1)[0]
            embed.add_field(name="Commands (most used)", value=f"dh!{mc_command_name} ({mc_command_uses} uses)", inline=False)
        except (ValueError, IndexError):
            embed.add_field(name="Commands", value=f"❌", inline=False)

        ds_cog = self.bot.get_cog("DucksSpawning")
        if ds_cog:
            now = time.time()
            loop_time = ds_cog.current_iteration_public
            diff = now - loop_time
            diff_str = round(diff, 2)
            if loop_time == 0:
                embed.add_field(name="Ducks Loop", value=f"⚠️ Restoring ducks...", inline=True)
            elif diff < 2:
                embed.add_field(name="Ducks Loop", value=f"✅ {diff_str}s off", inline=True)
            else:
                embed.add_field(name="Ducks Loop", value=f"⚠️ {diff_str}s off", inline=True)
        else:
            embed.add_field(name="Ducks Loop", value=f"❌ Unloaded", inline=True)

        boss_cog = self.bot.get_cog("DuckBoss")
        if boss_cog:
            if boss_cog.background_loop.failed():
                embed.add_field(name="Boss Loop", value=f"❌ Failed", inline=True)
            else:

                embed.add_field(name="Boss Loop", value=f"✅ {boss_cog.iterations_spawn} spawns "
                                                        f"({ round(boss_cog.luck) }% luck), {boss_cog.background_loop.current_loop} it",
                                inline=True)
        else:
            embed.add_field(name="Boss Loop", value=f"❌ Unloaded", inline=True)

        embed.timestamp = timezone.now()

        next_it = self.background_loop.next_iteration
        now = timezone.now()

        delta = dates.format_timedelta(next_it - now, locale='en')
        embed.set_footer(text=f"This should update every {delta} - Last update")

        await purge_channel_messages(status_channel)
        await status_channel.send(embed=embed)

    @background_loop.before_loop
    async def before(self):
        await self.bot.wait_until_ready()

    @commands.command(aliases=["shard_status"])
    async def shards(self, ctx: MyContext):
        """
        Check the status of every shard the bot is hosting.
        """
        if self.bot.shard_count == 1:
            await ctx.send("The bot is not yet sharded.")
            return

        latencies = sorted(self.bot.latencies, key=lambda l: l[0])
        message = "```"

        for shard, latency in latencies:
            if shard == ctx.guild.shard_id:
                message += "**"
            message += f"•\t Shard ID {shard}: {round(latency, 2)}ms"
            if shard in self.bot.shards_ready:
                message += f" (ready)"
            if shard == ctx.guild.shard_id:
                message += "**"
            message += "\n"

        message += f"\n```\n\nAvg latency: {self.bot.latency}ms"
        if self.bot.is_ready():
            message += " (bot ready)"

        await ctx.send(message)

    @commands.command(aliases=["used_commands"])
    async def commands_used(self, ctx: MyContext):
        """
        Shows a paginator with the most used commands on the bot. This is the poor version of a bot analytics.
        The counters get reset every time the bot reboot.
        """
        _ = await ctx.get_translate_function()

        menu = menus.MenuPages(EmbedCounterPaginator(self.bot.commands_used.most_common(), per_page=10,
                                                     embed_title=_("Most used commands"),
                                                     name_str="`dh!{elem}`",
                                                     value_str=_("{n} uses", n="{n}"),
                                                     ))
        await menu.start(ctx)

    @commands.command(name="bot_users", aliases=["bot_topusers"])
    async def c_bot_users(self, ctx: MyContext):
        """
        Shows a paginator with the users that have used the bot the most. This is again the poor version of a bot analytics.
        The counters get reset every time the bot reboot.
        """
        _ = await ctx.get_translate_function()

        menu = menus.MenuPages(EmbedCounterPaginator(self.bot.top_users.most_common(), per_page=10,
                                                     embed_title=_("Top users"),
                                                     name_str="ID: `{elem}`",
                                                     value_str=_("{n} commands used", n="{n}"),
                                                     field_inline=False
                                                     ))
        await menu.start(ctx)


setup = SupportServerCommands.setup
