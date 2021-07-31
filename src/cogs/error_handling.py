import datetime
import traceback

import babel
import discord
import tortoise
from discord.ext import menus
from babel import dates
from discord.ext import commands

from cogs.shopping_commands import NotEnoughExperience
from utils import checks
from utils.cog_class import Cog
from utils.ctx_class import MyContext
from utils.interaction import escape_everything
from utils.models import get_from_db

DELETE_ERROR_MESSAGE_AFTER = 60


class CommandErrorHandler(Cog):
    @commands.Cog.listener()
    async def on_command_error(self, ctx: MyContext, exception: Exception) -> None:
        _ = await ctx.get_translate_function()

        # This prevents any commands with local handlers being handled here in on_command_error.
        if hasattr(ctx.command, 'on_error'):
            return

        ignored = (commands.CommandNotFound,)

        # Allows us to check for original exceptions raised and sent to CommandInvokeError.
        # If nothing is found. We keep the exception passed to on_command_error.

        # Anything in ignored will return and prevent anything happening.
        if isinstance(exception, ignored):
            return

        command_invoke_help = f"{ctx.prefix}{ctx.command.qualified_name} {ctx.command.signature}"

        ctx.logger.debug(f"Error during processing: {exception} ({repr(exception)})")

        if hasattr(exception, "original"):
            exception = exception.original

        # https://discordpy.readthedocs.io/en/latest/ext/commands/api.html#discord.ext.commands.CommandError
        if isinstance(exception, commands.CommandError):
            if isinstance(exception, commands.ConversionError):
                original = exception.original
                message = _("There was an error converting one of your arguments with {exception.converter}. The "
                            "correct syntax would be `{command_invoke_help}`. The converter returned the following "
                            "error: {original}",
                            command_invoke_help=command_invoke_help,
                            original=escape_everything(str(original)))
            elif isinstance(exception, commands.UserInputError):
                if isinstance(exception, commands.errors.MissingRequiredArgument):
                    message = _(
                        "This command is missing an argument. The correct syntax would be `{command_invoke_help}`.",
                        command_invoke_help=command_invoke_help)
                elif isinstance(exception, commands.errors.ArgumentParsingError):
                    if isinstance(exception, commands.UnexpectedQuoteError):
                        message = _("Too many quotes were provided in your message: don't forget to escape your "
                                    "quotes like this `\\{exception.quote}`. The correct syntax for the command is "
                                    "`{command_invoke_help}`.",
                                    command_invoke_help=command_invoke_help,
                                    exception=exception)
                    elif isinstance(exception, commands.InvalidEndOfQuotedStringError):
                        message = _("A space was expected after a closing quote, but I found {exception.char}. "
                                    "Please check that you are using the correct syntax: `{command_invoke_help}`.",
                                    command_invoke_help=command_invoke_help,
                                    exception=exception)
                    elif isinstance(exception, commands.ExpectedClosingQuoteError):
                        message = _("A closing quote was expected, but wasn't found. Don't forget to close your "
                                    "quotes with `{exception.close_quote}` at the end of your argument. Please check "
                                    "that you are using the correct syntax: `{command_invoke_help}`.",
                                    command_invoke_help=command_invoke_help,
                                    exception=exception)
                    elif isinstance(exception, commands.TooManyArguments):
                        message = _("Too many arguments were passed in this command. "
                                    "Please check that you are using the correct syntax: `{command_invoke_help}`.",
                                    command_invoke_help=command_invoke_help)
                    else:  # Should not trigger, just in case some more errors are added.
                        message = _("The way you are invoking this command is confusing me. The correct syntax would "
                                    "be `{command_invoke_help}`.",
                                    command_invoke_help=command_invoke_help)

                elif isinstance(exception, commands.BadArgument):
                    message = _("An argument passed was incorrect. `{exception}`. "
                                "Please check that you are using the correct syntax: `{command_invoke_help}`.",
                                command_invoke_help=command_invoke_help,
                                exception=exception)
                elif isinstance(exception, commands.BadUnionArgument):
                    message = _(
                        "{exception} Please check that you are using the correct syntax: `{command_invoke_help}`.",
                        command_invoke_help=command_invoke_help,
                        exception=str(exception))
                else:
                    message = f"{str(exception)} ({type(exception).__name__})"
                    ctx.logger.error(
                        "".join(traceback.format_exception(type(exception), exception, exception.__traceback__)))

            elif isinstance(exception, commands.CheckFailure):
                if isinstance(exception, commands.PrivateMessageOnly):
                    message = _("This command can only be used in a private message.")
                elif isinstance(exception, commands.NoPrivateMessage):
                    message = _("This command cannot be used in a private message.")
                elif isinstance(exception, commands.CheckAnyFailure):
                    message = _("Multiple errors were encountered when running your command: {exception.errors}",
                                exception=exception)
                elif isinstance(exception, commands.NotOwner):
                    message = _("You need to be the owner of the bot to run that.")
                # We could edit and change the message here, but the lib messages are fine and specify exactly what
                # permissions are missing
                elif isinstance(exception, commands.MissingPermissions):
                    message = f"{str(exception)}"
                elif isinstance(exception, commands.BotMissingPermissions):
                    message = f"{str(exception)}"
                elif isinstance(exception, commands.MissingRole):
                    message = f"{str(exception)}"
                elif isinstance(exception, commands.BotMissingRole):
                    message = f"{str(exception)}"
                elif isinstance(exception, commands.MissingAnyRole):
                    message = f"{str(exception)}"
                elif isinstance(exception, commands.BotMissingAnyRole):
                    message = f"{str(exception)}"
                elif isinstance(exception, commands.NSFWChannelRequired):
                    message = _("You need to be in a NSFW channel to run that.")

                # Custom checks errors
                elif isinstance(exception, checks.NotInServer):
                    correct_guild = self.bot.get_guild(exception.must_be_in_guild_id)
                    if correct_guild:
                        message = _(
                            "You need to be in the {correct_guild.name} server (`{exception.must_be_in_guild_id}`).",
                            correct_guild=correct_guild,
                            exception=exception)
                    else:
                        message = _("You need to be in a server with ID {exception.must_be_in_guild_id}.",
                                    exception=exception)
                elif isinstance(exception, checks.NotInChannel):
                    correct_channel = self.bot.get_channel(exception.must_be_in_channel_id)
                    if correct_channel:
                        message = _("You need to be in the {correct_channel.name} channel (`{exception.must_be_in_channel_id}`).",
                                    correct_channel=correct_channel,
                                    exception=exception)
                    else:
                        message = _("You need to be in a channel with ID {exception.must_be_in_channel_id}.",
                                    exception=exception)

                elif type(exception).__name__ == NotEnoughExperience.__name__:
                    message = _("You don't have enough experience to enjoy this item. You'd need at least {exception.needed} exp, but you only have {exception.having}.",
                                exception=exception)

                elif isinstance(exception, checks.AccessTooLow):
                    message = _("Your access level is too low : you have an access level of {exception.current_access.name}, and you need at least {exception.required_access.name}.",
                                exception=exception)

                elif isinstance(exception, checks.ChannelDisabled):
                    db_guild = await get_from_db(ctx.guild)

                    if db_guild.channel_disabled_message:
                        message = _(
                            "The game isn't running on this channel. "
                            "Admins can disable this message by running `dh!settings channel_disabled_message False`, "
                            "or can enable the channel with `dh!settings enabled True`.",
                            exception=exception)
                    else:
                        return

                elif isinstance(exception, checks.LandminesDisabled):
                    db_guild = await get_from_db(ctx.guild)

                    if db_guild.channel_disabled_message:
                        message = _(
                            "Landmines commands cannot be ran on this channel. "
                            "Admins can disable this message by running `dh!settings channel_disabled_message False`, "
                            "or can enable the channel with `dh!settings landmines_commands_enabled True`.",
                            exception=exception)
                    else:
                        return

                elif isinstance(exception, checks.BotIgnore):
                    return
                else:
                    message = _("Check error running this command: {err_data}", err_data=f"{str(exception)} ({type(exception).__name__})")
                    ctx.logger.error(
                        "".join(traceback.format_exception(type(exception), exception, exception.__traceback__)))
            elif isinstance(exception, commands.CommandNotFound):
                # This should be disabled.
                message = _("The provided command was not found.")
            elif isinstance(exception, commands.errors.DisabledCommand):
                message = _("That command has been disabled.")
            elif isinstance(exception, commands.CommandInvokeError):
                message = _("There was an error running the specified command. Contact the bot admins.")
                ctx.logger.error(
                    "".join(traceback.format_exception(type(exception), exception, exception.__traceback__)))
            elif isinstance(exception, commands.errors.CommandOnCooldown):
                if await self.bot.is_owner(ctx.author):
                    await ctx.reinvoke()
                    return
                else:
                    delta = datetime.timedelta(seconds=min(round(exception.retry_after, 1), 1))
                    # NOTE: This message uses a formatted, direction date in some_time. Formatted, it'll give
                    # something like:
                    # "This command is overused. Please try again *in 4 seconds*"
                    message = _("This command is overused. Please try again {some_time}.",
                                some_time=dates.format_timedelta(delta, add_direction=True, locale=(await ctx.get_language_code())))
            elif isinstance(exception, commands.errors.MaxConcurrencyReached):
                message = f"{str(exception)}"  # The message from the lib is great.
            else:
                message = f"{str(exception)} ({type(exception).__name__})"
                ctx.logger.error(
                    "".join(traceback.format_exception(type(exception), exception, exception.__traceback__)))
        else:
            message = _(
                "This should not have happened. A command raised an error that does not comes from CommandError. "
                "Please inform the owner.")
            ctx.logger.error("".join(traceback.format_exception(type(exception), exception, exception.__traceback__)))
            if isinstance(exception, tortoise.exceptions.OperationalError):
                message = _("You are above the limits of DuckHunt database. Try to reduce your expectations. Database message: `{exception}`",
                            exception=exception)
            elif isinstance(exception, babel.core.UnknownLocaleError):
                message = f"Unknown server language. Fix with `{ctx.prefix}set lang en`"
            elif isinstance(exception, discord.Forbidden):
                message = _("Missing permissions, please check I can embed links here. `{exception}`",
                            exception=exception)
            elif isinstance(exception, menus.CannotAddReactions):
                message = _("Missing permissions, please check I can add reactions here.")
            else:
                message = _("This should not have happened. A command raised an error that does not come from CommandError, and isn't handled by our error handler. "
                            "Please inform the owner.") + "\n```py\n" + "".join(traceback.format_exception(type(exception), exception, exception.__traceback__)) + "\n```"
                ctx.logger.error("".join(traceback.format_exception(type(exception), exception, exception.__traceback__)))

        if message:
            await ctx.send("❌ " + message, delete_after=DELETE_ERROR_MESSAGE_AFTER)


setup = CommandErrorHandler.setup
