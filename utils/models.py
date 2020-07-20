import discord
from tortoise import Tortoise, fields
from tortoise.models import Model

from utils.ctx_class import MyContext


class DiscordGuild(Model):
    id = fields.IntField(pk=True)
    discord_id = fields.BigIntField(index=True)
    name = fields.TextField()
    prefix = fields.CharField(20, null=True)
    permissions = fields.JSONField(default={})

    class Meta:
        table = "guilds"

    def __str__(self):
        return self.name

    def __repr__(self):
        return f"<Guild name={self.name}>"


class DiscordChannel(Model):
    id = fields.IntField(pk=True)
    guild = fields.ForeignKeyField('models.DiscordGuild')
    discord_id = fields.BigIntField(index=True)
    name = fields.TextField()
    permissions = fields.JSONField(default={})

    class Meta:
        table = "channels"

    def __str__(self):
        return self.name

    def __repr__(self):
        return f"<Channel name={self.name}>"


class DiscordUser(Model):
    id = fields.IntField(pk=True)
    discord_id = fields.BigIntField(index=True)
    name = fields.TextField()
    discriminator = fields.CharField(4)
    last_modified = fields.DatetimeField(auto_now=True)
    times_ran_example_command = fields.IntField(default=0)
    permissions = fields.JSONField(default={})

    class Meta:
        table = "users"

    def __str__(self):
        return self.name

    def __repr__(self):
        return f"<User name={self.name}#{self.discriminator}>"


class DiscordMember(Model):
    id = fields.IntField(pk=True)
    guild = fields.ForeignKeyField('models.DiscordGuild')
    user = fields.ForeignKeyField('models.DiscordUser')
    permissions = fields.JSONField(default={})

    class Meta:
        table = "members"

    def __repr__(self):
        return f"<Member user={self.user} guild={self.guild}>"


async def get_from_db(discord_object, as_user=False):
    if isinstance(discord_object, discord.Guild):
        db_obj = await DiscordGuild.filter(discord_id=discord_object.id).first()
        if not db_obj:
            db_obj = DiscordGuild(discord_id=discord_object.id, name=discord_object.name)
            await db_obj.save()
        return db_obj
    elif isinstance(discord_object, discord.abc.GuildChannel):
        db_obj = await DiscordChannel.filter(discord_id=discord_object.id).first()
        if not db_obj:
            db_obj = DiscordChannel(discord_id=discord_object.id, name=discord_object.name, guild=get_from_db(discord_object.guild))
            await db_obj.save()
        return db_obj
    elif isinstance(discord_object, discord.Member) and not as_user:
        db_obj = await DiscordMember.filter(user__discord_id=discord_object.id).first().prefetch_related("user", "guild")
        if not db_obj:
            db_obj = DiscordMember(guild=await get_from_db(discord_object.guild), user=await get_from_db(discord_object, as_user=True))
            await db_obj.save()
        return db_obj
    elif isinstance(discord_object, discord.User) or isinstance(discord_object, discord.Member) and as_user:
        db_obj = await DiscordUser.filter(discord_id=discord_object.id).first()
        if not db_obj:
            db_obj = DiscordUser(discord_id=discord_object.id, name=discord_object.name, discriminator=discord_object.discriminator)
            await db_obj.save()
        return db_obj


async def get_ctx_permissions(ctx: MyContext) -> dict:
    """
    Discover the permissions for a specified context. Permissions are evaluated first from the default permissions
    specified in the config file, then by the guild config, the channel conifg, and again from the member_specific
    permissions, then by the fixed permissions as seen in the config file, and finally using user overrides set by
    the bot administrator in the database.
    :param ctx:
    :return:
    """
    if ctx.guild:
        db_member: DiscordMember = await get_from_db(ctx.author)
        db_channel: DiscordChannel = await get_from_db(ctx.channel)
        db_user: DiscordUser = db_member.user
        db_guild: DiscordGuild = db_member.guild
        guild_permissions = db_guild.permissions
        channel_permissions = db_channel.permissions
        member_permissions = db_member.permissions
        user_permissions = db_user.permissions
        subguild_permissions = {}
        subchannel_permissions = {}
        for role in ctx.author.roles:
            subguild_permissions = {**subguild_permissions, **guild_permissions.get(role.id, {})}
            subchannel_permissions = {**subchannel_permissions, **channel_permissions.get(role.id, {})}
    else:
        subguild_permissions = {}
        subchannel_permissions = {}
        member_permissions = {}
        db_user: DiscordUser = await get_from_db(ctx.author, as_user=True)
        user_permissions = db_user.permissions

    default_permissions = ctx.bot.config['permissions']['default']
    fixed_permissions = ctx.bot.config['permissions']['fixed']

    permissions = {**default_permissions, **subguild_permissions, **subchannel_permissions, **member_permissions, **fixed_permissions, **user_permissions}
    return permissions


async def init_db_connection(config):
    tortoise_config = {
        'connections': {
            # Dict format for connection
            'default': {
                'engine': 'tortoise.backends.asyncpg',
                'credentials': {
                    'host': config['host'],
                    'port': config['port'],
                    'user': config['user'],
                    'password': config['password'],
                    'database': config['database'],
                }
            },
        },
        'apps': {
            'models': {
                'models': ["utils.models"],
                'default_connection': 'default',
            }
        }
    }

    await Tortoise.init(tortoise_config)

    await Tortoise.generate_schemas()
