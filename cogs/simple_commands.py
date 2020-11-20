import time

from discord.ext import commands

from utils import checks
from utils.cog_class import Cog
from utils.ctx_class import MyContext

from babel import dates

from utils.models import AccessLevel, get_from_db


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
        Say hi with a customisable hello message. This is used to demonstrate cogs config usage
        """
        _ = await ctx.get_translate_function()

        wiki_url = self.config()["wiki_url"]

        await ctx.send(_(wiki_url))

    @commands.command(aliases=['start', 'add_channel'])
    @checks.needs_access_level(AccessLevel.ADMIN)
    async def enable(self, ctx: MyContext):
        _ = await ctx.get_translate_function()

        db_channel = await get_from_db(ctx.channel)
        if not db_channel.enabled:
            db_channel.enabled = True
            await db_channel.save()

            await ctx.send(_("The game has been started on this channel."))
        else:
            await ctx.send(_("The game was already started on this channel. Wait a while for ducks to appear. Use `{ctx.prefix}disable` to stop the game.",
                             ctx=ctx))

    @commands.command(aliases=['stop', 'del_channel'])
    @checks.needs_access_level(AccessLevel.ADMIN)
    async def disable(self, ctx: MyContext):
        _ = await ctx.get_translate_function()

        db_channel = await get_from_db(ctx.channel)
        if db_channel.enabled:

            db_channel.enabled = True
            await db_channel.save()

            await ctx.send(_("The game has been stopped on this channel. The channel data is saved, and the game can be restarted at any time with `{ctx.prefix}enable`",
                             ctx=ctx))
        else:
            await ctx.send(_("The game was already stopped here. The game can be restarted at any time with `{ctx.prefix}enable`",
                             ctx=ctx))


setup = SimpleCommands.setup
