"""
Commands that relate to permissions viewing and setting
"""
import discord
from discord.ext import commands

from utils import permissions, checks
from utils.cog_class import Cog
from utils.ctx_class import MyContext
from utils.interaction import escape_everything
from utils.models import get_from_db, DiscordMember, DiscordChannel, DiscordUser, DiscordGuild
from utils.permissions import _recursive_permission_check


def get_sign(value):
    if value is True:
        return "+"
    elif value is False:
        return "-"
    else:
        return "="


class PermissionsCommands(Cog):
    @commands.group(aliases=["perms"])
    async def permissions(self, ctx: MyContext):
        """
        Commands to view and edit permissions
        """
        if not ctx.invoked_subcommand:
            await ctx.send_help(ctx.command)

    @permissions.group()
    async def view(self, ctx: MyContext):
        """
        Do you have that permission you'd so much like to have ?
        """
        if not ctx.invoked_subcommand:
            await ctx.send_help(ctx.command)

    @view.command(name="me")
    async def view_me(self, ctx: MyContext, permission: str, negate: bool = False, administrator: bool = True, show_none: bool = False):
        """
        Check a permission for yourself
        """
        _ = await ctx.get_translate_function()

        value = await permissions.has_permission(ctx, permission, negate=negate, administrator=administrator)
        if value:
            await ctx.send(_("😃 You have that permission."))
        else:
            await ctx.send(_("☹️ You don't have that permission."))

        if ctx.guild:
            message = [_("Details of permissions hierarchy"), "```diff"]
            parsed_permission = permission.split(".")

            default_permissions = ctx.bot.config['permissions']['default']

            value, by = _recursive_permission_check(parsed_permission, default_permissions)
            message.append(_("{sign} Default (from {sign}{by})", sign=get_sign(value), by=by))

            db_member: DiscordMember = await get_from_db(ctx.author)
            db_channel: DiscordChannel = await get_from_db(ctx.channel)
            db_user: DiscordUser = db_member.user
            db_guild: DiscordGuild = db_member.guild
            guild_permissions = db_guild.permissions

            for role in ctx.author.roles:
                role_permissions = guild_permissions.get(str(role.id), {})
                if len(role_permissions):
                    value, by = _recursive_permission_check(parsed_permission, role_permissions)
                    if value in [True, False] or show_none:

                        message.append(_("{sign} Guild role {role} (from {sign}{by})",
                                         sign=get_sign(value),
                                         role=escape_everything(role.name),
                                         by=by))

            channel_permissions = db_channel.permissions
            for role in ctx.author.roles:
                role_permissions = channel_permissions.get(str(role.id), {})
                if len(role_permissions):
                    value, by = _recursive_permission_check(parsed_permission, role_permissions)
                    if value in [True, False] or show_none:
                        message.append(_("{sign} Channel role {role} (from {sign}{by})",
                                         sign=get_sign(value),
                                         role=escape_everything(role.name),
                                         by=by))

            member_permissions = db_member.permissions
            value, by = _recursive_permission_check(parsed_permission, member_permissions)
            if value in [True, False] or show_none:
                message.append(_("{sign} Member (from {sign}{by})",
                                 sign=get_sign(value),
                                 by=by))

            fixed_permissions = ctx.bot.config['permissions']['fixed']
            value, by = _recursive_permission_check(parsed_permission, fixed_permissions)
            if value in [True, False] or show_none:
                message.append(_("{sign} Fixed (from {sign}{by})",
                                 sign=get_sign(value),
                                 by=by))

            user_permissions = db_user.permissions
            value, by = _recursive_permission_check(parsed_permission, user_permissions)
            if value in [True, False] or show_none:
                message.append(_("{sign} User (from {sign}{by})",
                                 sign=get_sign(value),
                                 by=by))

            message.append("```")

            await ctx.send("\n".join(message))

    @view.command(name="guild")
    @commands.cooldown(2, 30, commands.BucketType.guild)
    async def view_guild(self, ctx: MyContext):
        """
        Display all permissions set for this guild
        """
        _ = await ctx.get_translate_function()

        said_something = False
        guild = ctx.guild
        db_guild = await get_from_db(guild)
        permissions_by_role = db_guild.permissions

        for role_id, role_permissions in permissions_by_role.items():
            role = guild.get_role(int(role_id))
            if role and len(role_permissions):
                message = [_("**{role} permissions**", role=escape_everything(role.name)), "```diff"]

                for permission, value in role_permissions.items():
                    sign = "+" if value else "-"
                    message.append(f"{sign} {permission}")
                message.append("```")
                said_something = True
                await ctx.send("\n".join(message))

        if not said_something:
            await ctx.send(_("There are no specific permissions set in this guild."))

    @view.command(name="channel")
    @commands.cooldown(2, 30, commands.BucketType.guild)
    async def view_channel(self, ctx: MyContext, channel: discord.TextChannel = None):
        """
        Display all permissions set for this channel
        """
        _ = await ctx.get_translate_function()

        said_something = False
        guild = ctx.guild
        if not channel or channel.guild.id != guild.id:
            channel = ctx.channel

        db_channel = await get_from_db(channel)
        permissions_by_role = db_channel.permissions

        for role_id, role_permissions in permissions_by_role.items():
            role = guild.get_role(int(role_id))
            if role and len(role_permissions):
                message = [_("**{role} permissions**", role=escape_everything(role.name)), "```diff"]

                for permission, value in role_permissions.items():
                    sign = "+" if value else "-"
                    message.append(f"{sign} {permission}")
                message.append("```")
                said_something = True
                await ctx.send("\n".join(message))

        if not said_something:
            await ctx.send(_("There are no specific permissions set in this channel."))

    @view.command(name="member")
    @commands.cooldown(2, 30, commands.BucketType.guild)
    async def view_member(self, ctx: MyContext, member: discord.Member = None):
        """
        Display all permissions set for this channel
        """
        _ = await ctx.get_translate_function()

        if not member:
            member = ctx.author

        db_member = await get_from_db(member, as_user=False)
        permissions = db_member.permissions

        if len(permissions):
            message = [_("**{member.name}#{member.discriminator} permissions**", member=member), "```diff"]

            for permission, value in permissions.items():
                sign = "+" if value else "-"
                message.append(f"{sign} {permission}")
            message.append("```")
            await ctx.send("\n".join(message))
        else:
            await ctx.send(_("There are no specific permissions for this member."))

    @permissions.group()
    async def set(self, ctx: MyContext, ):
        """
        Set a permission in a guild, a channel, for a member...
        """
        if not ctx.invoked_subcommand:
            await ctx.send_help(ctx.command)

    @set.command(name="user")
    @checks.has_permission("bot.administrator")
    async def set_user(self, ctx: MyContext, user: discord.User, permission: str, value: bool):
        """
        Set a permission for a specific user, globally.
        """
        _ = await ctx.get_translate_function()

        db_user = await get_from_db(user, as_user=True)
        db_user.permissions[permission] = value
        await db_user.save(update_fields=['permissions'])

        await ctx.send(_("👌 Permission {permission} for user {user.name}#{user.discriminator} has been set to {value} globally.",
                         permission=escape_everything(permission),
                         user=user,
                         value=value))

    @set.command(name="member")
    @checks.server_admin_or_permission("server.manage_permissions.member")
    async def set_member(self, ctx: MyContext, member: discord.Member, permission: str, value: bool):
        """
        Set a permission for a member in a guild
        """
        _ = await ctx.get_translate_function()

        db_user = await get_from_db(member, as_user=False)
        db_user.permissions[permission] = value
        await db_user.save(update_fields=['permissions'])
        await ctx.send(_("👌 Permission {permission} for member {member.name}#{member.discriminator} has been set to {value} globally.",
                         permission=escape_everything(permission),
                         member=member,
                         value=value))
    @set.command(name="channel")
    @checks.server_admin_or_permission("server.manage_permissions.channel")
    async def set_channel(self, ctx: MyContext, channel: discord.TextChannel, role: discord.Role, permission: str, value: bool):
        """
        Set a permission for a role in a channel
        """
        _ = await ctx.get_translate_function()

        if channel not in ctx.guild.channels:
            await ctx.send(_("❌ Can't set permissions in a channel that is not in this guild."))
            return False

        if role.guild.id != ctx.guild.id:
            await ctx.send(_("❌ Can't set permissions for a role that does not exist in this guild."))
            return False

        db_channel = await get_from_db(channel)
        current_permissions = db_channel.permissions.get(str(role.id), {})
        current_permissions[permission] = value

        db_channel.permissions[str(role.id)] = current_permissions

        await db_channel.save(update_fields=['permissions'])
        await ctx.send(_("👌 Permission {permission} for role {role_name} [`{role_id}`] has been set to {value} in this channel.",
                         permission=escape_everything(permission),
                         role_name=escape_everything(role.name),
                         role_id=role.id,
                         value=value))

    @set.command(name="guild")
    @checks.server_admin_or_permission("server.manage_permissions.guild")
    async def set_guild(self, ctx: MyContext, role: discord.Role, permission: str, value: bool):
        """
        Set a permission for a role in a guild
        """
        _ = await ctx.get_translate_function()

        if role.guild.id != ctx.guild.id:
            await ctx.send(_("❌ Can't set permissions for a role that does not exist in this guild."))
            return False

        db_guild = await get_from_db(ctx.guild)

        current_permissions = db_guild.permissions.get(str(role.id), {})
        current_permissions[permission] = value
        db_guild.permissions[str(role.id)] = current_permissions

        await db_guild.save(update_fields=['permissions'])
        await ctx.send(_("👌 Permission {permission} for role {role_name} [`{role_id}`] has been set to {value} in this guild.",
                         permission=escape_everything(permission),
                         role_name=escape_everything(role.name),
                         role_id=role.id,
                         value=value))


setup = PermissionsCommands.setup
