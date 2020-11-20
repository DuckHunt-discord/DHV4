from discord.ext import commands


class NotInServer(commands.CheckFailure):
    """Exception raised when a command is not ran in the specified server."""

    def __init__(self, must_be_in_guild_id):
        self.must_be_in_guild_id = must_be_in_guild_id


class BotIgnore(commands.CheckFailure):
    """Exception raised when a member is ignored by the bot"""


def is_in_server(must_be_in_guild_id):
    def predicate(ctx):
        if not ctx.guild:
            raise commands.NoPrivateMessage()
        elif ctx.guild.id != must_be_in_guild_id:
            raise NotInServer(must_be_in_guild_id=must_be_in_guild_id)
        return True

    return commands.check(predicate)

