import random
import time
from typing import Optional

import discord
from babel.dates import format_timedelta
from discord.ext import commands

from utils import checks

from utils.cog_class import Cog
from utils.ctx_class import MyContext
from utils.interaction import get_timedelta
from utils.models import get_player, Player

SECOND = 1
MINUTE = 60 * SECOND
HOUR = 60 * MINUTE
DAY = 24 * HOUR


class NotEnoughExperience(commands.CheckFailure):
    def __init__(self, needed, having):
        self.needed = needed
        self.having = having


class ShoppingCommands(Cog):
    @commands.group(aliases=["buy", "rent", "sh", "sho"])
    @checks.channel_enabled()
    async def shop(self, ctx: MyContext):
        """
        Buy items here
        """
        if not ctx.invoked_subcommand:
            await ctx.send_help(ctx.command)

    def ensure_enough_experience(self, db_hunter, item_cost):
        if db_hunter.experience < item_cost:
            raise NotEnoughExperience(needed=item_cost, having=db_hunter.experience)

    @shop.command(aliases=["1"])
    async def bullet(self, ctx: MyContext):
        """
        Adds a bullet to your current magazine
        """
        ITEM_COST = 7

        _ = await ctx.get_translate_function()
        db_hunter: Player = await get_player(ctx.author, ctx.channel)

        self.ensure_enough_experience(db_hunter, ITEM_COST)

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
        ITEM_COST = 13

        _ = await ctx.get_translate_function()
        db_hunter: Player = await get_player(ctx.author, ctx.channel, giveback=True)

        self.ensure_enough_experience(db_hunter, ITEM_COST)

        level_info = db_hunter.level_info()

        max_magazines = level_info['magazines']
        if db_hunter.magazines >= max_magazines:
            await ctx.reply(_("❌ Whoops, you have too many magazines in your backpack already... Try reloading !"))
            return False

        db_hunter.experience -= ITEM_COST
        db_hunter.magazines += 1
        db_hunter.bought_items['magazines'] += 1

        await db_hunter.save()
        await ctx.reply(_("💸 You added a magazine in your weapon. Time to reload!"))

    @shop.command(aliases=["3", "ap_ammo"])
    async def ap(self, ctx: MyContext):
        """
        Buy AP ammo to double the damage you do to super ducks for 24 hours
        """
        ITEM_COST = 15

        _ = await ctx.get_translate_function()
        language_code = await ctx.get_language_code()
        db_hunter: Player = await get_player(ctx.author, ctx.channel)

        self.ensure_enough_experience(db_hunter, ITEM_COST)

        if db_hunter.is_powerup_active("ap_ammo"):
            time_delta = get_timedelta(db_hunter.active_powerups['ap_ammo'],
                                       time.time())

            await ctx.reply(_("❌ Whoops, your gun is already using AP ammo for {time_delta} !",
                              time_delta=format_timedelta(time_delta, locale=language_code)))
            return False
        elif db_hunter.is_powerup_active("explosive_ammo"):
            time_delta = get_timedelta(db_hunter.active_powerups['explosive_ammo'],
                                       time.time())

            await ctx.reply(_("❌ Your gun is using some even better explosive ammo for {time_delta} !",
                              time_delta=format_timedelta(time_delta, locale=language_code)))
            return False

        db_hunter.experience -= ITEM_COST
        db_hunter.active_powerups["ap_ammo"] = int(time.time()) + DAY
        db_hunter.bought_items['ap_ammo'] += 1

        await db_hunter.save()
        await ctx.reply(_("💸 You bought some AP ammo. Twice the damage, twice the fun!"))

    @shop.command(aliases=["4", "explosive_ammo", "explo"])
    async def explosive(self, ctx: MyContext):
        """
        Buy Explosive ammo to TRIPLE the damage you do to super ducks for 24 hours
        """
        ITEM_COST = 25

        _ = await ctx.get_translate_function()
        language_code = await ctx.get_language_code()
        db_hunter: Player = await get_player(ctx.author, ctx.channel)

        self.ensure_enough_experience(db_hunter, ITEM_COST)

        if db_hunter.is_powerup_active("explosive_ammo"):
            time_delta = get_timedelta(db_hunter.active_powerups['explosive_ammo'],
                                       time.time())

            await ctx.reply(_("❌ Your gun is already explosive ammo for {time_delta} !",
                              time_delta=format_timedelta(time_delta, locale=language_code)))
            return False

        db_hunter.experience -= ITEM_COST
        db_hunter.active_powerups["explosive_ammo"] = int(time.time()) + DAY
        db_hunter.bought_items['explosive_ammo'] += 1

        await db_hunter.save()
        await ctx.reply(_("💸 You bought some **EXPLOSIVE** ammo. Thrice the damage, that'll be bloody!"))

    @shop.command(aliases=["5", "gun", ])
    async def weapon(self, ctx: MyContext):
        """
        Buy back your weapon from the police if it was confiscated.
        """
        ITEM_COST = 30

        _ = await ctx.get_translate_function()
        db_hunter: Player = await get_player(ctx.author, ctx.channel)

        self.ensure_enough_experience(db_hunter, ITEM_COST)

        if not db_hunter.weapon_confiscated:
            await ctx.reply(_("❌ Your gun isn't confiscated, why would you need a new one ?"))
            return False

        db_hunter.experience -= ITEM_COST
        db_hunter.weapon_confiscated = False
        db_hunter.bought_items['weapon'] += 1

        await db_hunter.save()
        await ctx.reply(_("💸 You bribed the police and brought back your weapon. The fun continues."))

    @shop.command(aliases=["6", "lubricant"])
    async def grease(self, ctx: MyContext):
        """
        Add some grease in your weapon to prevent jamming.
        """
        ITEM_COST = 8

        _ = await ctx.get_translate_function()
        db_hunter: Player = await get_player(ctx.author, ctx.channel)

        self.ensure_enough_experience(db_hunter, ITEM_COST)

        if db_hunter.is_powerup_active('grease'):
            await ctx.reply(_("❌ Your gun is already perfectly greased, you don't need any more of that."))
            return False

        db_hunter.experience -= ITEM_COST
        db_hunter.active_powerups["grease"] = int(time.time()) + DAY
        db_hunter.bought_items['grease'] += 1

        await db_hunter.save()
        await ctx.reply(_("💸 You added some grease to your weapon to reduce jamming for a day."))

    @shop.command(aliases=["7",])
    async def sight(self, ctx: MyContext):
        """
        Add a sight to your weapon to improve accuracy.
        """
        ITEM_COST = 6

        _ = await ctx.get_translate_function()
        db_hunter: Player = await get_player(ctx.author, ctx.channel)

        self.ensure_enough_experience(db_hunter, ITEM_COST)

        if db_hunter.active_powerups["sight"]:
            await ctx.reply(_("❌ You added a new sight to your weapon recntly. You don't need a new one."))
            return False

        db_hunter.experience -= ITEM_COST
        db_hunter.active_powerups["sight"] = 12  # 12 shots to go
        db_hunter.bought_items['sight'] += 1

        await db_hunter.save()
        await ctx.reply(_("💸 You added a sight to your weapon to improve your accuracy for the next few shots."))

    @shop.command(aliases=["8", "ir", "infrared", "ir_detector", "infrared_detector"])
    async def detector(self, ctx: MyContext):
        """
        Add an infrared detector to your weapon. Save bullets and shots.
        """
        ITEM_COST = 15

        _ = await ctx.get_translate_function()
        db_hunter: Player = await get_player(ctx.author, ctx.channel)

        self.ensure_enough_experience(db_hunter, ITEM_COST)

        if db_hunter.active_powerups["detector"]:
            await ctx.reply(_("❌ You already have that infrared detector on your weapon."))
            return False

        db_hunter.experience -= ITEM_COST
        db_hunter.active_powerups["detector"] = 6
        db_hunter.bought_items['detector'] += 1

        await db_hunter.save()
        await ctx.reply(_("💸 You added an infrared detector to your weapon. If you can't see ducks, you can't shoot them."))

    @shop.command(aliases=["9", "shhh", "silence"])
    async def silencer(self, ctx: MyContext):
        """
        Add a silencer to your weapon to prevent scaring ducks.
        """
        ITEM_COST = 5

        _ = await ctx.get_translate_function()
        db_hunter: Player = await get_player(ctx.author, ctx.channel)

        self.ensure_enough_experience(db_hunter, ITEM_COST)

        if db_hunter.is_powerup_active('silencer'):
            await ctx.reply(_("❌ You already use a silencer."))
            return False

        db_hunter.experience -= ITEM_COST
        db_hunter.active_powerups["silencer"] = int(time.time()) + DAY
        db_hunter.bought_items['silencer'] += 1

        await db_hunter.save()
        await ctx.reply(_("💸 You added a silencer to your weapon. Ducks are still afraid of the noise, but you don't make any."))

setup = ShoppingCommands.setup
