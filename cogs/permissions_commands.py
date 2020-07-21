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

    @permissions.group()
    async def view(self, ctx: MyContext):
        """
        Do you have that permission you'd so much like to have ?
        """

    @view.command(name="me")
    async def view_me(self, ctx: MyContext, permission: str, negate: bool = False, administrator: bool = True, show_none: bool = False):
        """
        Check a permission for yourself
        """

        value = await permissions.has_permission(ctx, permission, negate=negate, administrator=administrator)
        if value:
            await ctx.send("😃 You have that permission.")
        else:
            await ctx.send("☹️ You don't have that permission.")

        if ctx.guild:
            message = [f"Details of permissions hierarchy", "```diff"]
            parsed_permission = permission.split(".")

            default_permissions = ctx.bot.config['permissions']['default']

            value, by = _recursive_permission_check(parsed_permission, default_permissions)
            message.append(f"{get_sign(value)} Default (from {get_sign(value)}{by})")

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
                        message.append(f"{get_sign(value)} Guild role {escape_everything(role.name)} (from {get_sign(value)}{by})")

            channel_permissions = db_channel.permissions
            for role in ctx.author.roles:
                role_permissions = channel_permissions.get(str(role.id), {})
                if len(role_permissions):
                    value, by = _recursive_permission_check(parsed_permission, role_permissions)
                    if value in [True, False] or show_none:
                        message.append(f"{get_sign(value)} Channel role {escape_everything(role.name)} (from {get_sign(value)}{by})")

            member_permissions = db_member.permissions
            value, by = _recursive_permission_check(parsed_permission, member_permissions)
            if value in [True, False] or show_none:
                message.append(f"{get_sign(value)} Member (from {get_sign(value)}{by})")

            fixed_permissions = ctx.bot.config['permissions']['fixed']
            value, by = _recursive_permission_check(parsed_permission, fixed_permissions)
            if value in [True, False] or show_none:
                message.append(f"{get_sign(value)} Fixed (from {get_sign(value)}{by})")

            user_permissions = db_user.permissions
            value, by = _recursive_permission_check(parsed_permission, user_permissions)
            if value in [True, False] or show_none:
                message.append(f"{get_sign(value)} User (from {get_sign(value)}{by})")

            message.append("```")

            await ctx.send("\n".join(message))

    @view.command(name="guild")
    @commands.cooldown(2, 30, commands.BucketType.guild)
    async def view_guild(self, ctx: MyContext):
        """
        Display all permissions set for this guild
        """
        said_something = False
        guild = ctx.guild
        db_guild = await get_from_db(guild)
        permissions_by_role = db_guild.permissions

        for role_id, role_permissions in permissions_by_role.items():
            role = guild.get_role(int(role_id))
            if role and len(role_permissions):
                message = [f"**{escape_everything(role.name)} permissions**", "```diff"]

                for permission, value in role_permissions.items():
                    sign = "+" if value else "-"
                    message.append(f"{sign} {permission}")
                message.append("```")
                said_something = True
                await ctx.send("\n".join(message))

        if not said_something:
            await ctx.send("There are no specific permissions set in this guild.")

    @view.command(name="channel")
    @commands.cooldown(2, 30, commands.BucketType.guild)
    async def view_channel(self, ctx: MyContext, channel: discord.TextChannel = None):
        """
        Display all permissions set for this channel
        """
        said_something = False
        guild = ctx.guild
        if not channel or channel.guild.id != guild.id:
            channel = ctx.channel

        db_channel = await get_from_db(channel)
        permissions_by_role = db_channel.permissions

        for role_id, role_permissions in permissions_by_role.items():
            role = guild.get_role(int(role_id))
            if role and len(role_permissions):
                message = [f"**{escape_everything(role.name)} permissions**", "```diff"]

                for permission, value in role_permissions.items():
                    sign = "+" if value else "-"
                    message.append(f"{sign} {permission}")
                message.append("```")
                said_something = True
                await ctx.send("\n".join(message))

        if not said_something:
            await ctx.send("There are no specific permissions set in this channel.")

    @view.command(name="member")
    @commands.cooldown(2, 30, commands.BucketType.guild)
    async def view_member(self, ctx: MyContext, member: discord.Member = None):
        """
        Display all permissions set for this channel
        """
        if not member:
            member = ctx.author

        db_member = await get_from_db(member, as_user=False)
        permissions = db_member.permissions

        if len(permissions):
            message = [f"**{member.name}#{member.discriminator} permissions**", "```diff"]

            for permission, value in permissions.items():
                sign = "+" if value else "-"
                message.append(f"{sign} {permission}")
            message.append("```")
            await ctx.send("\n".join(message))
        else:
            await ctx.send("There are no specific permissions for this member.")

    @permissions.group()
    async def set(self, ctx: MyContext, ):
        """
        Set a permission in a guild, a channel, for a member...
        """

    @set.command(name="user")
    @checks.has_permission("bot.administrator")
    async def set_user(self, ctx: MyContext, user: discord.User, permission: str, value: bool):
        """
        Set a permission for a specific user, globally.
        """
        db_user = await get_from_db(user, as_user=True)
        db_user.permissions[permission] = value
        await db_user.save(update_fields=['permissions'])

        await ctx.send(f"👌 Permission {escape_everything(permission)} for user {user.name}#{user.discriminator} has been set to {value} globally.")

    @set.command(name="member")
    @checks.server_admin_or_permission("server.manage_permissions.member")
    async def set_member(self, ctx: MyContext, member: discord.Member, permission: str, value: bool):
        """
        Set a permission for a member in a guild
        """
        db_user = await get_from_db(member, as_user=False)
        db_user.permissions[permission] = value
        await db_user.save(update_fields=['permissions'])
        await ctx.send(f"👌 Permission {escape_everything(permission)} for user {member.name}#{member.discriminator} has been set to {value} in this server.")

    @set.command(name="channel")
    @checks.server_admin_or_permission("server.manage_permissions.channel")
    async def set_channel(self, ctx: MyContext, channel: discord.TextChannel, role: discord.Role, permission: str, value: bool):
        """
        Set a permission for a role in a channel
        """
        if channel not in ctx.guild.channels:
            await ctx.send(f"❌ Can't set permissions in a channel that is not in this guild.")
            return False

        if role.guild.id != ctx.guild.id:
            await ctx.send(f"❌ Can't set permissions for a role that does not exist in this guild.")
            return False

        db_channel = await get_from_db(channel)
        current_permissions = db_channel.permissions.get(str(role.id), {})
        current_permissions[permission] = value

        db_channel.permissions[str(role.id)] = current_permissions

        await db_channel.save(update_fields=['permissions'])
        await ctx.send(f"👌 Permission {escape_everything(permission)} for role {escape_everything(role.name)} [`{role.id}`] has been set to {value} in this channel.")

    @set.command(name="guild")
    @checks.server_admin_or_permission("server.manage_permissions.guild")
    async def set_guild(self, ctx: MyContext, role: discord.Role, permission: str, value: bool):
        """
        Set a permission for a role in a guild
        """
        if role.guild.id != ctx.guild.id:
            await ctx.send(f"❌ Can't set permissions for a role that does not exist in this guild.")
            return False

        db_guild = await get_from_db(ctx.guild)

        current_permissions = db_guild.permissions.get(str(role.id), {})
        current_permissions[permission] = value
        db_guild.permissions[str(role.id)] = current_permissions

        await db_guild.save(update_fields=['permissions'])
        await ctx.send(f"👌 Permission {escape_everything(permission)} for role {escape_everything(role.name)} [`{role.id}`] has been set to {value} in this guild.")


setup = PermissionsCommands.setup
