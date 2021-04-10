"""
Some example of commands that can be used to interact with the database.
"""
from typing import Optional

from discord.ext import commands
from discord.utils import escape_markdown, escape_mentions

from utils.cog_class import Cog
from utils.ctx_class import MyContext
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

    @commands.group()
    async def settings(self, ctx: MyContext):
        """
        Commands to view and edit settings
        """
        if not ctx.invoked_subcommand:
            await ctx.send_help(ctx.command)

    @settings.command()
    async def prefix(self, ctx: MyContext, new_prefix: Optional[str] = None):
        """
        Change/view the server prefix.

        Note that some prefixes are global and can't be edited.
        """
        _ = await ctx.get_translate_function()
        db_guild = await get_from_db(ctx.guild)
        if new_prefix:
            db_guild.prefix = new_prefix
        await db_guild.save()
        if db_guild.prefix:
            await ctx.send(_("The server prefix is set to `{prefix}`.",
                             prefix=escape_mentions(escape_markdown(db_guild.prefix))
                             ))
        else:
            await ctx.send(_("There is no specific prefix set for this guild."))

    @settings.command()
    async def language(self, ctx: MyContext, language_code: Optional[str] = None):
        """
        Change/view the server language.

        Specify the server language as a 2/5 letters code. For example, if you live in France, you'd use fr or fr_FR.
        In Quebec, you could use fr_QC.
        """
        db_guild = await get_from_db(ctx.guild)
        if language_code:
            db_guild.language = language_code
        await db_guild.save()

        _ = await ctx.get_translate_function()
        if db_guild.language:
            await ctx.send(_("The server language is set to `{language}`.",
                             language=escape_mentions(escape_markdown(db_guild.language))
                             ))

            # Do not translate
            await ctx.send(
                f"If you wish to go back to the default, english language, use "
                f"`{ctx.prefix}{ctx.command.qualified_name} en`")
        else:
            await ctx.send(_("There is no specific language set for this guild."))


setup = DatabaseCommands.setup
