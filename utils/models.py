import typing
from enum import IntEnum, unique

import discord
# noinspection PyPackageRequirements
from tortoise import Tortoise, fields
# noinspection PyPackageRequirements
from tortoise.models import Model

# TODO : https://github.com/long2ice/aerich

class DiscordGuild(Model):
    id = fields.IntField(pk=True)
    discord_id = fields.BigIntField(index=True)
    name = fields.TextField()
    prefix = fields.CharField(20, null=True)

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

    class Meta:
        table = "channels"

    def __str__(self):
        return self.name

    def __repr__(self):
        return f"<Channel name={self.name}>"


@unique
class AccessLevel(IntEnum):
    BANNED = 0
    DEFAULT = 50
    TRUSTED = 100
    MODERATOR = 200
    ADMIN = 300


class DiscordUser(Model):
    id = fields.IntField(pk=True)
    discord_id = fields.BigIntField(index=True)
    name = fields.TextField()
    discriminator = fields.CharField(4)
    last_modified = fields.DatetimeField(auto_now=True)
    times_ran_example_command = fields.IntField(default=0)

    language = fields.CharField(6, default="en")
    access_level_override = fields.IntEnumField(enum_type=AccessLevel, default=AccessLevel.DEFAULT)

    class Meta:
        table = "users"

    def __str__(self):
        return self.name

    def __repr__(self):
        return f"<User name={self.name}#{self.discriminator}>"


class DiscordMember(Model):
    id = fields.IntField(pk=True)
    guild: DiscordGuild = fields.ForeignKeyField('models.DiscordGuild')
    user: DiscordUser = fields.ForeignKeyField('models.DiscordUser')

    access_level = fields.IntEnumField(enum_type=AccessLevel, default=AccessLevel.DEFAULT)

    def get_access_level(self):
        override = self.user.access_level_override
        if override != AccessLevel.DEFAULT:
            return override
        else:
            return self.access_level

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
            db_obj = DiscordChannel(discord_id=discord_object.id, name=discord_object.name,
                                    guild=await get_from_db(discord_object.guild))
            await db_obj.save()
        return db_obj
    elif isinstance(discord_object, discord.Member) and not as_user:
        db_obj = await DiscordMember.filter(user__discord_id=discord_object.id,
                                            guild__discord_id=discord_object.guild.id).\
                                            first().\
                                            prefetch_related("user", "guild")
        if not db_obj:
            db_obj = DiscordMember(guild=await get_from_db(discord_object.guild),
                                   user=await get_from_db(discord_object, as_user=True))
            await db_obj.save()
        return db_obj
    elif isinstance(discord_object, discord.User) or isinstance(discord_object, discord.Member) and as_user:
        db_obj = await DiscordUser.filter(discord_id=discord_object.id).first()
        if not db_obj:
            db_obj = DiscordUser(discord_id=discord_object.id, name=discord_object.name,
                                 discriminator=discord_object.discriminator)
            await db_obj.save()
        return db_obj


async def init_db_connection(config):
    # noinspection SpellCheckingInspection
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
