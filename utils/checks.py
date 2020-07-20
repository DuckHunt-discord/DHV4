from discord.ext import commands
from typing import List

from utils.models import get_ctx_permissions
from utils.permissions import has_permission as permissions_has_permissions
from utils.permissions import is_ignored


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

    return commands.check(predicate)


def has_any_permission(permissions: List[str], negate=False, required=1):
    async def predictate(ctx):
        user_permissions = await get_ctx_permissions(ctx)
        if await is_ignored(ctx, permissions=user_permissions):
            raise BotIgnore()

        in_error = []
        ok = []

        for permission in permissions:
            permissions_value = await permissions_has_permissions(ctx, permission, negate=negate, permissions=user_permissions)
            if permissions_value:
                ok.append(permission)
            else:
                in_error.append(permission)

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
        user_permissions = await get_ctx_permissions(ctx)

        if await is_ignored(ctx, permissions=user_permissions):
            raise BotIgnore()

        ret = await permissions_has_permissions(ctx, permission, negate=negate)
        if ret and negate:
            raise HavingPermission(permission)
        elif not ret and not negate:
            raise MissingPermission(permission)
        else:
            return True

    return commands.check(predictate)
