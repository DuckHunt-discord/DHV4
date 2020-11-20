import asyncio
import random
import time
import datetime
from typing import Optional

import discord
from discord.ext import commands

from utils import checks
from utils.bot_class import MyBot
from utils.interaction import get_webhook_if_possible

from utils.ducks import Duck, SuperDuck

from babel.dates import format_timedelta

from utils.cog_class import Cog
from utils.ctx_class import MyContext
from utils.levels import get_level_info
from utils.models import get_from_db, get_player, Player, get_random_player


def get_timedelta(event, now):
    return datetime.datetime.fromtimestamp(event) - datetime.datetime.fromtimestamp(now)


def compute_luck(luck_pct):
    current = random.randint(1, 100)
    return current <= luck_pct


class DucksHuntingCommands(Cog):
    @commands.command(aliases=["pan", "pew", "pang", "shoot", "bong", "bonk", "kill", "itshighnoon", "its_high_noon", "killthatfuckingduck", "kill_that_fucking_duck", "kill_that_fucking_duck_omg"])
    @checks.channel_enabled()
    async def bang(self, ctx: MyContext, target: Optional[discord.Member], *args):
        """
        Shoot at the duck that appeared first on the channel.
        """
        _ = await ctx.get_translate_function()
        db_hunter: Player = await get_player(ctx.author, ctx.channel)
        now = int(time.time())

        language_code = await ctx.get_language_code()

        if db_hunter.active_powerups['wet'] > now:
            db_hunter.shooting_stats['shots_when_wet'] += 1
            await db_hunter.save()

            td = get_timedelta(db_hunter.active_powerups['wet'], now)
            await ctx.reply(_("Dude... Your clothes are wet, at least dry them (for **{time_delta}**) or something, or buy new ones (`{ctx.prefix}shop clothes`)",
                              ctx=ctx,
                              time_delta=format_timedelta(td, locale=language_code)))
            return False

        if db_hunter.weapon_confiscated:
            db_hunter.shooting_stats['shots_when_confiscated'] += 1
            await db_hunter.save()

            await ctx.reply(_("Dude... Your weapon has been confiscated. Wait for freetime (`{ctx.prefix}freetime`), or buy it back in the shop (`{ctx.prefix}shop weapon`)",
                              ctx=ctx))
            return False

        sabotage = db_hunter.weapon_sabotaged_by
        if sabotage:
            db_hunter.weapon_sabotaged_by = None
            db_hunter.weapon_jammed = True
            db_hunter.shooting_stats['shots_when_sabotaged'] += 1
            await db_hunter.save()

            await ctx.reply(_("💥 Your weapon was sabotaged and exploded in your face. You can thank "
                              "{sabotager.member.user.name}#{sabotager.member.user.discriminator} for this bad joke.",
                              sabotager=sabotage))
            return False

        if db_hunter.weapon_jammed:
            db_hunter.shooting_stats['shots_when_jammed'] += 1
            await db_hunter.save()

            await ctx.reply(_("☁️ Your weapon is jammed. Reload it to clean it up !"))
            return False

        if db_hunter.bullets <= 0:
            db_hunter.shooting_stats['shots_with_empty_magazine'] += 1
            await db_hunter.save()

            await ctx.reply(_("🦉 Magazine empty ! Reload or buy bullets ! **EMPTY**: 0 bullet, {magazines} magazines",
                              magazines=db_hunter.magazines))
            return False

        # Jamming
        level_info = get_level_info(db_hunter.experience)
        lucky = compute_luck(level_info['reliability'])
        if db_hunter.active_powerups['grease'] > now:
            lucky = lucky or compute_luck(level_info['reliability'])

        if not lucky:
            db_hunter.shooting_stats['shots_jamming_weapon'] += 1
            db_hunter.weapon_jammed = True
            await db_hunter.save()
            await ctx.reply(_("💥 Your weapon jammed. Consider buying grease next time."))
            return False

        db_hunter.bullets -= 1
        db_channel = await get_from_db(ctx.channel)

        # Missing
        accuracy = level_info['accuracy']
        if db_hunter.active_powerups['sight'] > now:
            accuracy += int((100 - accuracy) / 3)

        missed = not compute_luck(accuracy)
        if (missed and not target) or (target and not missed):
            db_hunter.shooting_stats['missed'] += 1
            db_hunter.experience -= 2

            # Killing
            killed_someone = target or compute_luck(db_channel.kill_on_miss_chance)

            if killed_someone:
                db_hunter.shooting_stats['killed'] += 1
                db_hunter.experience -= 15

                if not target:
                    db_target: Player = await get_random_player(db_channel)
                else:
                    db_target: Player = await get_from_db(target)
                    db_hunter.shooting_stats['murders'] += 1

                db_target.shooting_stats['got_killed'] += 1
                await asyncio.gather(db_target.save(), db_hunter.save())  # Save both at the same time

                await ctx.reply(_("🔫 You took your weapon, you shot... and killed {player.name}. [**WEAPON CONFISCATED**][**MISSED**: -2 exp][**KILL**: -15 exp]",
                                  player=db_target.member.user,
                                  ))
            else:
                await db_hunter.save()
                await ctx.reply(_("🌲 What did you try to aim at ? I guess you shot that tree, over here. [**MISSED**: -2 exp]",))

            return False

        await db_hunter.save()
        duck = await ctx.target_next_duck()

        if duck:
            await duck.shoot(args)
        else:
            await ctx.reply(_("❓️ What are you trying to kill exactly ? There are no ducks here."))
            db_hunter.shooting_stats['shots_without_ducks'] += 1

            await db_hunter.save()


    @commands.command(aliases=["rl"])
    @checks.channel_enabled()
    async def reload(self, ctx: MyContext, *args):
        """
        Reload your gun.
        """
        _ = await ctx.get_translate_function()
        db_hunter: Player = await get_player(ctx.author, ctx.channel)
        now = int(time.time())



        if db_hunter.weapon_confiscated:
            db_hunter.shooting_stats['reloads_when_confiscated'] += 1
            await db_hunter.save()

            await ctx.reply(_("Dude... You don't have a weapon, it has been confiscated. Wait for freetime (`{ctx.prefix}freetime`), or buy it back in the shop (`{ctx.prefix}shop weapon`)",
                              ctx=ctx))
            return False

        if db_hunter.weapon_jammed:
            db_hunter.weapon_jammed = False
            await db_hunter.save()

            await ctx.reply(_("☀️️ Your unjam your weapon !"))
            return True

        level_info = get_level_info(db_hunter.experience)

        if db_hunter.bullets <= 0 and db_hunter.magazines >= 1:
            db_hunter.shooting_stats['reloads'] += 1
            db_hunter.magazines -= 1
            db_hunter.bullets = level_info["bullets"]

            await db_hunter.save()

            await ctx.reply(_("🦉 You reloaded your weapon | Bullets: {current_bullets}/{max_bullets} | Magazines: {current_magazines}/{max_magazines} ",
                              current_bullets=db_hunter.bullets,
                              max_bullets=level_info["bullets"],
                              current_magazines=db_hunter.magazines,
                              max_magazines=level_info["magazines"]))
            return True
        elif db_hunter.bullets > 0:
            db_hunter.shooting_stats['unneeded_reloads'] += 1
            await db_hunter.save()

            await ctx.reply(_("🦉 You don't need to reload your weapon | **Bullets**: {current_bullets}/{max_bullets} | Magazines: {current_magazines}/{max_magazines} ",
                              current_bullets=db_hunter.bullets,
                              max_bullets=level_info["bullets"],
                              current_magazines=db_hunter.magazines,
                              max_magazines=level_info["magazines"]))
            return False
        elif db_hunter.magazines <= 0:
            db_hunter.shooting_stats['unneeded_reloads'] += 1
            await db_hunter.save()

            await ctx.reply(_("🦉 You don't have any magazines. `{ctx.prefix}shop magazine` | Bullets: {current_bullets}/{max_bullets} | **Magazines**: {current_magazines}/{max_magazines} ",
                              current_bullets=db_hunter.bullets,
                              max_bullets=level_info["bullets"],
                              current_magazines=db_hunter.magazines,
                              max_magazines=level_info["magazines"]))
            return False

    @commands.command()
    @checks.channel_enabled()
    async def hug(self, ctx: MyContext, target: Optional[discord.Member], *args):
        """
        Hug the duck that appeared first on the channel.
        """
        _ = await ctx.get_translate_function()
        db_hunter: Player = await get_player(ctx.author, ctx.channel)

        channel = ctx.channel

        if target:
            db_hunter.hugged['players'] += 1
            await db_hunter.save()
            await channel.send(_("{you.mention} hugged {other.mention}. They feel loved.", you=ctx.author, other=target))
            return

        duck = await ctx.target_next_duck()
        if duck:
            await duck.hug(args)
        else:
            await channel.send(_("What are you trying to hug, exactly? A tree?"))
            db_hunter.hugged["nothing"] += 1
            await db_hunter.save()


setup = DucksHuntingCommands.setup
