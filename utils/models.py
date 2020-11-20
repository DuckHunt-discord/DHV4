import asyncio
import collections
import datetime

import discord
import typing
from tortoise import Tortoise, fields
from tortoise.models import Model

from enum import IntEnum, unique


DB_LOCKS = collections.defaultdict(asyncio.Lock)


class DefaultDictJSONField(fields.JSONField):
    def __init__(self, default_factory: typing.Callable = int, **kwargs: typing.Any):
        self.default_factory = default_factory
        kwargs["default"] = collections.defaultdict(default_factory)
        super().__init__(**kwargs)

    def to_python_value(self, value: typing.Optional[typing.Union[str, dict, list]]) -> typing.Optional[collections.defaultdict]:
        ret = super().to_python_value(value)
        return collections.defaultdict(self.default_factory, ret)

    def to_db_value(self, value: typing.Optional[collections.defaultdict], instance: typing.Union[typing.Type[Model], Model]) -> typing.Optional[str]:
        value = dict(value)
        return super().to_db_value(value, instance)


class PercentageField(fields.SmallIntField):
    # TODO: Use constraints when they go out :)
    def to_db_value(self, value: typing.Any, instance: typing.Union[typing.Type[Model], Model]):
        value = min(100, max(0, int(value)))
        return super().to_db_value(value, instance)


# TODO : https://github.com/long2ice/aerich
class DiscordGuild(Model):
    discord_id = fields.BigIntField(pk=True)
    name = fields.TextField()
    prefix = fields.CharField(20, null=True)

    vip = fields.BooleanField(default=False)

    language = fields.CharField(6, default="en")

    class Meta:
        table = "guilds"

    def __str__(self):
        return self.name

    def __repr__(self):
        return f"<Guild name={self.name}>"


class DiscordChannel(Model):
    discord_id = fields.BigIntField(pk=True)

    guild = fields.ForeignKeyField('models.DiscordGuild')
    name = fields.TextField()

    webhook_urls = fields.JSONField(default=[])

    # Generic settings
    use_webhooks = fields.BooleanField(default=True)
    use_emojis = fields.BooleanField(default=True)
    enabled = fields.BooleanField(default=False)

    allow_global_items = fields.BooleanField(default=True)

    tax_on_user_send = PercentageField(default=5)
    mentions_when_killed = fields.BooleanField(default=True)
    show_duck_lives = fields.BooleanField(default=True)

    # Luck percentages
    kill_on_miss_chance = PercentageField(default=3)
    duck_frighten_chance = PercentageField(default=7)

    # Shop items
    clover_min_experience = fields.SmallIntField(default=1)
    clover_max_experience = fields.SmallIntField(default=10)

    # Experience
    base_duck_exp = fields.SmallIntField(default=10)
    per_life_exp = fields.SmallIntField(default=7)

    # Spawn rates
    ducks_per_day = fields.SmallIntField(default=96)

    spawn_weight_normal_ducks = fields.SmallIntField(default=100)
    spawn_weight_super_ducks = fields.SmallIntField(default=15)
    spawn_weight_baby_ducks = fields.SmallIntField(default=7)
    spawn_weight_prof_ducks = fields.SmallIntField(default=10)
    spawn_weight_ghost_ducks = fields.SmallIntField(default=1)
    spawn_weight_moad_ducks = fields.SmallIntField(default=5)
    spawn_weight_mechanical_ducks = fields.SmallIntField(default=1)
    spawn_weight_armored_ducks = fields.SmallIntField(default=3)
    spawn_weight_golden_ducks = fields.SmallIntField(default=1)
    spawn_weight_plastic_ducks = fields.SmallIntField(default=6)
    spawn_weight_kamikaze_ducks = fields.SmallIntField(default=6)

    # Duck settings
    ducks_time_to_live = fields.SmallIntField(default=660)  # Seconds
    super_ducks_min_life = fields.SmallIntField(default=2)
    super_ducks_max_life = fields.SmallIntField(default=7)

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
    BOT_MODERATOR = 500
    BOT_OWNER = 600


class DiscordUser(Model):
    discord_id = fields.BigIntField(pk=True)
    name = fields.TextField()
    discriminator = fields.CharField(4)
    times_ran_example_command = fields.IntField(default=0)

    inventory = fields.JSONField(default=[])

    language = fields.CharField(6, default="en")
    first_use = fields.BooleanField(default=True)

    access_level_override = fields.IntEnumField(enum_type=AccessLevel, default=AccessLevel.DEFAULT)

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

    # Inventories
    active_powerups = DefaultDictJSONField(default_factory=int)  # Until a timestamp.

    achievements = DefaultDictJSONField(default_factory=bool)

    experience = fields.BigIntField(default=0)
    spent_experience = fields.BigIntField(default=0)
    murders = fields.SmallIntField(default=0)

    givebacks = fields.IntField(default=0)

    found_items = DefaultDictJSONField()

    # Weapon stats
    shots_without_ducks = fields.IntField(default=0)
    effective_reloads = fields.IntField(default=0)
    no_magazines_reloads = fields.IntField(default=0)
    unneeded_reloads = fields.IntField(default=0)

    bullets = fields.IntField(default=6)
    magazines = fields.IntField(default=2)

    # Weapon & Player status
    last_giveback = fields.DatetimeField(auto_now_add=True)

    weapon_confiscated = fields.BooleanField(default=False)
    weapon_jammed = fields.BooleanField(default=False)
    weapon_sabotaged_by = fields.ForeignKeyField('models.Player', null=True, on_delete=fields.SET_NULL)
    sand_in_weapon = fields.BooleanField(default=False)

    is_dazzled = fields.BooleanField(default=False)
    wet_until = fields.DatetimeField(auto_now_add=True)

    # Killed ducks stats
    best_times = DefaultDictJSONField(default_factory=lambda: 660)
    killed = DefaultDictJSONField()
    hugged = DefaultDictJSONField()
    hurted = DefaultDictJSONField()
    resisted = DefaultDictJSONField()
    frightened = DefaultDictJSONField()

    async def get_bonus_experience(self, given_experience):
        return 0

    class Meta:
        table = "players"

    def __repr__(self):
        return f"<Player member={self.member} channel={self.channel}>"


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
    async with DB_LOCKS[(discord_object, as_user)]:
        if isinstance(discord_object, discord.Guild):
            db_obj = await DiscordGuild.filter(discord_id=discord_object.id).first()
            if not db_obj:
                db_obj = DiscordGuild(discord_id=discord_object.id, name=discord_object.name)
                await db_obj.save()
            return db_obj
        elif isinstance(discord_object, discord.TextChannel):
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
    async with DB_LOCKS[(member, channel)]:
        db_obj = await Player.filter(member__user__discord_id=member.id, channel__discord_id=channel.id).first()
        if not db_obj:
            db_obj = Player(channel=await get_from_db(channel), member=await get_from_db(member, as_user=False))
            await db_obj.save()
        return db_obj


async def get_enabled_channels():
    return await DiscordChannel.filter(enabled=True).all()


async def init_db_connection(config):
    tortoise_config = {
        'connections': {
            # Dict format for connection
            'default': {
                'engine'     : 'tortoise.backends.asyncpg',
                'credentials': {
                    'host'    : config['host'],
                    'port'    : config['port'],
                    'user'    : config['user'],
                    'password': config['password'],
                    'database': config['database'],
                }
            },
        },
        'apps'       : {
            'models': {
                'models'            : ["utils.models", "aerich.models"],
                'default_connection': 'default',
            }
        }
    }

    await Tortoise.init(tortoise_config)

    await Tortoise.generate_schemas()
