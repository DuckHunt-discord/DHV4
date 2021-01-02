"""
Some example of commands that can be used only in the bot support server.
"""

import datetime
import time

import discord
import pytz
from babel.dates import format_timedelta
from discord.ext import commands, tasks

from utils import checks
from utils.cog_class import Cog
from utils.ctx_class import MyContext
from utils.interaction import purge_channel_messages
from babel import dates

from utils.models import AccessLevel


class SupportServerCommands(Cog):
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
        return dates.format_timedelta(self.bot.uptime - datetime.datetime.utcnow(), locale='en')

    @tasks.loop(minutes=15)
    async def background_loop(self):
        status_channel = self.bot.get_channel(self.config()["status_channel_id"])
        if not status_channel or not isinstance(status_channel, discord.TextChannel):
            self.bot.logger.warning("The status channel for the support server command is misconfigured.")
            return

        self.bot.logger.debug("Updating status message", guild=status_channel.guild, channel=status_channel)

        await purge_channel_messages(status_channel)
        embed = discord.Embed(colour=discord.Colour.blurple(),
                              title=f"{self.bot.user.name}'s status")

        embed.add_field(name="Guilds Count", value=f"{len(self.bot.guilds)}", inline=True)
        embed.add_field(name="Users Count", value=f"{len(self.bot.users)}", inline=True)
        embed.add_field(name="Messages in cache", value=f"{len(self.bot.cached_messages)}", inline=True)

        ping_f = status_channel.trigger_typing()
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

        embed.timestamp = datetime.datetime.utcnow()

        next_it = self.background_loop.next_iteration
        now = pytz.utc.localize(datetime.datetime.utcnow())

        delta = dates.format_timedelta(next_it - now, locale='en')
        embed.set_footer(text=f"This should update every {delta} - Last update")

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

    @commands.group(aliases=["bot_administration", "emergencies"])
    @checks.needs_access_level(AccessLevel.BOT_MODERATOR)
    async def manage_bot(self, ctx: MyContext):
        """
        Manage the bot current state by starting and stopping ducks spawning, leaving, and planning ducks spawn for the
        day.

        This commands do not use the translation system, and will always show in english
        """

        if not ctx.invoked_subcommand:
            await ctx.send_help(ctx.command)

    @manage_bot.command(aliases=["replan", "replanning", "replanify", "plan_spawns"])
    async def planify(self, ctx: MyContext):
        """
        Allow ducks spawning again, everywhere. Ducks will spawn more quickly than usual if a planification isn't done.

        Note that ducks leaves are controlled separately.
        """

        ducks_spawning_cog = self.bot.get_cog('DucksSpawning')

        await ducks_spawning_cog.planify()

        await ctx.reply(f"Ducks spawns have been reset based on the current time of the day.")

    @manage_bot.command(aliases=["disable_spawns"])
    async def stop_spawns(self, ctx: MyContext):
        """
        Stop ducks from spawning immediately, everywhere. Ducks don't get removed from the planification,
        so once the stop is over, ducks will spawn more quickly than usual.

        Duck will still be able to leave, even if this lock is set.
        """

        self.bot.allow_ducks_spawning = False

        await ctx.reply(f"Ducks will no longer spawn until the lock is removed with "
                        f"`{ctx.prefix}manage_bot start_spawns`.")

    @manage_bot.command(aliases=["restart_spawns", "enable_spawns"])
    async def start_spawns(self, ctx: MyContext):
        """
        Allow ducks spawning again, everywhere. Ducks will spawn more quickly than usual if a planification isn't done.
        """

        self.bot.allow_ducks_spawning = True

        await ctx.reply(f"Ducks will now spawn. Consider planning again if they have been stopped for a while :"
                        f"`{ctx.prefix}manage_bot planify`.")


setup = SupportServerCommands.setup
