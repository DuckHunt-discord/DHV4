import discord
from discord.ext import commands


class NotInServer(commands.CheckFailure):
    """Exception raised when a command is not ran in the specified server."""

    def __init__(self, must_be_in_guild_id):
        self.must_be_in_guild_id = must_be_in_guild_id


def is_in_server(must_be_in_guild_id):
    def predicate(ctx):
        if not ctx.guild:
            raise commands.NoPrivateMessage()
        elif ctx.guild.id != must_be_in_guild_id:
            raise NotInServer(must_be_in_guild_id=must_be_in_guild_id)
        return True

        # a function that takes ctx as it's only arg, that returns a truethy or falsey value, or raises an exception

    return commands.check(predicate)


def _has_discord_permission(ctx, permission_name):
    permissions: discord.Permissions = ctx.author_permissions()
    return getattr(permissions, permission_name)


def has_permission(permission):
    parsed_permission = permission.lower().split(".")

    if parsed_permission[0] == "discord":
        # Special permissions first
        permission_name = parsed_permission[1]

        def predicate(ctx):
            if _has_discord_permission(ctx, permission_name):
                return True
            else:
                raise commands.MissingPermissions([getattr(discord.Permissions, permission_name)])
    else:
        def predicate(ctx):
            return False

    return commands.check(predicate)

