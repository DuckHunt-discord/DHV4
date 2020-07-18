import discord
from discord.ext import commands
from typing import List

from utils.models import get_ctx_permissions


class NotInServer(commands.CheckFailure):
    """Exception raised when a command is not ran in the specified server."""

    def __init__(self, must_be_in_guild_id):
        self.must_be_in_guild_id = must_be_in_guild_id


class MissingPermissions(commands.CheckFailure):
    """Exception raised when a member don't have some specific, rich permission"""

    def __init__(self, permissions: List[str] = "", required: int = 1):
        self.permissions = permissions
        self.required = required


class HavingPermissions(commands.CheckFailure):
    """Exception raised when a member have some specific, rich permission"""

    def __init__(self, permissions: List[str] = "", required: int = 1):
        self.permissions = permissions
        self.required = required


class MissingPermission(commands.CheckFailure):
    """Exception raised when a member don't have a specific, rich permission"""

    def __init__(self, permission: str = ""):
        self.permission = permission


class HavingPermission(commands.CheckFailure):
    """Exception raised when a member does have a specific, rich permission, and shouldn't"""

    def __init__(self, permission: str = ""):
        self.permission = permission


class BotIgnore(commands.CheckFailure):
    """Exception raised when a member is ignored by the bot"""


def is_in_server(must_be_in_guild_id):
    def predicate(ctx):
        if not ctx.guild:
            raise commands.NoPrivateMessage()
        elif ctx.guild.id != must_be_in_guild_id:
            raise NotInServer(must_be_in_guild_id=must_be_in_guild_id)
        return True

        # a function that takes ctx as it's only arg, that returns a truethy or falsey value, or raises an exception

    return commands.check(predicate)


def is_not_ignored():
    return has_permission('', negate=True)


def _has_discord_permission(ctx, permission_name):
    permissions: discord.Permissions = ctx.author_permissions()

    return permissions.is_superset(discord.Permissions(**{permission_name: True}))


async def _has_permission(ctx, permission, negate=False, permissions=None):
    if permissions is None:
        permissions = await get_ctx_permissions(ctx)

    parsed_permission = permission.lower().split(".")

    if parsed_permission[0] == "discord":
        # Special permissions first
        permission_name = parsed_permission[1]
        if _has_discord_permission(ctx, permission_name):
            if negate:
                return HavingPermission(permission_name)
            else:
                return True
        else:
            if negate:
                return True
            else:
                raise MissingPermission(permission_name)
    else:

        permission_value = permissions.get(permission, False)
        if permissions["bot.administrator"]:
            if negate:
                return HavingPermission(permission)
            else:
                return True
        elif permissions["server.ignored"]:
            raise BotIgnore()
        elif permissions['bot.ignored']:
            raise BotIgnore()
        elif permission_value:
            if negate:
                raise HavingPermission(permission)
            else:
                return True
        else:
            if negate:
                return True
            else:
                raise MissingPermission(permission)


def has_any_permission(permissions: List[str], negate=False, required=1):
    async def predictate(ctx):
        user_permissions = await get_ctx_permissions(ctx)
        in_error = []
        ok = []

        for permission in permissions:
            try:
                await _has_permission(ctx, permission, negate=negate, permissions=user_permissions)
            except (HavingPermission, MissingPermission, commands.MissingPermissions):
                in_error.append(permission)
            except BotIgnore:
                raise
            else:
                ok.append(permission)

        if len(ok) >= required:
            return True
        else:
            if negate:
                raise HavingPermissions(in_error, required)
            else:
                raise MissingPermissions(in_error, required)

    return commands.check(predictate)


def server_admin_or_permission(permission: str):
    return has_any_permission(["discord.administrator", permission])


def has_permission(permission: str, negate=False):
    async def predictate(ctx):
        return await _has_permission(ctx, permission, negate=negate)

    return commands.check(predictate)
