import datetime
from typing import Optional, List

import babel.lists
import discord
from babel.dates import format_timedelta
from discord import HTTPException, Thread
from discord.ext import commands, tasks
from discord.ext.commands import MaxConcurrency, BucketType
from tortoise import timezone

from utils import models, checks
from utils.bot_class import MyBot
from utils.cog_class import Cog
from utils.ctx_class import MyContext
from utils.models import get_from_db, DiscordMember, AccessLevel


def _(message):
    return message


class Event2021(Cog):
    display_name = _("Landmines")
    help_priority = 9
    help_color = 'primary'

    def __init__(self, bot: MyBot, *args, **kwargs):
        super().__init__(bot, *args, **kwargs)
        self.concurrency = MaxConcurrency(number=1, per=BucketType.member, wait=True)

    async def user_can_play(self, user: discord.Member):
        if user.bot:
            return False

        db_member: DiscordMember = await get_from_db(user)

        if db_member.get_access_level() == AccessLevel.BANNED:
            return False

        return True

    @Cog.listener()
    async def on_message(self, message: discord.Message):
        required_permissions = discord.Permissions(send_messages=True, read_messages=True,
                                                   read_message_history=True, attach_files=True,
                                                   )

        if not message.content:
            # Message has no text
            return

        if not message.guild:
            return

        if not message.channel.permissions_for(message.guild.me).is_superset(required_permissions):
            # No perms
            return

        if isinstance(message.channel, Thread):
            channel = message.channel.parent
        else:
            channel = message.channel

        db_channel = await models.get_from_db(channel)

        if not db_channel:
            ctx: MyContext = await self.bot.get_context(message, cls=MyContext)
            ctx.logger.warning(f"Channel {channel} ({type(channel).__name__}) not found in database by get_from_db, weird..")
            ctx.logger.warning(f"Channel {channel.id} not found in database by get_from_db, weird.")
            return

        if not db_channel.landmines_enabled:
            return

        if not await self.user_can_play(message.author):
            return

        ctx: MyContext = await self.bot.get_context(message, cls=MyContext)
        if ctx.valid:
            # It's just a command.
            return

        await self.bot.wait_until_ready()

        try:
            await self.concurrency.acquire(message)

            db_target = await models.get_member_landminesdata(message.author)

            added_points = db_target.add_points_for_message(message.content)

            landmine = await models.get_landmine(message.guild, message.content)

            if landmine:
                _ = await ctx.get_translate_function()
                landmine.stopped_by = db_target
                landmine.stopped_at = timezone.now()
                duration = landmine.stopped_at - landmine.placed
                landmine.tripped = True

                explosion_value = landmine.value_for(db_target)
                landmine.exploded = explosion_value

                db_target.points_exploded += explosion_value
                db_target.points_current -= explosion_value

                placed_by = await landmine.placed_by

                if placed_by.member_id == db_target.member_id:
                    placed_by = db_target

                placed_by.points_won += explosion_value
                placed_by.points_current += explosion_value + landmine.value / 4

                message_text = discord.utils.escape_mentions(landmine.message)
                if placed_by.member_id != db_target.member_id:
                    await placed_by.save()

                await landmine.save()

                td = format_timedelta(duration, locale=await ctx.get_language_code())
                placed_by_member = await placed_by.member

                if message_text:
                    await ctx.reply(
                        _(
                            "💥 You stepped on a `{landmine.word}` landmine placed {td} ago by <@{placed_by_member.user_id}>. "
                            "It exploded, taking away **{explosion_value} points** from your account.\n\n"
                            "<@{placed_by_member.user_id}> message:\n"
                            "{message_text}",
                            landmine=landmine, placed_by_member=placed_by_member, td=td, explosion_value=explosion_value, message_text=message_text),
                        delete_on_invoke_removed=False)
                else:
                    await ctx.reply(
                        _(
                            "💥 You stepped on a `{landmine.word}` landmine placed {td} ago by <@{placed_by_member.user_id}>. "
                            "It exploded, taking away **{explosion_value} points** from your account.\n\n",
                            landmine=landmine, placed_by_member=placed_by_member, explosion_value=explosion_value, td=td,
                        ),
                        delete_on_invoke_removed=False)

            if landmine or added_points:
                await db_target.save()
        finally:
            await self.concurrency.release(message)

    @commands.command()
    @checks.landmines_commands_enabled()
    async def place(self, ctx: MyContext, guild: discord.Guild, value: Optional[int], word: str, *, message_text: str = ""):
        """
        Alias for dh!landmine landmine, so that you can just type dh!place instead.
        """
        if value is None:
            value = 50

        await self.landmine(ctx, guild, value, word, message_text=message_text)

    @commands.command()
    @commands.guild_only()
    @checks.landmines_commands_enabled()
    async def defuse(self, ctx: MyContext, *, words: str = ""):
        """
        Alias for dh!landmine defuse_kit, so that you can just type dh!defuse instead.
        """
        await self.defuse_kit(ctx, words=words)

    @commands.group(aliases=["landmines", "event2021", "lm"], name="landmine", case_insensitive=True)
    @checks.landmines_commands_enabled()
    async def event(self, ctx: MyContext):
        """
        This command group contains all commands related to "Landmines" game.
        """
        if not ctx.invoked_subcommand:
            await ctx.send_help(ctx.command)

    @event.command()
    @commands.guild_only()
    @checks.landmines_commands_enabled()
    async def me(self, ctx: MyContext, target: discord.Member = None):
        """
        View your event statistics.
        """
        _ = await ctx.get_translate_function()
        if target is None:
            target = ctx.author

        if not await self.user_can_play(target):
            await ctx.reply(_("They can't play the game :("))

        db_target = await models.get_member_landminesdata(target)

        embed = discord.Embed(
            title=_("{target.name} event statistics", target=target),
            colour=discord.Color.green()
        )
        embed.description = _("The most important currency in the game are the points, which are used in the shop to buy "
                              "stuff. The available points show how many ponts you have and how many you acquired in "
                              "total.\n"
                              "You can get points by sending (long) messages. Some shop items may help you get more. "
                              "Be careful not to spam, server rules **still apply** during the event. "
                              "At the end of the game, the player having the greater amount of points will win.")

        embed.add_field(name=_("Available"), value=_("{db_target.points_current} points", db_target=db_target),
                        inline=False)

        embed.add_field(name=_("Messages sent"), value=_("{db_target.messages_sent} ({db_target.words_sent} words)", db_target=db_target),
                        inline=False)

        if db_target.points_won:
            embed.add_field(name=_("Points won by landmines"), value=_("{db_target.points_won} points", db_target=db_target),
                            inline=True)

        if db_target.points_recovered:
            embed.add_field(name=_("Points recovered by defusing landmines"), value=_("{db_target.points_recovered} points", db_target=db_target),
                            inline=True)

        if db_target.points_acquired:
            embed.add_field(name=_("Points acquired by talking"), value=_("{db_target.points_acquired} points", db_target=db_target),
                            inline=True)

        if db_target.points_exploded:
            embed.add_field(name=_("Points exploded by stepping on mines"), value=_("{db_target.points_exploded} points", db_target=db_target),
                            inline=True)

        if db_target.points_spent:
            embed.add_field(name=_("Points spent in the shop"), value=_("{db_target.points_spent} points", db_target=db_target),
                            inline=True)

        embed.set_footer(text=_("For more information on how to place a mine, run the `dh!lm landmines` command."))
        embed.set_author(name=str(target), icon_url=str(target.display_avatar.replace(format="jpg", size=256)))

        await ctx.reply(embed=embed)

    @event.command(aliases=["hl", "hlm", "hmine", "hlandmines", "how_to", "guide"])
    @commands.guild_only()
    @checks.landmines_commands_enabled()
    async def landmine_how_to(self, ctx: MyContext):
        """
        This command explains how to place a landmine
        """
        _ = await ctx.get_translate_function(user_language=True)
        await ctx.send(_("To place a landmine, send a DM to the bot with the following command: ```\n"
                         "dh!landmine place {ctx.guild.id} your_mine_value your_mine_word a_message_to_send_when_the_mine_explodes\n"
                         "```\n"
                         "The value must be at least 50 points, and a word must be at least 3 characters long."))

    @event.command(aliases=["l", "lm", "mine", "landmines", "place"])
    @checks.landmines_commands_enabled()
    async def landmine(self, ctx: MyContext, guild: Optional[discord.Guild], value: int, word: str, *, message_text: str = ""):
        """
        [THIS COMMAND WORKS IN DMs]
        Buy a landmine that will trigger on a specific word.

        A landmine has a value, at least greater than 2, that will be used to determine it's price and the damage done
        to the person that steps on it.
        The word must be at least 2 characters long, and must only contain letters. The steps are case-insensitive.
        The longer it is, the higher the power. An exploding landmine gives you the point damage, and half it's value
        back.
        """
        _ = await ctx.get_translate_function(user_language=True)

        if ctx.guild:
            await ctx.message.delete()
            guild = ctx.guild
            member = ctx.author
        else:
            if guild is None:
                await ctx.author.send(_("❌ On what server do you want to place this landmine ? You need to add the Guild ID at the start of your command. "
                                        "See `dh!landmines landmine_how_to`"))
                return
            try:
                member = await guild.fetch_member(ctx.author.id)
            except HTTPException:
                await ctx.author.send(_("❌ You aren't in that guild."))
                return

        if value < 50:
            await ctx.author.send(_("❌ A landmine must have a value higher than 50."))
            return

        if len(message_text) > 1500:
            await ctx.author.send(_("❌ The message left on the landmine must be less than 1500 characters."))
            return

        word = models.get_valid_words(word)
        if len(word) != 1:
            await ctx.author.send(_("❌ The word must only contain letters."))
            return
        else:
            word = word[0]

        protect = await models.get_word_protect_for(guild, word)

        if protect:
            protect_db_data = await protect.protected_by
            protect_db_member = await protect_db_data.member
            protect_db_user = await protect_db_member.user

            protect.protect_count += 1
            await protect.save()

            if protect.message:
                await ctx.author.send(
                    _("❌ This word is currently protected by {user.name}#{user.discriminator}, you can't place a mine on it — {protect.message}.", value=value, user=protect_db_user, protect=protect))
            else:
                await ctx.author.send(_("❌ This word is currently protected by {user.name}#{user.discriminator}, you can't place a mine on it.", value=value, user=protect_db_user, protect=protect))

            return

        try:
            await self.concurrency.acquire(ctx.message)
            db_data = await models.get_member_landminesdata(member)

            if db_data.points_current < value:
                await ctx.author.send(_("❌ You don't have {value} points, you can't buy a landmine as powerful as this.", value=value))
                return

            landmine = models.LandminesPlaced(
                placed_by=db_data,
                word=word,
                value=value,
                message=message_text,
            )
            db_data.points_current -= value
            db_data.points_spent += value

            await db_data.save()
            await landmine.save()
            await ctx.author.send(_("💣️ You placed a landmine on `{word}` that can give you at most `{base_value}` points.", word=word, base_value=landmine.base_value()))
        finally:
            await self.concurrency.release(ctx.message)

    @event.command(aliases=["p", "s", "shield", "prot"])
    @commands.guild_only()
    @checks.landmines_commands_enabled()
    async def protect(self, ctx: MyContext, word: str, *, message_text: str = ""):
        """
        Buy a shield that will be placed on a given word. A shield will defuse all landmines placed on that word,
        and will prevent further landmines from being placed on it.

        A shield is a very powerful item, that'll cost 500 points for any given word.
        You can however add a message that will be sent when trying to place a mine.
        """
        _ = await ctx.get_translate_function()
        ngettext = await ctx.get_ntranslate_function()

        words_list = models.get_valid_words(word)

        if len(words_list) != 1:
            await ctx.reply(_("❌ Please give one valid words to protect."))
            return

        word = words_list[0]

        try:
            await self.concurrency.acquire(ctx.message)

            protect = await models.get_word_protect_for(ctx.guild, word)

            if protect:
                protect_db_data = await protect.protected_by
                protect_db_member = await protect_db_data.member
                protect_db_user = await protect_db_member.user

                await ctx.send(
                    _("❌ This word is already protected by {user.name}#{user.discriminator}.", user=protect_db_user))
                return

            db_data = await models.get_member_landminesdata(ctx.author)

            if db_data.points_current < 500:
                await ctx.reply(_("❌ You don't have 500 points, so you can't buy a shield to protect a word."))
                return
            else:
                db_data.points_current -= 500
                db_data.points_spent += 500

            db_data.shields_bought += 1

            await models.LandminesProtects.create(
                protected_by=db_data,
                word=word,
                message=message_text
            )

            landmines: List[models.LandminesPlaced] = await models.get_landmine(ctx.guild, word, as_list=True)
            ret = [_("You placed a shield on `{word}` for 500 points.", word=word)]

            now = timezone.now()
            got_points = 0
            landmines_list = []

            for landmine in landmines:
                landmine.stopped_by = db_data
                landmine.disarmed = True
                landmine.stopped_at = now

                money_recovered = landmine.value
                db_data.points_recovered += money_recovered
                db_data.points_current += money_recovered

                got_points += money_recovered

                placed_by = await landmine.placed_by
                placed_by_member = await placed_by.member

                duration = landmine.stopped_at - landmine.placed

                td = format_timedelta(duration, locale=await ctx.get_language_code())

                landmines_list.append(_("- <@{placed_by_member.user_id}> mine for {value} points (placed {td} ago)",
                                        value=money_recovered, placed_by_member=placed_by_member, td=td))

                await landmine.save()

            if len(landmines):
                ret.append(ngettext(
                    "You defused the following landmine for a value of {got_points} points.",
                    "You defused {n} landmines placed on that word, for a total value of {got_points} points.",
                    len(landmines),
                    got_points=got_points,
                ))

                ret.extend(landmines_list)
            else:
                ret.append(_("There were no active landmines on that word to be defused."))

            await db_data.save()
            await ctx.reply("\n".join(ret))
        finally:
            await self.concurrency.release(ctx.message)

    @event.command(aliases=["d", "defuse", "defuse_kits"])
    @commands.guild_only()
    @checks.landmines_commands_enabled()
    async def defuse_kit(self, ctx: MyContext, *, words: str):
        """
        Buy a defuse kit. You can use it on a sentence. If it's used, you collect the landmine value, minus the price
        of the defuse kit (30 points). If you don't use it, you'll just have to pay a restocking fee of 15 points.

        You need at least 30 points to use one.
        """
        _ = await ctx.get_translate_function()

        words_list = models.get_valid_words(words)

        if len(words_list) < 1:
            await ctx.reply(_("❌ Please give (as much) valid words as you want to the defuse kit."))
            return

        landmine = await models.get_landmine(ctx.guild, words)

        try:
            await self.concurrency.acquire(ctx.message)
            db_data = await models.get_member_landminesdata(ctx.author)

            if db_data.points_current < 30:
                await ctx.reply(_("❌ You don't have 30 points, so you can't buy a defuse kit."))
                return

            db_data.defuse_kits_bought += 1

            if landmine:
                landmine.stopped_by = db_data
                landmine.disarmed = True
                landmine.stopped_at = timezone.now()

                money_recovered = landmine.value
                db_data.points_current -= 30
                db_data.points_spent += 30
                db_data.points_recovered += money_recovered
                db_data.points_current += money_recovered

                got_points = money_recovered - 30

                placed_by = await landmine.placed_by
                placed_by_member = await placed_by.member

                duration = landmine.stopped_at - landmine.placed

                td = format_timedelta(duration, locale=await ctx.get_language_code())

                if got_points > 0:
                    await ctx.reply(_("💰️ You used the defuse kit on `{landmine.word}`, and defused "
                                      "<@{placed_by_member.user_id}> landmine (placed {td} ago), that has a `{landmine.value}` points value."
                                      "You got {got_points} points, congratulations.",
                                      landmine=landmine, got_points=got_points, placed_by_member=placed_by_member, td=td),
                                    delete_on_invoke_removed=False)
                else:
                    await ctx.reply(_("💸️ You used the defuse kit on `{landmine.word}`, and defused "
                                      "<@{placed_by_member.user_id}> landmine (placed {td} ago), that has a `{landmine.value}` points value."
                                      "You've lost {-got_points} points, because the value of the landmine was lower "
                                      "than the defuse kit price. Sorry!",
                                      landmine=landmine, got_points=got_points, placed_by_member=placed_by_member, td=td),
                                    delete_on_invoke_removed=False)

                await landmine.save()
            else:
                db_data.points_current -= 15
                db_data.points_spent += 15
                words = babel.lists.format_list(words_list, locale=await ctx.get_language_code())
                await ctx.reply(_("♻️️ You didn't use the defuse kit, and sold it back to the shop. "
                                  "You are sure that there isn't any mine on any of those words: \n"
                                  "```\n"
                                  "{words}\n"
                                  "```",
                                  words=words),
                                delete_on_invoke_removed=False)

            await db_data.save()
        finally:
            await self.concurrency.release(ctx.message)

    @event.command()
    @commands.guild_only()
    @checks.landmines_commands_enabled()
    async def top(self, ctx: MyContext):
        """
        Show statistics about landmines on this server.
        """
        _ = await ctx.get_translate_function()

        db_guild = await models.get_from_db(ctx.guild)

        stats_embed = discord.Embed(colour=discord.Colour.dark_green(),
                                    title=_("Landmines statistics"))

        stats_embed.url = f"https://duckhunt.me/data/guilds/{ctx.guild.id}/landmines/"

        players_count = await models.LandminesUserData.all().filter(member__guild=db_guild).count()
        total_mines_count = await models.LandminesPlaced.all().filter(placed_by__member__guild=db_guild).count()
        current_mines_count = await models.LandminesPlaced.all().filter(placed_by__member__guild=db_guild).filter(stopped_at__isnull=True).count()
        biggest_mine = await models.LandminesPlaced.all().filter(placed_by__member__guild=db_guild).filter(stopped_at__isnull=True).order_by('-value').first()

        negatives_count = await models.LandminesUserData \
            .filter(points_current__lte=0) \
            .filter(member__guild=db_guild) \
            .count()

        stats_embed.add_field(name=_("Players tracked"), value=str(players_count))
        stats_embed.add_field(name=_("Mines count"),
                              value=_("{current_mines_count} mines placed, {total_mines_count} created", current_mines_count=current_mines_count, total_mines_count=total_mines_count))
        if biggest_mine:
            top_placed = await biggest_mine.placed_by
            top_placed_member = await top_placed.member

            stats_embed.add_field(name=_("Biggest active mine"),
                                  value=_("Valued at `{biggest_mine.value} ({letters} letters)`, placed by <@{user}>", biggest_mine=biggest_mine, letters=len(biggest_mine.word),
                                          user=top_placed_member.user_id),
                                  inline=False)
        stats_embed.add_field(name=_("Players in the negative"), value=str(negatives_count))

        top_embed = discord.Embed(colour=discord.Colour.blurple(),
                                  title=_("Event scoreboard"))
        top_embed.url = f"https://duckhunt.me/data/guilds/{ctx.guild.id}/landmines/?discord_embeds=sucks"

        top_players = await models.LandminesUserData.all().filter(member__guild=db_guild).order_by('-points_current').limit(10)

        for i, top_player in enumerate(top_players):
            top_member = await top_player.member
            top_embed.add_field(name=_("{points} points", points=top_player.points_current), value=f"<@{top_member.user_id}>", inline=i > 2)

        await ctx.send(embeds=[stats_embed, top_embed])


setup = Event2021.setup
