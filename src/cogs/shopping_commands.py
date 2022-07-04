import asyncio
import random
import time
from typing import Optional

import discord
from babel.dates import format_timedelta
from discord.ext import commands

from utils import checks, ducks
from utils.coats import Coats, get_random_coat_type
from utils.cog_class import Cog
from utils.ctx_class import MyContext
from utils.events import Events
from utils.interaction import get_timedelta
from utils.models import get_player, Player, get_from_db, DiscordChannel

SECOND = 1
MINUTE = 60 * SECOND
HOUR = 60 * MINUTE
DAY = 24 * HOUR


class NotEnoughExperience(commands.CheckFailure):
    def __init__(self, needed, having):
        self.needed = needed
        self.having = having


def _(message):
    return message


class ShoppingCommands(Cog):
    display_name = _("Shop")
    help_priority = 3

    @commands.group(aliases=["buy", "rent", "sh", "sho"], case_insensitive=True)
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
        else:
            db_hunter.spent_experience += item_cost

    @shop.command(aliases=["1"])
    async def bullet(self, ctx: MyContext):
        """
        Adds a bullet to your current magazine. [7 exp]
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

        await db_hunter.edit_experience_with_levelups(ctx, -ITEM_COST)
        db_hunter.bullets += 1
        db_hunter.bought_items['bullets'] += 1

        await db_hunter.save()
        await ctx.reply(_("💸 You added a bullet in your weapon. [Bought: -{ITEM_COST} exp, total {db_hunter.experience} exp]", db_hunter=db_hunter, ITEM_COST=ITEM_COST))

        if max_bullets > 2:
            await ctx.reply(_("💡 Next time, you might want to buy a magazine, it'll be cheaper for you 😁"))

    @shop.command(aliases=["2", "charger", "mag"])
    async def magazine(self, ctx: MyContext):
        """
        Adds a magazine in your backpack. [13 exp]
        """
        ITEM_COST = 13

        _ = await ctx.get_translate_function()
        db_hunter: Player = await get_player(ctx.author, ctx.channel, giveback=True)

        self.ensure_enough_experience(db_hunter, ITEM_COST)

        level_info = db_hunter.level_info()

        max_magazines = level_info['magazines']
        if db_hunter.magazines >= max_magazines:
            await ctx.reply(_("❌ Whoops, you have too many magazines in your backpack already... Try reloading!"))
            return False

        await db_hunter.edit_experience_with_levelups(ctx, -ITEM_COST)
        db_hunter.magazines += 1
        db_hunter.bought_items['magazines'] += 1

        await db_hunter.save()

        if db_hunter.bullets <= 0:
            await ctx.reply(_("💸 You added a magazine in your weapon. Time to reload! [Bought: -{ITEM_COST} exp, total {db_hunter.experience} exp]", db_hunter=db_hunter, ITEM_COST=ITEM_COST))
        else:
            await ctx.reply(_("💸 You added a magazine in your weapon. [Bought: -{ITEM_COST} exp, total {db_hunter.experience} exp]", db_hunter=db_hunter, ITEM_COST=ITEM_COST))

    @shop.command(aliases=["3", "ap_ammo"])
    async def ap(self, ctx: MyContext):
        """
        Buy AP ammo to double the damage you do to super ducks. [15 exp/24 hrs]
        """
        ITEM_COST = 15

        _ = await ctx.get_translate_function()
        language_code = await ctx.get_language_code()
        if self.bot.current_event == Events.UN_TREATY:
            await ctx.reply(_("❌ A UN treaty bans the use of Armor Piercing and Explosive ammo for now, "
                              "I can't sell that to you. (`{ctx.prefix}event`)",))
            return False

        db_hunter: Player = await get_player(ctx.author, ctx.channel)

        self.ensure_enough_experience(db_hunter, ITEM_COST)

        if db_hunter.is_powerup_active("ap_ammo"):
            time_delta = get_timedelta(db_hunter.active_powerups['ap_ammo'],
                                       time.time())

            await ctx.reply(_("❌ Whoops, your gun is already using AP ammo for {time_delta}!",
                              time_delta=format_timedelta(time_delta, locale=language_code)))
            return False
        elif db_hunter.is_powerup_active("explosive_ammo"):
            time_delta = get_timedelta(db_hunter.active_powerups['explosive_ammo'],
                                       time.time())

            await ctx.reply(_("❌ Your gun is using some even better explosive ammo for {time_delta}!",
                              time_delta=format_timedelta(time_delta, locale=language_code)))
            return False

        await db_hunter.edit_experience_with_levelups(ctx, -ITEM_COST)
        db_hunter.active_powerups["ap_ammo"] = int(time.time()) + DAY
        db_hunter.bought_items['ap_ammo'] += 1

        await db_hunter.save()
        await ctx.reply(_("💸 You bought some AP ammo. Twice the damage, twice the fun! [Bought: -{ITEM_COST} exp, total {db_hunter.experience} exp]", db_hunter=db_hunter, ITEM_COST=ITEM_COST))

    @shop.command(aliases=["4", "explosive_ammo", "explo"])
    async def explosive(self, ctx: MyContext):
        """
        Buy Explosive ammo to TRIPLE the damage you do to super ducks. [25 exp/24 hrs]
        """
        ITEM_COST = 25

        _ = await ctx.get_translate_function()

        if self.bot.current_event == Events.UN_TREATY:
            await ctx.reply(_("❌ A UN treaty bans the use of Armor Piercing and Explosive ammo for now, "
                              "I can't sell that to you. (`{ctx.prefix}event`)",))
            return False

        language_code = await ctx.get_language_code()
        db_hunter: Player = await get_player(ctx.author, ctx.channel)

        self.ensure_enough_experience(db_hunter, ITEM_COST)

        if db_hunter.is_powerup_active("explosive_ammo"):
            time_delta = get_timedelta(db_hunter.active_powerups['explosive_ammo'],
                                       time.time())

            await ctx.reply(_("❌ Your gun is already using explosive ammo for {time_delta}!",
                              time_delta=format_timedelta(time_delta, locale=language_code)))
            return False

        await db_hunter.edit_experience_with_levelups(ctx, -ITEM_COST)
        db_hunter.active_powerups["explosive_ammo"] = int(time.time()) + DAY
        db_hunter.bought_items['explosive_ammo'] += 1

        await db_hunter.save()
        await ctx.reply(_("💸 You bought some **EXPLOSIVE** ammo. Thrice the damage, that'll be bloody! [Bought: -{ITEM_COST} exp, total {db_hunter.experience} exp]", db_hunter=db_hunter, ITEM_COST=ITEM_COST))

    @shop.command(aliases=["5", "gun", ])
    async def weapon(self, ctx: MyContext):
        """
        Buy back your weapon from the police if it was confiscated. [30 exp]
        """
        ITEM_COST = 30

        _ = await ctx.get_translate_function()
        db_hunter: Player = await get_player(ctx.author, ctx.channel)

        self.ensure_enough_experience(db_hunter, ITEM_COST)

        if not db_hunter.is_powerup_active('confiscated'):
            await ctx.reply(_("❌ Your gun isn't confiscated, why would you need a new one ?"))
            return False

        await db_hunter.edit_experience_with_levelups(ctx, -ITEM_COST)
        db_hunter.active_powerups['confiscated'] = 0
        db_hunter.bought_items['weapon'] += 1

        await db_hunter.save()
        f = discord.File("assets/bribes.gif")
        await ctx.reply(_("💸 You bribed the police and bought back your weapon. The fun continues. [Bought: -{ITEM_COST} exp, total {db_hunter.experience} exp]", db_hunter=db_hunter, ITEM_COST=ITEM_COST), file=f)

    @shop.command(aliases=["6", "lubricant"])
    async def grease(self, ctx: MyContext):
        """
        Add some grease in your weapon to prevent jamming. [8 exp/24 hrs]
        """
        ITEM_COST = 8

        _ = await ctx.get_translate_function()
        db_hunter: Player = await get_player(ctx.author, ctx.channel)

        self.ensure_enough_experience(db_hunter, ITEM_COST)

        if db_hunter.is_powerup_active('grease'):
            await ctx.reply(_("❌ Your gun is already perfectly greased, you don't need any more of that."))
            return False

        await db_hunter.edit_experience_with_levelups(ctx, -ITEM_COST)
        db_hunter.active_powerups["grease"] = int(time.time()) + DAY
        db_hunter.bought_items['grease'] += 1

        await db_hunter.save()
        await ctx.reply(_("💸 You added some grease to your weapon to reduce jamming for a day. [Bought: -{ITEM_COST} exp, total {db_hunter.experience} exp]", db_hunter=db_hunter, ITEM_COST=ITEM_COST))

    @shop.command(aliases=["7", ])
    async def sight(self, ctx: MyContext):
        """
        Add a sight to your weapon to improve accuracy. [6 exp/12 shots]
        """
        ITEM_COST = 6

        _ = await ctx.get_translate_function()
        db_hunter: Player = await get_player(ctx.author, ctx.channel)

        self.ensure_enough_experience(db_hunter, ITEM_COST)

        if db_hunter.is_powerup_active("sight"):
            await ctx.reply(_("❌ You added a new sight to your weapon recently. "
                              "You don't need a new one for your next {uses} shots.",
                              uses=db_hunter.active_powerups["sight"]))
            return False

        await db_hunter.edit_experience_with_levelups(ctx, -ITEM_COST)
        db_hunter.active_powerups["sight"] = 12  # 12 shots to go
        db_hunter.bought_items['sight'] += 1

        await db_hunter.save()
        await ctx.reply(_("💸 You added a sight to your weapon to improve your accuracy for the next few shots. [Bought: -{ITEM_COST} exp, total {db_hunter.experience} exp]", db_hunter=db_hunter, ITEM_COST=ITEM_COST))

    @shop.command(aliases=["8", "ir", "infrared", "ir_detector", "infrared_detector"])
    async def detector(self, ctx: MyContext):
        """
        Add an infrared detector to your weapon. Save bullets and shots. [15 exp/6 shots]
        """
        ITEM_COST = 15

        _ = await ctx.get_translate_function()
        db_hunter: Player = await get_player(ctx.author, ctx.channel)

        self.ensure_enough_experience(db_hunter, ITEM_COST)

        if db_hunter.is_powerup_active("detector"):
            await ctx.reply(_("❌ You already have that infrared detector on your weapon. "
                              "It is still good for {times} missed shots.",
                              times=db_hunter.active_powerups["detector"]))
            return False

        await db_hunter.edit_experience_with_levelups(ctx, -ITEM_COST)
        db_hunter.active_powerups["detector"] = 6
        db_hunter.bought_items['detector'] += 1

        await db_hunter.save()
        await ctx.reply(_("💸 You added an infrared detector to your weapon. If you can't see ducks, you can't shoot them. [Bought: -{ITEM_COST} exp, total {db_hunter.experience} exp]", db_hunter=db_hunter, ITEM_COST=ITEM_COST))

    @shop.command(aliases=["9", "shhh", "silence"])
    async def silencer(self, ctx: MyContext):
        """
        Add a silencer to your weapon to prevent scaring ducks. [5 exp/24* hrs]
        """
        ITEM_COST = 5

        _ = await ctx.get_translate_function()

        db_hunter: Player = await get_player(ctx.author, ctx.channel)

        self.ensure_enough_experience(db_hunter, ITEM_COST)

        if db_hunter.is_powerup_active('silencer'):
            language_code = await ctx.get_language_code()
            time_delta = get_timedelta(db_hunter.active_powerups['silencer'],
                                       time.time())

            await ctx.reply(_("❌ You already use a silencer. It's still good for {time_delta}, come back then.",
                              time_delta=format_timedelta(time_delta, locale=language_code)))
            return False

        await db_hunter.edit_experience_with_levelups(ctx, -ITEM_COST)
        db_hunter.active_powerups["silencer"] = int(time.time()) + DAY

        if db_hunter.prestige >= 6:
            db_hunter.active_powerups["silencer"] += DAY

        db_hunter.bought_items['silencer'] += 1

        await db_hunter.save()
        if db_hunter.prestige >= 6:
            await ctx.reply(_("💸 You added a military-grade silencer to your weapon. You seem to know the game well. [Bought: -{ITEM_COST} exp, total {db_hunter.experience} exp]", db_hunter=db_hunter, ITEM_COST=ITEM_COST))
        else:
            await ctx.reply(_("💸 You added a silencer to your weapon. Ducks are still afraid of the noise, but you don't make any. [Bought: -{ITEM_COST} exp, total {db_hunter.experience} exp]", db_hunter=db_hunter, ITEM_COST=ITEM_COST))

    @shop.command(aliases=["10", "best", "freeexp", "freexp", "4-leaf", "4leaf", "🍀"])
    async def clover(self, ctx: MyContext):
        """
        Buy a 4-Leaf clover to get more exp for every duck you kill :). [13 exp/24 hrs]

        You can always buy a new clover during the florist event, but the price will be doubled if you had a clover already.
        """
        ITEM_COST = 13

        _ = await ctx.get_translate_function()
        language_code = await ctx.get_language_code()

        db_hunter: Player = await get_player(ctx.author, ctx.channel)
        db_channel: DiscordChannel = await get_from_db(ctx.channel)

        if db_hunter.is_powerup_active('clover'):
            if self.bot.current_event == Events.FLORIST:
                try:
                    self.ensure_enough_experience(db_hunter, ITEM_COST * 2)
                except NotEnoughExperience:
                    db_hunter.shooting_stats['cops_seen'] += 1
                    await db_hunter.save()
                    await ctx.reply(_("❌ You tried to throw your old clover to buy a new one at the new florist. "
                                      "Unfortunately, there is a cop around and you don't have enough exp to pay a "
                                      "littering fine of {fine} exp.",
                                      fine=ITEM_COST))
                    return False
                db_hunter.shooting_stats['thrown_clovers'] += 1
                await ctx.reply(_("🍀 You throw your old clover to buy a new one at the new florist. "
                                  "Unfortunately, a cop catches you and fines you {fine} exp for littering.",
                                  fine=ITEM_COST))
                ITEM_COST *= 2
            else:
                time_delta = get_timedelta(db_hunter.active_powerups['clover'],
                                           time.time())
                await ctx.reply(_("❌ You already use a 4-Leaf clover. Try your luck again in {time_delta}!",
                                  time_delta=format_timedelta(time_delta, locale=language_code)))
                return False

        self.ensure_enough_experience(db_hunter, ITEM_COST)

        max_experience = db_channel.clover_max_experience
        if self.bot.current_event == Events.FLORIST:
            max_experience *= 2

        clover_exp = random.randint(db_channel.clover_min_experience, max_experience)
        await db_hunter.edit_experience_with_levelups(ctx, -ITEM_COST)
        db_hunter.active_powerups["clover"] = int(time.time()) + DAY
        db_hunter.active_powerups["clover_exp"] = clover_exp

        db_hunter.bought_items['clover'] += 1

        await db_hunter.save()
        await ctx.reply(
            _("🍀 You bought a 4-Leaf clover. Every time you kill a duck, you'll get {clover_exp} more experience points."
              " [Bought: -{ITEM_COST} exp, total {db_hunter.experience} exp]", db_hunter=db_hunter, ITEM_COST=ITEM_COST,
              clover_exp=clover_exp))

    @shop.command(aliases=["11", "glasses", "👓️", "🕶️", "😎"])
    async def sunglasses(self, ctx: MyContext):
        """
        Protects from mirror-induced glare. [5 exp/24 hrs]
        """
        ITEM_COST = 5

        _ = await ctx.get_translate_function()

        db_hunter: Player = await get_player(ctx.author, ctx.channel)

        self.ensure_enough_experience(db_hunter, ITEM_COST)

        previously_had = db_hunter.is_powerup_active('sunglasses')

        await db_hunter.edit_experience_with_levelups(ctx, -ITEM_COST)
        db_hunter.active_powerups["sunglasses"] = int(time.time()) + DAY
        db_hunter.active_powerups["mirror"] = 0

        if previously_had:
            db_hunter.bought_items['useless_sunglasses'] += 1
        else:
            db_hunter.bought_items['sunglasses'] += 1

        await db_hunter.save()
        if previously_had:
            await ctx.reply(_("😎 You bought sunglasses, again... What a waste. [Bought: -{ITEM_COST} exp, total {db_hunter.experience} exp]", db_hunter=db_hunter, ITEM_COST=ITEM_COST))
        else:
            await ctx.reply(_("😎 You bought sunglasses. [Bought: -{ITEM_COST} exp, total {db_hunter.experience} exp]", db_hunter=db_hunter, ITEM_COST=ITEM_COST))

    @shop.command(aliases=["12", "shirt", "dry"])
    async def clothes(self, ctx: MyContext):
        """
        A new set of clothes. Useful if you are wet. [7 exp]
        """
        ITEM_COST = 7

        _ = await ctx.get_translate_function()

        db_hunter: Player = await get_player(ctx.author, ctx.channel)

        self.ensure_enough_experience(db_hunter, ITEM_COST)

        await db_hunter.edit_experience_with_levelups(ctx, -ITEM_COST)
        db_hunter.active_powerups["wet"] = 0

        db_hunter.bought_items['clothes'] += 1

        await db_hunter.save()
        await ctx.reply(_("💸 You bought some new clothes. You look very good. Maybe the ducks will like your outfit. [Bought: -{ITEM_COST} exp, total {db_hunter.experience} exp]", db_hunter=db_hunter, ITEM_COST=ITEM_COST))

    @shop.command(aliases=["13", "clean"])
    async def brush(self, ctx: MyContext):
        """
        Clean your gun, removing sabotage and sand. [7 exp]
        """
        ITEM_COST = 7

        _ = await ctx.get_translate_function()

        db_hunter: Player = await get_player(ctx.author, ctx.channel)

        self.ensure_enough_experience(db_hunter, ITEM_COST)

        # We don't want to send a level down message here.
        # https://github.com/DuckHunt-discord/DHV4/issues/41
        db_hunter.experience -= ITEM_COST

        db_hunter.active_powerups["sand"] = 0
        db_hunter.weapon_sabotaged_by = None

        db_hunter.bought_items['brush'] += 1

        await db_hunter.save()
        await ctx.reply(_("💸 You've just cleaned your weapon. Could've just shot once, but heh ¯\\_(ツ)_/¯. [Bought: -{ITEM_COST} exp, total {db_hunter.experience} exp]", db_hunter=db_hunter, ITEM_COST=ITEM_COST))

    @shop.command(aliases=["14"])
    async def mirror(self, ctx: MyContext, target: discord.Member):
        """
        Dazzle another hunter using the power of sunlight. [7 exp]
        """
        ITEM_COST = 7

        _ = await ctx.get_translate_function()

        if target.id == ctx.author.id:
            await ctx.reply(_("❌ Don't play with fire, kid! Go somewhere else."))
            return False
        elif target.bot:
            await ctx.reply(_("❌ I don't think {target.mention} can play DuckHunt yet...", target=target))
            return False

        db_hunter: Player = await get_player(ctx.author, ctx.channel)
        db_target: Player = await get_player(target, ctx.channel)

        self.ensure_enough_experience(db_hunter, ITEM_COST)

        await db_hunter.edit_experience_with_levelups(ctx, -ITEM_COST)

        if not db_target.is_powerup_active('sunglasses'):
            db_target.active_powerups["mirror"] = 1
            db_hunter.bought_items['mirror'] += 1
            stupid = False
        else:
            db_hunter.bought_items['useless_mirror'] += 1
            stupid = True

        await asyncio.gather(db_hunter.save(), db_target.save())

        if stupid:
            await ctx.reply(
                _("💸 You are redirecting ☀️ sunlight towards {target.mention} eyes 👀 using your mirror. "
                  "That was kinda stupid, since they have sunglasses 😎. [Bought: -{ITEM_COST} exp, total {db_hunter.experience} exp]", db_hunter=db_hunter, ITEM_COST=ITEM_COST, target=target))
        else:
            await ctx.reply(_("💸 You are redirecting ☀️ sunlight towards {target.mention} eyes 👀 using your mirror. [Bought: -{ITEM_COST} exp, total {db_hunter.experience} exp]", db_hunter=db_hunter, ITEM_COST=ITEM_COST, target=target))

    @shop.command(aliases=["15", "handful_of_sand"])
    async def sand(self, ctx: MyContext, target: discord.Member):
        """
        Throw sand into another player weapon.
        This will increase their jamming chances for their next shot. [7 exp]
        """
        ITEM_COST = 7

        _ = await ctx.get_translate_function()

        if target.id == ctx.author.id:
            await ctx.reply(_("❌ Don't play with fire, kid! Go somewhere else."))
            return False
        elif target.bot:
            await ctx.reply(_("❌ I don't think {target.mention} can play DuckHunt yet...", target=target))
            return False

        db_hunter: Player = await get_player(ctx.author, ctx.channel)
        db_target: Player = await get_player(target, ctx.channel)

        self.ensure_enough_experience(db_hunter, ITEM_COST)

        await db_hunter.edit_experience_with_levelups(ctx, -ITEM_COST)

        db_target.active_powerups["sand"] = 1
        db_target.active_powerups["grease"] = 0
        db_hunter.bought_items['sand'] += 1

        await asyncio.gather(db_hunter.save(), db_target.save())

        await ctx.reply(_("💸 You threw sand in {target.mention} weapon... Not cool! [Bought: -{ITEM_COST} exp, total {db_hunter.experience} exp]", db_hunter=db_hunter, ITEM_COST=ITEM_COST, target=target))

    @shop.command(aliases=["16", "water", "water_bucket", "bukkit", "spigot"])
    async def bucket(self, ctx: MyContext, target: discord.Member):
        """
        Throw a bucket of water on the hunter of your choice,
        forcing them to wait 1h for their clothes to dry before hunting again. [10 exp/1* hrs]
        """
        ITEM_COST = 10

        _ = await ctx.get_translate_function()
        if target.id == ctx.author.id:
            await ctx.reply(_("❌ Don't play with fire, kid! Go somewhere else."))
            return False
        elif target.bot:
            await ctx.reply(_("❌ I don't think {target.mention} can play DuckHunt yet...", target=target))
            return False

        db_hunter: Player = await get_player(ctx.author, ctx.channel)
        db_target: Player = await get_player(target, ctx.channel)

        self.ensure_enough_experience(db_hunter, ITEM_COST)

        await db_hunter.edit_experience_with_levelups(ctx, -ITEM_COST)

        target_has_coat = db_target.is_powerup_active('coat')

        if not target_has_coat:
            db_hunter.bought_items['bucket'] += 1
            if db_hunter.prestige >= 4:
                db_target.active_powerups["wet"] = int(time.time()) + 3 * HOUR
            else:
                db_target.active_powerups["wet"] = int(time.time()) + HOUR
        else:
            db_hunter.bought_items['useless_bucket'] += 1

        await asyncio.gather(db_hunter.save(), db_target.save())

        if target_has_coat:
            await ctx.reply(_("💸 You threw water on {target.mention}... But they have a raincoat on. [Fail: -{ITEM_COST} exp]", ITEM_COST=ITEM_COST, target=target))
        elif db_hunter.prestige >= 4:
            await ctx.reply(_("💸 You threw some icelandic water on {target.mention}... They can't hunt for **three** hours! [Bought: -{ITEM_COST} exp, total {db_hunter.experience} exp]", db_hunter=db_hunter, ITEM_COST=ITEM_COST, target=target))
        else:
            await ctx.reply(_("💸 You threw water on {target.mention}... They can't hunt for an hour! [Bought: -{ITEM_COST} exp, total {db_hunter.experience} exp]", db_hunter=db_hunter, ITEM_COST=ITEM_COST, target=target))

    @shop.command(aliases=["17", "boom"])
    async def sabotage(self, ctx: MyContext, target: discord.Member):
        """
        Sabotage the weapon of another player.
        Their gun will jam and explode in their face the next time they press the trigger. [14* exp]
        """
        ITEM_COST = 14

        _ = await ctx.get_translate_function(user_language=True)
        if target.id == ctx.author.id:
            await ctx.reply(_("❌ Don't play with fire, kid! Go somewhere else."))
            return False
        elif target.bot:
            await ctx.reply(_("❌ I don't think {target.mention} can play DuckHunt yet...", target=target))
            return False

        try:
            await ctx.message.delete()
        except discord.Forbidden:
            pass

        db_hunter: Player = await get_player(ctx.author, ctx.channel)

        if db_hunter.get_current_coat_color() == Coats.BLACK:
            ITEM_COST = 11

        db_target: Player = await get_player(target, ctx.channel)

        if db_target.weapon_sabotaged_by:
            await ctx.reply(_("❌ That weapon is already sabotaged."))
            return False

        self.ensure_enough_experience(db_hunter, ITEM_COST)

        # We don't want to send a level down message here.
        # https://github.com/DuckHunt-discord/DHV4/issues/41
        db_hunter.experience -= ITEM_COST

        db_target.weapon_sabotaged_by = db_hunter
        db_hunter.bought_items['sabotage'] += 1

        await asyncio.gather(db_hunter.save(), db_target.save())

        try:
            await ctx.author.send(_("💸 You sabotaged {target.mention} weapon... They don't know... yet! [Bought: -{ITEM_COST} exp, total {db_hunter.experience} exp]", db_hunter=db_hunter, ITEM_COST=ITEM_COST, target=target, ))
        except discord.Forbidden:
            await ctx.reply(_("I couldn't DM you... Are your DMs blocked ? Anyway, you sabotaged {target.name} weapon... "
                              "They don't know... yet! [Bought: -{ITEM_COST} exp, total {db_hunter.experience} exp]", db_hunter=db_hunter, ITEM_COST=ITEM_COST, target=target,))

    @shop.command(aliases=["20", "duck"])
    async def decoy(self, ctx: MyContext):
        """
        Place a decoy to make a duck spawn in the next 10 minutes. [8 exp]
        """
        ITEM_COST = 8

        _ = await ctx.get_translate_function(user_language=True)

        try:
            await ctx.message.delete()
        except (discord.Forbidden, discord.NotFound):
            pass

        db_hunter: Player = await get_player(ctx.author, ctx.channel)

        self.ensure_enough_experience(db_hunter, ITEM_COST)

        await db_hunter.edit_experience_with_levelups(ctx, -ITEM_COST)

        db_hunter.bought_items['decoy'] += 1

        await db_hunter.save()

        delay = random.randint(MINUTE, 10 * MINUTE)

        async def spawn():
            await asyncio.sleep(delay)
            await ducks.spawn_random_weighted_duck(self.bot, ctx.channel)

        asyncio.ensure_future(spawn())

        await ctx.reply(_("💸 You placed a decoy on the channel, the ducks will come soon! [Bought: -{ITEM_COST} exp, total {db_hunter.experience} exp]", db_hunter=db_hunter, ITEM_COST=ITEM_COST, ))

    @shop.command(aliases=["23", "mecha"])
    async def mechanical(self, ctx: MyContext):
        """
        Spawn a fake duck in exactly 90 seconds. [15 exp]
        """
        ITEM_COST = 15

        _ = await ctx.get_translate_function(user_language=True)

        try:
            await ctx.message.delete()
        except discord.Forbidden:
            pass

        db_hunter: Player = await get_player(ctx.author, ctx.channel)

        self.ensure_enough_experience(db_hunter, ITEM_COST)

        await db_hunter.edit_experience_with_levelups(ctx, -ITEM_COST)

        db_hunter.bought_items['mechanical_duck'] += 1

        await db_hunter.save()

        async def spawn():
            await asyncio.sleep(90)
            await ducks.MechanicalDuck(bot=self.bot, channel=ctx.channel, creator=ctx.author).spawn()

        asyncio.ensure_future(spawn())

        try:
            await ctx.author.send(_("💸 You started a mechanical duck on {channel.mention}, it will spawn in 90 seconds. [Bought: -{ITEM_COST} exp, total {db_hunter.experience} exp]", db_hunter=db_hunter, ITEM_COST=ITEM_COST, channel=ctx.channel))
        except discord.Forbidden:
            await ctx.reply(_("💸 You started a mechanical duck on {channel.mention}, it will spawn in 90 seconds. [Bought: -{ITEM_COST} exp].\n**I couldn't DM you this message**", ITEM_COST=ITEM_COST, channel=ctx.channel))

    @shop.command(aliases=["26", "kway", "breizh", "rain_coat", "raincoat"])
    async def coat(self, ctx: MyContext, *, color: Optional[Coats] = None):
        """
        Protect yourself from water. If you are already wet, it also can be used as a change. [15 exp/24 hrs]
        """
        ITEM_COST = 15

        _ = await ctx.get_translate_function()

        db_hunter: Player = await get_player(ctx.author, ctx.channel)

        self.ensure_enough_experience(db_hunter, ITEM_COST)

        if color is None:
            color = get_random_coat_type()
        elif db_hunter.prestige < 2:
            await ctx.reply(_("❌ I'm afraid you cannot choose your coat color yet."))
            return

        await db_hunter.edit_experience_with_levelups(ctx, -ITEM_COST)
        db_hunter.active_powerups["wet"] = 0
        db_hunter.active_powerups["coat"] = int(time.time()) + DAY
        db_hunter.active_powerups["coat_color"] = color.name

        db_hunter.bought_items['coat'] += 1

        await db_hunter.save()
        await ctx.reply(_("💸 You bought a new, **{color}** coat. \nYou don't look very good, "
                          "but you are very much protected from water.\n\n"
                          "The tag on the coat says the following :\n"
                          "> 100% Polyester, machine washable\n"
                          "> {hint}\n"
                          "> Made in a CACAD factory also producing homing bullets\n\n"
                          "[Bought: -{ITEM_COST} exp, total {db_hunter.experience} exp]",
                          db_hunter=db_hunter,
                          ITEM_COST=ITEM_COST,
                          color=_(color.value[0]).lower(),
                          hint=_(color.value[1])
                          ))


    @shop.command(aliases=["29", "licence", "kill_permit", "permit", "licence_to_kill", "license_to_kill",
                           "licencetokill", "licensetokill", "kill_licence", "kill_license",
                           "killlicence", "killlicense"])
    async def license(self, ctx: MyContext):
        """
        Avoid penalties if you accidentally kill another hunter. [15 exp/24 hrs]
        """
        ITEM_COST = 15

        _ = await ctx.get_translate_function()

        db_hunter: Player = await get_player(ctx.author, ctx.channel)

        self.ensure_enough_experience(db_hunter, ITEM_COST)

        if db_hunter.is_powerup_active('kill_licence'):
            await ctx.reply(_("❌ You already use a kill license."))
            return False

        await db_hunter.edit_experience_with_levelups(ctx, -ITEM_COST)
        db_hunter.active_powerups["kill_licence"] = int(time.time()) + DAY

        db_hunter.bought_items['kill_licence'] += 1

        await db_hunter.save()
        await ctx.reply(_("💸 You bought a kill license. Accidental kills are now allowed. "
                          "[Bought: -{ITEM_COST} exp, total {db_hunter.experience} exp]", db_hunter=db_hunter, ITEM_COST=ITEM_COST))

    @shop.command(aliases=["30", "autoreload", "autoreloader", "automatic_reloader", "automaticreloader", "auto_reloader", "auto_reload"])
    async def reloader(self, ctx: MyContext):
        """
        Automatically reloads your weapon every time it's necessary. [35 exp/24 hrs]
        """
        ITEM_COST = 35

        _ = await ctx.get_translate_function()

        db_hunter: Player = await get_player(ctx.author, ctx.channel)

        if db_hunter.is_powerup_active('reloader'):
            await ctx.reply(_("❌ You already have an automatic reloader."))
            return False


        self.ensure_enough_experience(db_hunter, ITEM_COST)

        await db_hunter.edit_experience_with_levelups(ctx, -ITEM_COST)
        db_hunter.active_powerups["reloader"] = int(time.time()) + DAY

        db_hunter.bought_items['reloader'] += 1

        await db_hunter.save()
        await ctx.reply(_("💸 You bought an auto reloader for your weapon. It'll reload automatically every time it's necessary for a day. "
                          "[Bought: -{ITEM_COST} exp, total {db_hunter.experience} exp]", db_hunter=db_hunter, ITEM_COST=ITEM_COST))

    @shop.command(aliases=["50", "homing"])
    async def homing_bullets(self, ctx: MyContext):
        """
        Never miss a shot again with Homing Projectiles. [150 exp/Limited Duration]
        """
        ITEM_COST = 150

        _ = await ctx.get_translate_function(user_language=True)

        db_hunter: Player = await get_player(ctx.author, ctx.channel)

        if db_hunter.is_powerup_active('homing_bullets'):
            await ctx.reply(_("❌ You already have homing bullets."))
            return False

        self.ensure_enough_experience(db_hunter, ITEM_COST)

        await db_hunter.edit_experience_with_levelups(ctx, -ITEM_COST)

        db_hunter.bought_items['homing_bullets'] += 1
        db_hunter.active_powerups["homing_bullets"] = 1

        await db_hunter.save()

        await ctx.reply(_("💸 You are now using the brand new Homing Bullets made by CACAD (the Comitee Against the Comitee Against Ducks) in China. "
                          "Try them soon! [Bought: -{ITEM_COST} exp, total {db_hunter.experience} exp]", db_hunter=db_hunter, ITEM_COST=ITEM_COST, channel=ctx.channel))


setup = ShoppingCommands.setup
