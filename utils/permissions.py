import discord

from utils.models import get_ctx_permissions

IGNORE_PERMS = ["server.ignored", "bot.ignored"]


def _has_discord_permission(ctx, permission_name):
    permissions: discord.Permissions = ctx.author_permissions()

    return permissions.is_superset(discord.Permissions(**{permission_name: True}))


async def is_ignored(ctx, permissions=None):
    if permissions is None:
        permissions = await get_ctx_permissions(ctx)

    for permission in IGNORE_PERMS:
        if await has_permission(ctx, permission, permissions=permissions, administrator=False):
            return True
    return False


def _recursive_permission_check(parsed_permission, permissions):
    permission = ".".join(parsed_permission)

    if permissions.get(permission, None):  # Special case for that specific permission, since there is no wildcard for it
        return True

    permission_len = len(parsed_permission)
    if permission_len <= 1:
        return False
    else:
        for depth in range(permission_len)[::-1]:
            permission_part = parsed_permission[:depth]
            permission = ".".join(permission_part) + ".*"
            if permission == ".*":
                permission = "*"
            value = permissions.get(permission, None)
            if value:
                return True
            elif value is False:
                return False


async def has_permission(ctx, permission, negate=False, administrator=True, permissions=None):
    if permissions is None:
        permissions = await get_ctx_permissions(ctx)

    parsed_permission = permission.lower().split(".")

    if parsed_permission[0] == "discord":
        # Special permissions first
        permission_name = parsed_permission[1]
        if _has_discord_permission(ctx, permission_name):
            return not negate
        else:
            return negate
    else:
        if permissions["bot.administrator"] and administrator:
            return not negate
        elif _recursive_permission_check(parsed_permission, permissions):
            return not negate
        else:
            return negate
