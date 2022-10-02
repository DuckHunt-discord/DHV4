from discord.ext import commands

from utils.ctx_class import MyContext
from utils.models import get_from_db, AccessLevel


class NotInServer(commands.CheckFailure):
    """Exception raised when a command is not ran in the specified server."""

    def __init__(self, must_be_in_guild_id):
        self.must_be_in_guild_id = must_be_in_guild_id


class NotInChannel(commands.CheckFailure):
    """Exception raised when a command is not ran in the specified channel."""

    def __init__(self, must_be_in_channel_id):
        self.must_be_in_channel_id = must_be_in_channel_id


class BotIgnore(commands.CheckFailure):
    """Exception raised when a member is ignored by the bot"""


class AccessTooLow(commands.CheckFailure):
    """Exception raised when the access level of a Member is too low."""

    def __init__(self, current_access, required_access):
        self.current_access = current_access
        self.required_access = required_access


class ChannelDisabled(commands.CheckFailure):
    """Exception raised when the channel wasn't enabled."""


class LandminesDisabled(commands.CheckFailure):
    """Exception raised when the channel wasn't enabled."""


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
            elif access >= AccessLevel.BANNED and required_access <= AccessLevel.ADMIN:
                if ctx.author_permissions().administrator:
                    return True  # Override permissions for administrators
                raise AccessTooLow(current_access=access, required_access=required_access)
            else:
                raise AccessTooLow(current_access=access, required_access=required_access)

    predicate.access = required_access

    # noinspection PyTypeChecker
    return commands.check(predicate)


def channel_enabled():
    async def predictate(ctx):
        if await ctx.is_channel_enabled():
            return True
        else:
            raise ChannelDisabled()

    # noinspection PyTypeChecker
    return commands.check(predictate)


def landmines_commands_enabled():
    async def predictate(ctx):
        if ctx.guild:
            db_channel = await get_from_db(ctx.channel)
            if db_channel.landmines_commands_enabled:
                return True
            else:
                raise LandminesDisabled()
        else:
            return True

    # noinspection PyTypeChecker
    return commands.check(predictate)

