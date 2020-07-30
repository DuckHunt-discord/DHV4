import random

import discord
from discord.ext import commands

from utils import checks, permissions
from utils.bot_class import MyBot
from utils.interaction import get_webhook_if_possible

from utils.ducks import Duck, SuperDuck, BabyDuck, PrDuck, GhostDuck, MotherOfAllDucks, ArmoredDuck, GoldenDuck, PlasticDuck, KamikazeDuck, spawn_random_weighted_duck

from utils.cog_class import Cog
from utils.ctx_class import MyContext


class DucksSpawningCommands(Cog):
    @commands.group(aliases=["spawn", "spawnduck"])
    @checks.server_admin_or_permission("ducks.spawn.normal")
    async def coin(self, ctx: MyContext):
        """
        Spawns a random duck
        """
        if not ctx.invoked_subcommand:
            await spawn_random_weighted_duck(ctx.bot, ctx.channel)

    @coin.command()
    @checks.server_admin_or_permission("ducks.spawn.normal")
    async def super(self, ctx: MyContext):
        """
        Spawns a normal duck
        """
        myduck = Duck(ctx.bot, ctx.channel)
        await myduck.spawn()

    @coin.command()
    @checks.server_admin_or_permission("ducks.spawn.super")
    async def super(self, ctx: MyContext, lives: int = None):
        """
        Spawns a super duck
        """
        can_set_lives = await permissions.has_server_administrator_or_permission(ctx, 'ducks.spawn.super.set_lives')
        if lives and not can_set_lives:
            await ctx.send("⚠️ You can't set the lives of a super duck. Ask for the `ducks.spawn.super.set_lives` permission.")
            lives = None

        myduck = SuperDuck(ctx.bot, ctx.channel, lives=lives)
        await myduck.spawn()

    @coin.command()
    @checks.server_admin_or_permission("ducks.spawn.baby")
    async def baby(self, ctx: MyContext):
        """
        Spawns a baby duck
        """
        myduck = BabyDuck(ctx.bot, ctx.channel)
        await myduck.spawn()

    @coin.command()
    @checks.server_admin_or_permission("ducks.spawn.prof")
    async def prof(self, ctx: MyContext):
        """
        Spawns a professor Duck.
        """
        myduck = PrDuck(ctx.bot, ctx.channel)
        await myduck.spawn()

    @coin.command()
    @checks.server_admin_or_permission("ducks.spawn.ghost")
    async def ghost(self, ctx: MyContext):
        """
        Spawns a ghost duck. There will be no spawn message, obviously.
        """
        myduck = GhostDuck(ctx.bot, ctx.channel)
        await myduck.spawn()

    @coin.command(aliases=["mother", "mother_of_all_ducks"])
    @checks.server_admin_or_permission("ducks.spawn.moad")
    async def moad(self, ctx: MyContext):
        """
        Spawns a MOAD.
        """
        myduck = MotherOfAllDucks(ctx.bot, ctx.channel)
        await myduck.spawn()

    @coin.command()
    @checks.server_admin_or_permission("ducks.spawn.armored")
    async def armored(self, ctx: MyContext):
        """
        Spawns an armored duck, that will resist most 1 dmg hits.
        """
        myduck = ArmoredDuck(ctx.bot, ctx.channel)
        await myduck.spawn()

    @coin.command()
    @checks.server_admin_or_permission("ducks.spawn.golden")
    async def golden(self, ctx: MyContext):
        """
        Spawns a golden duck.
        """
        myduck = GoldenDuck(ctx.bot, ctx.channel)
        await myduck.spawn()

    @coin.command()
    @checks.server_admin_or_permission("ducks.spawn.plastic")
    async def plastic(self, ctx: MyContext):
        """
        Spawns a plastic duck.
        """
        myduck = PlasticDuck(ctx.bot, ctx.channel)
        await myduck.spawn()

    @coin.command()
    @checks.server_admin_or_permission("ducks.spawn.kamikaze")
    async def kamikaze(self, ctx: MyContext):
        """
        Spawns a plastic duck.
        """
        myduck = KamikazeDuck(ctx.bot, ctx.channel)
        await myduck.spawn()


setup = DucksSpawningCommands.setup
