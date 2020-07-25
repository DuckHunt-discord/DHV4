import discord
import typing
from tortoise import Tortoise, fields
from tortoise.models import Model

if typing.TYPE_CHECKING:
    from utils.ctx_class import MyContext


# TODO : https://github.com/long2ice/aerich

class DiscordGuild(Model):
    id = fields.IntField(pk=True)
    discord_id = fields.BigIntField(index=True)
    name = fields.TextField()
    prefix = fields.CharField(20, null=True)
    permissions = fields.JSONField(default={})

    language = fields.CharField(6, default="en")

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

    webhook_url = fields.TextField(null=True)

    # Generic settings
    use_emojis = fields.BooleanField(default=True)  # Seconds

    # Experience
    base_duck_exp = fields.IntField(default=10)
    per_life_exp = fields.IntField(default=7)

    # Duck settings
    ducks_time_to_live = fields.IntField(default=660)  # Seconds
    super_ducks_min_life = fields.IntField(default=2)
    super_ducks_max_life = fields.IntField(default=7)

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

    language = fields.CharField(6, default="en")

    class Meta:
        table = "users"

    def __str__(self):
        return self.name

    def __repr__(self):
        return f"<User name={self.name}#{self.discriminator}>"


class Player(Model):
    id = fields.IntField(pk=True)
    channel = fields.ForeignKeyField('models.DiscordChannel')
    member = fields.ForeignKeyField('models.DiscordMember')

    # Generic stats
    experience = fields.BigIntField(default=0)

    # Killed ducks stats
    killed_normal_ducks = fields.IntField(default=0)
    killed_super_ducks = fields.IntField(default=0)
    killed_baby_ducks = fields.IntField(default=0)
    killed_prof_ducks = fields.IntField(default=0)

    hugged_normal_ducks = fields.IntField(default=0)
    hugged_super_ducks = fields.IntField(default=0)
    hugged_baby_ducks = fields.IntField(default=0)
    hugged_prof_ducks = fields.IntField(default=0)

    hurted_super_ducks = fields.IntField(default=0)

    async def get_bonus_experience(self, given_experience):
        return 0

    class Meta:
        table = "players"

    def __repr__(self):
        return f"<Player member={self.member} channel={self.channel}>"


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
            db_obj = DiscordChannel(discord_id=discord_object.id, name=discord_object.name, guild=await get_from_db(discord_object.guild))
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


async def get_player(member: discord.Member, channel: discord.TextChannel):
    db_obj = await Player.filter(member__user__discord_id=member.id, channel__discord_id=channel.id).first()
    if not db_obj:
        db_obj = Player(channel=await get_from_db(channel.guild), member=await get_from_db(member, as_user=False))
        await db_obj.save()
    return db_obj


async def get_ctx_permissions(ctx: 'MyContext') -> dict:
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
            subguild_permissions = {**subguild_permissions, **guild_permissions.get(str(role.id), {})}
            subchannel_permissions = {**subchannel_permissions, **channel_permissions.get(str(role.id), {})}
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
                'models': ["utils.models", "aerich.models"],
                'default_connection': 'default',
            }
        }
    }

    await Tortoise.init(tortoise_config)

    await Tortoise.generate_schemas()
