import asyncio
import datetime
import random

import discord
from babel.dates import format_timedelta
from discord.ext import commands

from utils import checks, models
from utils.bot_class import MyBot
from utils.interaction import get_webhook_if_possible

from utils.ducks import Duck, SuperDuck, BabyDuck, PrDuck, GhostDuck, MotherOfAllDucks, ArmoredDuck, GoldenDuck, \
    PlasticDuck, KamikazeDuck, spawn_random_weighted_duck, \
    RANDOM_SPAWN_DUCKS_CLASSES, MechanicalDuck, NightDuck, SleepingDuck

from utils.cog_class import Cog
from utils.ctx_class import MyContext


def _(message):
    return message


class DucksSpawningCommands(Cog):
    display_name = _("Admin: Spawning")
    help_priority = 5
    help_color = 'red'

    @commands.group(aliases=["spawn", "spawnduck"])
    @checks.channel_enabled()
    @checks.needs_access_level(models.AccessLevel.ADMIN)
    @commands.cooldown(5, 30, commands.BucketType.channel)
    async def coin(self, ctx: MyContext):
        """
        Spawns a random duck
        """
        if not ctx.invoked_subcommand:
            await spawn_random_weighted_duck(ctx.bot, ctx.channel)

    @coin.command()
    async def roulette(self, ctx: MyContext, how_many_ducks: int = 5):
        """
        Spawns many ducks, of which (at least) one is a mechanical one
        """
        how_many_ducks = max(2, min(how_many_ducks, 14))

        ducks_classes = random.choices(RANDOM_SPAWN_DUCKS_CLASSES, k=how_many_ducks)

        random.shuffle(ducks_classes)

        ducks_classes += [MechanicalDuck]

        for duck_class in ducks_classes:
            myduck = duck_class(ctx.bot, ctx.channel)
            await myduck.spawn()
            await asyncio.sleep(2)

    @coin.command()
    async def normal(self, ctx: MyContext):
        """
        Spawns a normal duck
        """
        myduck = Duck(ctx.bot, ctx.channel)
        await myduck.spawn()

    @coin.command()
    async def super(self, ctx: MyContext, lives: int = None):
        """
        Spawns a super duck
        """
        if lives:
            lives = min(max(lives, 2), 99)
        myduck = SuperDuck(ctx.bot, ctx.channel, lives=lives)
        await myduck.spawn()

    @coin.command()
    async def baby(self, ctx: MyContext):
        """
        Spawns a baby duck
        """
        myduck = BabyDuck(ctx.bot, ctx.channel)
        await myduck.spawn()

    @coin.command()
    async def prof(self, ctx: MyContext):
        """
        Spawns a professor Duck.
        """
        myduck = PrDuck(ctx.bot, ctx.channel)
        await myduck.spawn()

    @coin.command()
    async def ghost(self, ctx: MyContext):
        """
        Spawns a ghost duck. There will be no spawn message, obviously.
        """
        myduck = GhostDuck(ctx.bot, ctx.channel)
        await myduck.spawn()

    @coin.command(aliases=["mother", "mother_of_all_ducks"])
    async def moad(self, ctx: MyContext, lives: int = None):
        """
        Spawns a MOAD.
        """
        if lives:
            lives = min(max(lives, 2), 99)
        myduck = MotherOfAllDucks(ctx.bot, ctx.channel, lives=lives)
        await myduck.spawn()

    @coin.command()
    async def armored(self, ctx: MyContext):
        """
        Spawns an armored duck, that will resist most 1 dmg hits.
        """
        myduck = ArmoredDuck(ctx.bot, ctx.channel)
        await myduck.spawn()

    @coin.command()
    async def golden(self, ctx: MyContext):
        """
        Spawns a golden duck.
        """
        myduck = GoldenDuck(ctx.bot, ctx.channel)
        await myduck.spawn()

    @coin.command()
    async def plastic(self, ctx: MyContext):
        """
        Spawns a plastic duck.
        """
        myduck = PlasticDuck(ctx.bot, ctx.channel)
        await myduck.spawn()

    @coin.command()
    async def kamikaze(self, ctx: MyContext):
        """
        Spawns a kamikaze duck.
        """
        myduck = KamikazeDuck(ctx.bot, ctx.channel)
        await myduck.spawn()

    @coin.command()
    async def night(self, ctx: MyContext):
        """
        Spawns a night duck.
        """
        myduck = NightDuck(ctx.bot, ctx.channel)
        await myduck.spawn()

    @coin.command()
    async def sleeping(self, ctx: MyContext):
        """
        Spawns a sleeping duck.
        """
        myduck = SleepingDuck(ctx.bot, ctx.channel)
        await myduck.spawn()

    @commands.group(aliases=["ducks"])
    @checks.channel_enabled()
    @checks.needs_access_level(models.AccessLevel.ADMIN)
    async def ducks_list(self, ctx: MyContext):
        """
        Show ducks currently on the channel
        """
        if not ctx.invoked_subcommand:
            _ = await ctx.get_translate_function(user_language=True)
            language_code = await ctx.get_language_code(user_language=True)
            ducks_spawned = self.bot.ducks_spawned[ctx.channel]
            ducks_spawned_count = len(ducks_spawned)
            ducks = self.bot.enabled_channels[ctx.channel]
            ducks_left = ducks.ducks_left
            ducks_day = ducks.day_ducks
            ducks_night = ducks.night_ducks

            if not ducks_night:
                message = [_("{ducks_spawned_count} ducks are on the channel, {ducks_left} ducks left to spawn today.",
                             ducks_spawned_count=ducks_spawned_count,
                             ducks_left=ducks_left), ]
            else:
                message = [_("{ducks_spawned_count} ducks are on the channel, {ducks_day} ducks left to spawn during "
                             "the day and {ducks_night} during the night.",
                             ducks_spawned_count=ducks_spawned_count,
                             ducks_day=ducks_day,
                             ducks_night=ducks_night), ]

            if ducks_spawned:
                message.append(_("Here's the list of ducks spawned :"))
                message.append('```')

                for duck in ducks_spawned:
                    spawned_for = datetime.timedelta(seconds=-duck.spawned_for)

                    time_delta = format_timedelta(spawned_for, locale=language_code, add_direction=True)

                    duck_lives = await duck.get_lives()

                    message.append(_("{duck.category} ({duck.lives_left}/{duck_lives} lives), spawned {time_delta}.",
                                     duck=duck,
                                     duck_lives=duck_lives,
                                     time_delta=time_delta
                                     ))
                message.append('```')
            try:
                await ctx.author.send(content='\n'.join(message))
            except discord.Forbidden:
                await ctx.reply("I couldn't DM you... Are your DMs blocked ?")

    @ducks_list.command()
    async def clear(self, ctx: MyContext):
        """
        Removes all ducks from the channel
        """
        _ = await ctx.get_translate_function()
        ducks_spawned = self.bot.ducks_spawned[ctx.channel]
        ducks_spawned_count = len(ducks_spawned)

        del self.bot.ducks_spawned[ctx.channel]

        await ctx.send(_("{ducks_spawned_count} ducks removed.", ducks_spawned_count=ducks_spawned_count))


setup = DucksSpawningCommands.setup
