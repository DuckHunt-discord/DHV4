"""
Some example of commands that can be used to interact with the database.
"""
from typing import Optional

from discord.ext import commands
from discord.utils import escape_markdown, escape_mentions

from utils import checks
from utils.cog_class import Cog
from utils.ctx_class import MyContext
from utils.interaction import create_and_save_webhook
from utils.models import get_from_db


class DatabaseCommands(Cog):
    @commands.command()
    async def how_many(self, ctx: MyContext):
        """
        Say hi with a customisable hello message. This is used to demonstrate cogs config usage
        """
        _ = await ctx.get_translate_function()
        db_user = await get_from_db(ctx.author, as_user=True)
        db_user.times_ran_example_command += 1
        await db_user.save()
        await ctx.send(_("You ran that command {times_ran_example_command} times already!",
                         times_ran_example_command=db_user.times_ran_example_command
                         ))

setup = DatabaseCommands.setup
