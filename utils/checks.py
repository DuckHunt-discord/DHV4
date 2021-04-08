from discord.ext import commands

from utils.ctx_class import MyContext
from utils.models import get_from_db


class NotInServer(commands.CheckFailure):
    """Exception raised when a command is not ran in the specified server."""

    def __init__(self, must_be_in_guild_id):
        self.must_be_in_guild_id = must_be_in_guild_id


class BotIgnore(commands.CheckFailure):
    """Exception raised when a member is ignored by the bot"""


class AccessTooLow(commands.CheckFailure):
    """Exception raised when the access level of a Member is too low."""

    def __init__(self, current_access, required_access):
        self.current_access = current_access
        self.required_access = required_access


def is_in_server(must_be_in_guild_id):
    def predicate(ctx):
        if not ctx.guild:
            raise commands.NoPrivateMessage()
        elif ctx.guild.id != must_be_in_guild_id:
            raise NotInServer(must_be_in_guild_id=must_be_in_guild_id)
        return True

    # noinspection PyTypeChecker
    return commands.check(predicate)


def needs_access_level(required_access):
    async def predicate(ctx: MyContext):

        if not ctx.guild:
            raise commands.NoPrivateMessage()
        else:
            db_user = await get_from_db(ctx.author)

            access = db_user.get_access_level()
            if access >= required_access:
                return True
            else:
                raise AccessTooLow(current_access=access, required_access=required_access)

    # noinspection PyTypeChecker
    return commands.check(predicate)
