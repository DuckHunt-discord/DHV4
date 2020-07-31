"""
Commands to change settings in a channel/server

These commands act where they are typed!
"""
from typing import Optional

from discord.ext import commands
from discord.utils import escape_markdown, escape_mentions

from utils import checks
from utils.cog_class import Cog
from utils.ctx_class import MyContext
from utils.interaction import create_and_save_webhook
from utils.models import get_from_db


class SettingsCommands(Cog):
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
        In Québec, you could use fr_QC.
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
            await ctx.send(f"If you wish to go back to the default, english language, use `{ctx.prefix}{ctx.command.qualified_name} en`")
        else:
            await ctx.send(_("There is no specific language set for this guild."))

    @settings.command()
    async def use_webhooks(self, ctx: MyContext, value: Optional[bool] = None):
        """
        Specify wether the bot should use webhooks to communicate in this channel.

        Webhooks allow for custom avatars and usernames. However, there is a Discord limit of 10 webhooks per channel.
        """
        db_channel = await get_from_db(ctx.channel)
        if value:
            db_channel.use_webhooks = value
        await db_channel.save()

        _ = await ctx.get_translate_function()
        if db_channel.use_webhooks:
            await ctx.send(_("Webhooks are used in this channel."))
        else:
            await ctx.send(_("Webhooks are not used in this channel."))

    @settings.command()
    async def add_webhook(self, ctx: MyContext):
        """
        Add a new webhook to the channel, to get better rate limits handling. Remember the 10 webhooks/channel limit.
        """
        _ = await ctx.get_translate_function()

        db_channel = await get_from_db(ctx.channel)

        if not db_channel.use_webhooks:
            await ctx.send(_("Webhooks are not used in this channel. Please enable them first. You can use `{command}` to do it.",
                             command=f"{ctx.prefix}settings use_webhooks True"))
            return

        webhooks_count = len(db_channel.webhook_urls)

        webhook = await create_and_save_webhook(ctx.bot, ctx.channel, force=True)
        if webhook:
            await ctx.send(_("Your webhook was created. The bot now uses {n} webhook(s) to spawn ducks.", n=webhooks_count + 1))
        else:
            await ctx.send(_("I couldn't create a webhook. Double-check my permissions and try again."))


setup = SettingsCommands.setup
