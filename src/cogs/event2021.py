import asyncio
import datetime
import random

import discord
from babel.dates import format_timedelta
from discord.ext import commands, tasks
from discord.ext.commands import MaxConcurrency, BucketType
from tortoise.functions import Sum

from utils import models
from utils.bot_class import MyBot
from utils.checks import NotInChannel
from utils.cog_class import Cog
from utils.ctx_class import MyContext
from utils.interaction import purge_channel_messages


class Event2021(Cog):
    def __init__(self, bot: MyBot, *args, **kwargs):
        super().__init__(bot, *args, **kwargs)
        self.concurrency = MaxConcurrency(number=1, per=BucketType.user, wait=True)
        self.scoreboard_loop.start()

    def cog_unload(self):
        self.scoreboard_loop.cancel()

    async def is_in_command_channel(self, ctx, allow_dm=False):
        channel_id = self.config()['commands_channel_id']
        if allow_dm and not ctx.guild:
            return True
        elif ctx.channel.id != channel_id:
            raise NotInChannel(must_be_in_channel_id=channel_id)

        return True

    async def user_can_play(self, user):
        if user.bot:
            return False

        return True

    @Cog.listener()
    async def on_message(self, message: discord.Message):
        if not message.content:
            # Message has no text
            return

        if not message.guild:
            return

        if message.guild.id != self.config()['server_id']:
            return

        if message.channel.id not in self.config()['enabled_on']:
            return

        if not await self.user_can_play(message.author):
            return

        ctx = await self.bot.get_context(message, cls=MyContext)
        if ctx.valid:
            # It's just a command.
            return

        await self.bot.wait_until_ready()

        try:
            await self.concurrency.acquire(message)

            db_target = await models.get_user_eventdata(message.author)

            added_points = db_target.add_points_for_message(message.content)

            landmine = await models.get_landmine(message.content)

            if landmine:
                landmine.stopped_by = db_target
                landmine.stopped_at = datetime.datetime.now(datetime.timezone.utc)
                duration = landmine.stopped_at - landmine.placed
                landmine.tripped = True

                explosion_value = landmine.value_for(db_target)
                landmine.exploded = explosion_value

                db_target.points_exploded += explosion_value
                db_target.points_current -= explosion_value

                placed_by = await landmine.placed_by

                if placed_by.user_id == db_target.user_id:
                    placed_by = db_target

                placed_by.points_won += explosion_value
                placed_by.points_current += explosion_value + landmine.value / 4

                message_text = discord.utils.escape_mentions(landmine.message)
                if placed_by.user_id != db_target.user_id:
                    await placed_by.save()

                await landmine.save()

                td = format_timedelta(duration, locale="en_US")
                if message_text:
                    await ctx.reply(
                        f"💥 You stepped on a `{landmine.word}` landmine placed {td} ago by <@{placed_by.user_id}>. "
                        f"It exploded, taking away **{explosion_value} points** from your account.\n\n"
                        f"<@{placed_by.user_id}> message:\n"
                        f"{message_text}",
                        delete_on_invoke_removed=False)
                else:
                    await ctx.reply(
                        f"💥 You stepped on a `{landmine.word}` landmine placed {td} ago by <@{placed_by.user_id}>. "
                        f"It exploded, taking away **{explosion_value} points** from your account.\n\n",
                        delete_on_invoke_removed=False)

            if landmine or added_points:
                await db_target.save()
        finally:
            await self.concurrency.release(message)

    @commands.group(aliases=["landmines", "event2021", "lm"], name="landmine", case_insensitive=True)
    async def event(self, ctx: MyContext):
        """
        This command group contains all commends related to the 2021 "Landmines" event on the DuckHunt server.

        Go see Warlord in the shop.
        """
        if not ctx.invoked_subcommand:
            await ctx.send_help(ctx.command)

    @event.command()
    async def me(self, ctx: MyContext, target: discord.Member = None):
        """
        View your event statistics.
        """
        if target is None:
            target = ctx.author

        if not await self.user_can_play(target):
            await ctx.reply("They can't play the game :(")

        await self.is_in_command_channel(ctx)

        db_target = await models.get_user_eventdata(target)

        embed = discord.Embed(
            title=f"{target.name} event statistics",
            colour=discord.Color.green()
        )
        embed.description = "The most important currency in the game are the points, which are used in the shop to buy " \
                            "stuff. The available points show how many ponts you have and how many you acquired in " \
                            "total.\n" \
                            "You can get points by sending (long) messages. Some shop items may help you get more. " \
                            "Be careful not to spam, server rules **still apply** during the event. " \
                            "At the end of the game, the player having the greater amount of points will win."

        embed.add_field(name="Available", value=f"{db_target.points_current} points",
                        inline=False)

        embed.add_field(name="Messages sent", value=f"{db_target.messages_sent} ({db_target.words_sent} words)",
                        inline=False)

        if db_target.points_won:
            embed.add_field(name="Points won by landmines", value=f"{db_target.points_won} points",
                            inline=True)

        if db_target.points_recovered:
            embed.add_field(name="Points recovered by defusing landmines", value=f"{db_target.points_recovered} points",
                            inline=True)

        if db_target.points_acquired:
            embed.add_field(name="Points acquired by talking", value=f"{db_target.points_acquired} points",
                            inline=True)

        if db_target.points_exploded:
            embed.add_field(name="Points exploded by stepping on mines", value=f"{db_target.points_exploded} points",
                            inline=True)

        if db_target.points_spent:
            embed.add_field(name="Points spent in the shop", value=f"{db_target.points_spent} points",
                            inline=True)

        embed.set_footer(text="For more information, run the `dh!tag landmines` command.")
        embed.set_author(name=str(target), icon_url=str(target.avatar_url_as(format="jpg", size=256)))

        await ctx.reply(embed=embed)

    @event.group(aliases=["s", "buy", "use"], case_insensitive=True)
    async def shop(self, ctx: MyContext):
        """
        Buy useful supplies from the Warlord shop.
        """
        await self.is_in_command_channel(ctx, allow_dm=True)

        if not ctx.invoked_subcommand:
            await ctx.send_help(ctx.command)

    @shop.command(aliases=["l", "lm", "mine", "landmines"])
    async def landmine(self, ctx: MyContext, value: int, word: str, *, message_text: str = ""):
        """
        [THIS COMMAND WORKS IN DMs]
        Buy a landmine that will trigger on a specific word.

        A landmine has a value, at least greater than 2, that will be used to determine it's price and the damage done
        to the person that steps on it.
        The word must be at least 2 characters long, and must only contain letters. The steps are case-insensitive.
        The longer it is, the higher the power. An exploding landmine gives you the point damage, and half it's value
        back.
        """
        await self.is_in_command_channel(ctx, allow_dm=True)
        if ctx.guild:
            await ctx.message.delete()

        if value < 50:
            await ctx.author.send("❌ A landmine must have a value higher than 50.")
            return

        if len(message_text) > 1500:
            await ctx.author.send("❌ The message left on the landmine must be less than 1500 characters.")
            return

        word = models.get_valid_words(word)
        if len(word) != 1:
            await ctx.author.send("❌ The word must only contain letters.")
            return
        else:
            word = word[0]

        try:
            await self.concurrency.acquire(ctx.message)
            db_user = await models.get_user_eventdata(ctx.author)

            if db_user.points_current < value:
                await ctx.author.send(f"❌ You don't have {value} points, you can't buy a landmine as powerful as this.")
                return

            landmine = models.Event2021Landmines(
                placed_by=db_user,
                word=word,
                value=value,
                message=message_text,
            )
            db_user.points_current -= value
            db_user.points_spent += value

            await db_user.save()
            await landmine.save()
            await ctx.author.send(
                f"💣️ You placed a landmine on `{word}` that can give you at most `{landmine.base_value()}` points.")
        finally:
            await self.concurrency.release(ctx.message)

    @shop.command(aliases=["d", "defuse", "defuse_kits"])
    async def defuse_kit(self, ctx: MyContext, *, words: str):
        """
        Buy a defuse kit. You can use it on a sentence. If it's used, you collect the landmine value, minus the price
        of the defuse kit (30 points). If you don't use it, you'll just have to pay a restocking fee of 15 points.

        You need at least 30 points to use one.
        """
        await self.is_in_command_channel(ctx)
        words_list = models.get_valid_words(words)

        if len(words_list) < 1:
            await ctx.reply(f"❌ Please give (as much) valid words as you want to the defuse kit.")
            return

        landmine = await models.get_landmine(words)

        try:
            await self.concurrency.acquire(ctx.message)
            db_user = await models.get_user_eventdata(ctx.author)

            if db_user.points_current < 30:
                await ctx.reply(f"❌ You don't have 30 points, so you can't buy a defuse kit.")
                return

            db_user.defuse_kits_bought += 1

            if landmine:
                landmine.stopped_by = db_user
                landmine.disarmed = True
                landmine.stopped_at = datetime.datetime.utcnow()

                money_recovered = landmine.value
                db_user.points_current -= 30
                db_user.points_spent += 30
                db_user.points_recovered += money_recovered
                db_user.points_current += money_recovered

                got_points = money_recovered - 30

                if got_points > 0:
                    await ctx.reply(f"💰️ You used the defuse kit on `{landmine.word}`, and defused "
                                    f"<@{landmine.placed_by_id}> landmine, that has a `{landmine.value}` points value."
                                    f"You got {got_points} points, congratulations.",
                                    delete_on_invoke_removed=False)
                else:
                    await ctx.reply(f"💸️ You used the defuse kit on `{landmine.word}`, and defused "
                                    f"<@{landmine.placed_by_id}> landmine, that has a `{landmine.value}` points value."
                                    f"You've lost {-got_points} points, because the value of the landmine was lower "
                                    f"than the defuse kit price. Sorry!",
                                    delete_on_invoke_removed=False)

                await landmine.save()
            else:
                db_user.points_current -= 15
                db_user.points_spent += 15

                await ctx.reply(f"♻️️ You didn't use the defuse kit, and sold it back to the shop. "
                                f"You are sure that there isn't any mine on any of those words: `" +
                                ', '.join(words_list) +
                                '`.',
                                delete_on_invoke_removed=False)

            await db_user.save()
        finally:
            await self.concurrency.release(ctx.message)

    @tasks.loop(minutes=1)
    async def scoreboard_loop(self):
        scoreboard_channel = self.bot.get_channel(self.config()["scoreboard_channel_id"])
        if not scoreboard_channel or not isinstance(scoreboard_channel, discord.TextChannel):
            self.bot.logger.warning("The status channel for the landmines event is misconfigured.")
            return

        self.bot.logger.debug("Updating scoreboard stats", guild=scoreboard_channel.guild, channel=scoreboard_channel)
        await purge_channel_messages(scoreboard_channel)

        embed = discord.Embed(colour=discord.Colour.dark_green(),
                              title=f"WarTrackr")

        players_count = await models.Event2021UserData.all().count()
        total_mines_count = await models.Event2021Landmines.all().count()
        current_mines_count = await models.Event2021Landmines.all().filter(stopped_at__isnull=True).count()
        biggest_mine = await models.Event2021Landmines.all().filter(stopped_at__isnull=True).order_by('-value').first()

        negatives_count = await models.Event2021UserData \
            .filter(points_current__lte=0) \
            .count()

        embed.add_field(name="Players tracked", value=str(players_count))
        embed.add_field(name="Mines count", value=f"{current_mines_count} mines placed, {total_mines_count} created")
        if biggest_mine:
            embed.add_field(name="Biggest active mine",
                            value=f"Valued at `{biggest_mine.value} ({len(biggest_mine.word)} letters)`, placed by <@{biggest_mine.placed_by_id}>",
                            inline=False)
        embed.add_field(name="Players in the negative", value=str(negatives_count))

        await scoreboard_channel.send(embed=embed)

        self.bot.logger.debug("Updating scoreboard message", guild=scoreboard_channel.guild, channel=scoreboard_channel)

        embed = discord.Embed(colour=discord.Colour.blurple(),
                              title=f"Event scoreboard")

        top_players = await models.Event2021UserData.all().order_by('-points_current').limit(10)

        for i, top_player in enumerate(top_players):
            embed.add_field(name=f"{top_player.points_current} points", value=f"<@{top_player.user_id}>", inline=i > 2)

        await scoreboard_channel.send(embed=embed)

    @scoreboard_loop.before_loop
    async def before(self):
        await self.bot.wait_until_ready()
        await asyncio.sleep(5)
        await self.bot.wait_until_ready()

    @scoreboard_loop.error
    async def scoreboard_error(self, exception):
        self.bot.logger.exception(f"Error in scoreboard loop: {exception}")


setup = Event2021.setup
