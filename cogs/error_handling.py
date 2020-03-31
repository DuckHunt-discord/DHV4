import traceback
import sys
from discord.ext import commands
import discord

from utils import checks
from utils.cog_class import Cog
from utils.ctx_class import MyContext


class CommandErrorHandler(Cog):
    @commands.Cog.listener()
    async def on_command_error(self, ctx: MyContext, exception: Exception) -> None:

        # This prevents any commands with local handlers being handled here in on_command_error.
        if hasattr(ctx.command, 'on_error'):
            return

        ignored = (commands.CommandNotFound, )

        # Allows us to check for original exceptions raised and sent to CommandInvokeError.
        # If nothing is found. We keep the exception passed to on_command_error.

        # Anything in ignored will return and prevent anything happening.
        if isinstance(exception, ignored):
            return

        DELETE_ERROR_MESSAGE_AFTER = 60
        command_invoke_help = f"{ctx.prefix}{ctx.command.qualified_name} {ctx.command.signature}"

        ctx.logger.debug(f"Error during processing: {exception} ({repr(exception)})")

        # https://discordpy.readthedocs.io/en/latest/ext/commands/api.html#discord.ext.commands.CommandError
        if isinstance(exception, commands.CommandError):
            if isinstance(exception, commands.ConversionError):
                original = exception.original
                message = f"❌ There was an error converting one of your arguments with {exception.converter}. The correct syntax would be `{command_invoke_help}`. "  \
                          f"The converter returned the following error: {original}"
            elif isinstance(exception, commands.UserInputError):
                if isinstance(exception, commands.errors.MissingRequiredArgument):
                    message = f"❌ This command is missing an argument. The correct syntax would be `{command_invoke_help}`."
                elif isinstance(exception, commands.errors.ArgumentParsingError):
                    if isinstance(exception, commands.UnexpectedQuoteError):
                        message = f"❌ Too many quotes were provided in your message: don't forget to escape your quotes like this `\\{exception.quote}`. " \
                                  f"The correct syntax for the command is `{command_invoke_help}`."
                    elif isinstance(exception, commands.InvalidEndOfQuotedStringError):
                        message = f"❌ A space was expected after a closing quote, but I found {exception.char}. " \
                                  f"Please check that you are using the correct syntax: `{command_invoke_help}`."
                    elif isinstance(exception, commands.ExpectedClosingQuoteError):
                        message = f"❌ A closing quote was expected, but wasn't found. " \
                                  f"Don't forget to close your quotes with `{exception.close_quote}` at the end of your argument. " \
                                  f"Please check that you are using the correct syntax: `{command_invoke_help}`."
                    elif isinstance(exception, commands.TooManyArguments):
                        message = f"❌ Too many arguments were passed in this command. " \
                                  f"Please check that you are using the correct syntax: `{command_invoke_help}`."
                    else:  # Should not trigger, just in case some more errors are added.
                        message = f"❌ The way you are invoking this command is confusing me. The correct syntax would be `{command_invoke_help}`."
                elif isinstance(exception, commands.BadArgument):
                    message = f"❌ An argument passed was incorrect. `{exception.message}`" \
                              f"Please check that you are using the correct syntax: `{command_invoke_help}`."
                elif isinstance(exception, commands.BadUnionArgument):
                    message = f"❌ {str(exception)}. The correct syntax would be `{command_invoke_help}`."
                else:
                    message = f"❌ {str(exception)} ({type(exception).__name__})"
                    ctx.logger.error("".join(traceback.format_exception(type(exception), exception, exception.__traceback__)))

            elif isinstance(exception, commands.CheckFailure):
                if isinstance(exception, commands.PrivateMessageOnly):
                    message = f"❌ This command can only be used in a private message."
                elif isinstance(exception, commands.NoPrivateMessage):
                    message = f"❌ This command can not be used in a private message."
                elif isinstance(exception, commands.CheckAnyFailure):
                    message = f"❌ Multiple errors were encountered when running your command : {exception.errors}"
                elif isinstance(exception, commands.NotOwner):
                    message = f"❌ You need to be the owner of the bot to run that."
                elif isinstance(exception, commands.MissingPermissions):
                    message = f"❌ {str(exception)}"
                elif isinstance(exception, commands.BotMissingPermissions):
                    message = f"❌ {str(exception)}"
                elif isinstance(exception, commands.MissingRole):
                    message = f"❌ {str(exception)}"
                elif isinstance(exception, commands.BotMissingRole):
                    message = f"❌ {str(exception)}"
                elif isinstance(exception, commands.MissingAnyRole):
                    message = f"❌ {str(exception)}"
                elif isinstance(exception, commands.BotMissingAnyRole):
                    message = f"❌ {str(exception)}"
                elif isinstance(exception, commands.NSFWChannelRequired):
                    message = f"❌ You need to be in a NSFW channel to run that."

                # Custom checks errors
                elif isinstance(exception, checks.NotInServer):
                    correct_guild = self.bot.get_guild(exception.must_be_in_guild_id)
                    if correct_guild:
                        message = f"❌ You need to be in the {correct_guild.name} server (`{exception.must_be_in_guild_id}`)."
                    else:
                        message = f"❌ You need to be in a server with ID {exception.must_be_in_guild_id}."
                else:
                    message = f"❌ Check error running this command : {str(exception)} ({type(exception).__name__})"
                    ctx.logger.error("".join(traceback.format_exception(type(exception), exception, exception.__traceback__)))
            elif isinstance(exception, commands.CommandNotFound):
                # This should be disabled.
                message = f"❌ The provided command was not found."
            elif isinstance(exception, commands.errors.DisabledCommand):
                message = f"❌ {ctx.command} has been disabled."
            elif isinstance(exception, commands.CommandInvokeError):
                message = f"❌ There was an error running the specified command. Contact the bot admins."
                ctx.logger.error("".join(traceback.format_exception(type(exception), exception, exception.__traceback__)))
            elif isinstance(exception, commands.errors.CommandOnCooldown):
                if self.bot.is_owner(ctx.author):
                    await ctx.reinvoke()
                    return
                else:
                    message = "❌ This command is overused. Please try again in {seconds}s.".format(
                        seconds=round(exception.retry_after, 1))
            elif isinstance(exception, commands.errors.MaxConcurrencyReached):
                message = f"❌ {str(exception)}" # The message from the lib is great.
            else:
                message = f"❌ {str(exception)} ({type(exception).__name__})"
                ctx.logger.error("".join(traceback.format_exception(type(exception), exception, exception.__traceback__)))
        else:
            message = f"❌ This should not have happened. A command raised an error that does not comes from CommandError. Please inform the owner."
            ctx.logger.error("".join(traceback.format_exception(type(exception), exception, exception.__traceback__)))

        await ctx.send(message, delete_after=DELETE_ERROR_MESSAGE_AFTER)


setup = CommandErrorHandler.setup