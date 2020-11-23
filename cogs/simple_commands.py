import datetime
import time

from babel.dates import format_timedelta
from discord.ext import commands

from utils.cog_class import Cog
from utils.ctx_class import MyContext

SECOND = 1
MINUTE = 60 * SECOND
HOUR = 60 * MINUTE
DAY = 24 * HOUR

class SimpleCommands(Cog):
    @commands.command()
    async def ping(self, ctx: MyContext):
        """
        Check that the bot is online, give the latency between the bot and discord servers.
        """
        _ = await ctx.get_translate_function()

        t_1 = time.perf_counter()
        await ctx.trigger_typing()  # tell Discord that the bot is "typing", which is a very simple request
        t_2 = time.perf_counter()
        time_delta = round((t_2 - t_1) * 1000)  # calculate the time needed to trigger typing
        await ctx.send(_("Pong. — Time taken: {miliseconds}ms", miliseconds=time_delta))  # send a message telling the user the calculated ping time

    @commands.command()
    async def wiki(self, ctx: MyContext):
        """
        Returns the wiki URL
        """
        _ = await ctx.get_translate_function()

        wiki_url = self.config()["wiki_url"]

        await ctx.send(_(wiki_url))

    @commands.command()
    async def invite(self, ctx: MyContext):
        """
        Get the URL to invite the bot
        """

        await ctx.send(f"<https://discord.com/oauth2/authorize?client_id={self.bot.user.id}&scope=bot&permissions=204856385>")


    @commands.command()
    async def freetime(self, ctx: MyContext):
        """
        Get the time when you'll get free magazines and your weapon back from the police
        """

        _ = await ctx.get_translate_function()
        language_code = await ctx.get_language_code()

        now = int(time.time())
        SECONDS_SPENT_TODAY = now % 86400
        SECONDS_LEFT_TODAY = 86400 - SECONDS_SPENT_TODAY
        time_delta = datetime.timedelta(seconds=SECONDS_LEFT_TODAY)

        formatted_delta = format_timedelta(time_delta, add_direction=True, locale=language_code)

        await ctx.send(_("You'll get back your weapon and magazines {formatted_delta}", formatted_delta=formatted_delta))

setup = SimpleCommands.setup
