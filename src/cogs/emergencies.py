"""
The emergencies command group, allowing for finer control of the bot, raw debugging and statistics.
"""
import asyncio
import datetime
import time
from typing import Union

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


class Emergencies(Cog):
    display_name = _("Support team: emergencies")
    help_priority = 15
    help_color = 'red'

    def __init__(self, bot, *args, **kwargs):
        super().__init__(bot, *args, **kwargs)
        self.ws_send_timings = []
        self.ws_recv_timings = []

    @commands.group(aliases=["bot_administration", "emergencies"])
    @checks.needs_access_level(AccessLevel.BOT_MODERATOR)
    async def manage_bot(self, ctx: MyContext):
        """
        Manage the bot current state by starting and stopping ducks spawning, leaving, and planning ducks spawn for the
        day.

        These commands do not use the translation system, and will always show in english
        """

        if not ctx.invoked_subcommand:
            await ctx.send_help(ctx.command)

    @manage_bot.command(aliases=["replan", "replanning", "replanify", "plan_spawns"])
    async def planify(self, ctx: MyContext):
        """
        Reset ducks planning, setting the ducks left to spawn counts to a value proportional to the time left spawning
        ducks today. This is executed everyday at midnight.
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

        embed = discord.Embed()

        embed.colour = discord.Colour.dark_red()
        embed.title = f"Maintenance: ducks won't spawn for now"
        embed.description = f"{ctx.author.mention} has stopped ducks from appearing for now, due to maintenance " \
                            f"requirements.\nStand by for a new message announcing the return of the spawns"

        embed.set_footer(text="Ducks will come back stronger than ever")

        await self.bot.log_to_channel(embed=embed)

    @manage_bot.command(aliases=["restart_spawns", "enable_spawns"])
    async def start_spawns(self, ctx: MyContext):
        """
        Allow ducks spawning again, everywhere. Ducks will spawn more quickly than usual if a planification isn't done.
        """

        self.bot.allow_ducks_spawning = True

        await ctx.reply(f"Ducks will now spawn. Consider planning again if they have been stopped for a while :"
                        f"`{ctx.prefix}manage_bot planify`.")

        embed = discord.Embed()

        embed.colour = discord.Colour.dark_green()
        embed.title = f"Maintenance: ducks are able to spawn"
        embed.description = f"{ctx.author.mention} has re-enabled ducks spawns."

        await self.bot.log_to_channel(embed=embed)

    @manage_bot.command(aliases=["spawn_boss", "boss", "boss_spawn"])
    async def force_boss_spawn(self, ctx: MyContext):
        """
        Force a boss to spawn
        """
        boss_cog = self.bot.get_cog('DuckBoss')

        await boss_cog.spawn_boss()

        await ctx.reply(f"A boss has been spawned.")

    @manage_bot.command(aliases=["event", "reroll_event", "change_event", "regen_event"])
    async def update_event(self, ctx: MyContext, force=True):
        """
        Force the current event to change, and reroll a new one.
        """
        ducks_spawning_cog = self.bot.get_cog('DucksSpawning')

        await ducks_spawning_cog.change_event(force=force)

        await ctx.reply(f"New event rolled.")

    @manage_bot.command()
    async def give_trophy(self, ctx: MyContext, trophy_key: str, user: discord.User, value: bool = True):
        """
        Congratulate an user giving them a trophy.
        """

        async with ctx.typing():
            db_user = await get_from_db(user, as_user=True)

            if value:
                db_user.trophys[trophy_key] = True
            else:
                del db_user.trophys[trophy_key]

            await db_user.save()

        await ctx.reply(f"User {user.name}#{user.discriminator} (`{user.id}`) updated.")

    @manage_bot.command()
    async def socketstats(self, ctx):
        delta = timezone.now() - self.bot.uptime
        minutes = delta.total_seconds() / 60
        total = sum(self.bot.socket_stats.values())
        cpm = total / minutes
        await ctx.send(f'{total} socket events observed ({cpm:.2f}/minute):\n{self.bot.socket_stats}')


setup = Emergencies.setup
