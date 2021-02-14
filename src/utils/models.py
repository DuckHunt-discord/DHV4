import asyncio
import collections
import datetime
import random
import time

import babel.lists
import discord
import typing

from discord.ext import commands
from tortoise import Tortoise, fields
from tortoise.models import Model

from enum import IntEnum, unique
from utils.levels import get_level_info
from utils.translations import translate

DB_LOCKS = collections.defaultdict(asyncio.Lock)


class DefaultDictJSONField(fields.JSONField):
    def __init__(self, default_factory: typing.Callable = int, **kwargs: typing.Any):
        def make_default():
            return collections.defaultdict(default_factory)

        self.default_factory = default_factory
        kwargs["default"] = make_default
        super().__init__(**kwargs)

    def to_python_value(self, value: typing.Optional[typing.Union[str, dict, list]]) -> typing.Optional[collections.defaultdict]:
        ret = super().to_python_value(value)
        return collections.defaultdict(self.default_factory, ret)

    def to_db_value(self, value: typing.Optional[collections.defaultdict],
                    instance: typing.Union[typing.Type[Model], Model]) -> typing.Optional[str]:
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
    first_seen = fields.DatetimeField(auto_now_add=True)

    name = fields.TextField()
    prefix = fields.CharField(20, null=True, default="!")

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
    first_seen = fields.DatetimeField(auto_now_add=True)

    guild = fields.ForeignKeyField('models.DiscordGuild')
    name = fields.TextField()

    webhook_urls = fields.JSONField(default=[])
    api_key = fields.UUIDField(null=True)

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

    night_start_at = fields.IntField(default=0)  # Seconds from midnight UTC
    night_end_at = fields.IntField(default=0)  # Seconds from midnight UTC

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
    spawn_weight_night_ducks = fields.SmallIntField(default=100)
    spawn_weight_sleeping_ducks = fields.SmallIntField(default=5)

    # Duck settings
    ducks_time_to_live = fields.SmallIntField(default=660)  # Seconds
    super_ducks_min_life = fields.SmallIntField(default=2)
    super_ducks_max_life = fields.SmallIntField(default=7)

    def serialize(self, serialize_fields=None):
        DONT_SERIALIZE = {'guild', 'members', 'playerss', 'webhook_urls', 'api_key'}

        ser = {}

        if serialize_fields is None:
            serialize_fields = self._meta.fields.copy() - DONT_SERIALIZE

        for serialize_field in serialize_fields:
            if serialize_field == "discord_id":
                ser[serialize_field] = str(getattr(self, serialize_field))

            ser[serialize_field] = getattr(self, serialize_field)

        return ser

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

    @classmethod
    async def convert(cls, ctx, argument: str):
        _ = await ctx.get_translate_function()

        if argument.isdigit():
            try:
                return cls(min(int(argument), 300))
            except ValueError:
                raise commands.BadArgument(_("This is not a valid level. Choose between {levels}",
                                             levels=babel.lists.format_list(list(AccessLevel.__members__),
                                                                            locale=await ctx.get_language_code())))
        else:
            if not argument.upper().startswith('BOT'):
                try:
                    return getattr(cls, argument.upper())
                except AttributeError:
                    raise commands.BadArgument(_("This is not a valid level. Choose between {levels}",
                                                 levels=babel.lists.format_list(list(AccessLevel.__members__),
                                                                                locale=await ctx.get_language_code())))
            else:
                raise commands.BadArgument(_("Can't set such a high level"))


class DiscordUser(Model):
    discord_id = fields.BigIntField(pk=True)
    first_seen = fields.DatetimeField(auto_now_add=True)

    name = fields.TextField()
    discriminator = fields.CharField(4)
    times_ran_example_command = fields.IntField(default=0)

    inventory = fields.JSONField(default=[])
    trophys = fields.JSONField(default={})

    ping_friendly = fields.BooleanField(default=True)

    language = fields.CharField(6, default="en")
    first_use = fields.BooleanField(default=True)

    access_level_override = fields.IntEnumField(enum_type=AccessLevel, default=AccessLevel.DEFAULT)

    last_votes = DefaultDictJSONField(default_factory=int)  # Unix Timestamps by botlist.
    votes = DefaultDictJSONField(default_factory=int)  # Count of votes by botlist

    boss_kills = fields.IntField(default=0)

    def add_to_inventory(self, item_to_give, item_number=None):
        for item_in_inventory in self.inventory:
            if item_in_inventory["type"] == item_to_give["type"] and \
                    item_in_inventory.get("action", "") == item_to_give.get("action", "") and \
                    item_in_inventory.get("amount", 0) == item_to_give.get("amount", 0):
                item_in_inventory["uses"] = item_in_inventory.get("uses", 1) + item_to_give.get("uses", 1)
                break
        else:
            if item_number:
                self.inventory.insert(item_number, item_to_give)
            else:
                self.inventory.append(item_to_give)

    class Meta:
        table = "users"

    def get_access_level(self):
        return self.access_level_override

    def __str__(self):
        return self.name

    def __repr__(self):
        return f"<User name={self.name}#{self.discriminator}>"


class Player(Model):
    id = fields.IntField(pk=True)
    first_seen = fields.DatetimeField(auto_now_add=True)

    channel = fields.ForeignKeyField('models.DiscordChannel')
    member = fields.ForeignKeyField('models.DiscordMember')

    prestige = fields.SmallIntField(default=0)
    prestige_last_daily = fields.DatetimeField(auto_now_add=True)
    prestige_dailies = fields.IntField(default=0)

    # Inventories
    active_powerups = DefaultDictJSONField(default_factory=int)  # Until a timestamp.
    shooting_stats = DefaultDictJSONField(default_factory=int)  # Count of times.

    stored_achievements = DefaultDictJSONField(default_factory=bool)

    experience = fields.BigIntField(default=0)
    spent_experience = fields.BigIntField(default=0)

    givebacks = fields.IntField(default=0)

    found_items = DefaultDictJSONField()
    bought_items = DefaultDictJSONField()

    # Weapon stats
    bullets = fields.IntField(default=6)
    magazines = fields.IntField(default=2)

    # Weapon & Player status
    last_giveback = fields.DatetimeField(auto_now_add=True)

    weapon_sabotaged_by = fields.ForeignKeyField('models.Player', null=True, on_delete=fields.SET_NULL)

    # Killed ducks stats
    best_times = DefaultDictJSONField(default_factory=lambda: 660)
    killed = DefaultDictJSONField()
    hugged = DefaultDictJSONField()
    hurted = DefaultDictJSONField()
    resisted = DefaultDictJSONField()
    frightened = DefaultDictJSONField()

    def serialize(self, serialize_fields=None):
        DONT_SERIALIZE = {'weapon_sabotaged_by', 'playerss', 'channel', 'member'}
        db_member: DiscordMember = self.member
        db_user: DiscordUser = db_member.user

        ser = {
            "user_id": str(db_user.discord_id),
            "user_name": db_user.name,
            "user_discriminator": db_user.discriminator,
            "member_access_level_override": db_member.get_access_level(),
        }

        if serialize_fields is None:
            serialize_fields = self._meta.fields.copy() - DONT_SERIALIZE

        for serialize_field in serialize_fields:
            value = getattr(self, serialize_field)
            if isinstance(value, datetime.datetime):
                value = value.timestamp()
            elif isinstance(value, datetime.timedelta):
                value = value.total_seconds()
            elif serialize_field == "channel_id":
                value = str(value)

            ser[serialize_field] = value

            if serialize_field == "killed":
                ser["killed_total"] = sum(self.killed.values())

        return ser

    @property
    def real_reliability(self):
        total_shots = self.shooting_stats["bullets_used"] + self.shooting_stats["shots_jamming_weapon"]
        if total_shots:
            return 100 - round(self.shooting_stats["shots_jamming_weapon"] / total_shots * 100, 2)
        else:
            return 0

    @property
    def real_accuracy(self):
        total_shots = self.shooting_stats["bullets_used"]
        if total_shots:
            return 100 - round(self.shooting_stats["missed"] / total_shots * 100, 2)
        else:
            return 0

    @property
    def computed_achievements(self):
        return {
            'murderer': self.shooting_stats.get('murders', 0) >= 1,
            'big_spender': self.spent_experience >= 2000,
            'first_week': self.givebacks >= 7,
            'first_month': self.givebacks >= 30,
            'first_year': self.givebacks >= 365,
            'i_dont_want_bullets': self.found_items.get('left_bullet', 0) >= 1,
            'baby_killer': self.killed.get('baby', 0) >= 5,
            'maths': self.killed.get('prof', 0) >= 5,
            'brains': self.shooting_stats.get('brains_eaten', 0) >= 5,
            'sentry_gun': self.shooting_stats.get('bullets_used', 0) >= 1000,
            'homing_killed': self.shooting_stats.get('homing_kills', 0) >= 1,
        }

    @property
    def achievements(self):
        return {
            **self.computed_achievements,
            **self.stored_achievements,
        }

    async def get_bonus_experience(self, given_experience):
        if self.is_powerup_active('clover'):
            return self.active_powerups['clover_exp']
        return 0

    def level_info(self):
        li = get_level_info(self.experience).copy()

        if self.prestige >= 8:
            li['bullets'] *= 2

        return li

    async def maybe_giveback(self):
        now = datetime.datetime.now()
        if self.last_giveback.date() != now.date():
            level_info = self.level_info()
            self.last_giveback = now
            self.givebacks += 1
            self.magazines = level_info["magazines"]
            self.active_powerups['confiscated'] = 0
            await self.save()

    async def edit_experience_with_levelups(self, ctx, delta):
        old_level_info = self.level_info()
        self.experience += delta
        new_level_info = self.level_info()

        if old_level_info['level'] == new_level_info['level']:
            return
        else:
            if isinstance(ctx, discord.TextChannel):
                guild = ctx.guild
                db_guild = await get_from_db(guild)
                language_code = db_guild.language

                def _(message):
                    return translate(message, language_code)

            else:
                _ = await ctx.get_translate_function()

            e = discord.Embed()
            e.add_field(name=_("Experience"), value=f"{self.experience - delta} -> {self.experience}", inline=False)
            e.add_field(name=_("Level"),
                        value=f"({old_level_info['level']}) {_(old_level_info['name'])} -> ({new_level_info['level']}) {_(new_level_info['name'])}",
                        inline=False)

            if old_level_info['accuracy'] != new_level_info['accuracy']:
                e.add_field(name=_("Accuracy"), value=f"{old_level_info['accuracy']}% -> {new_level_info['accuracy']}%",
                            inline=False)

            if old_level_info['reliability'] != new_level_info['reliability']:
                e.add_field(name=_("Reliability"),
                            value=f"{old_level_info['reliability']}% -> {new_level_info['reliability']}%", inline=False)

            if old_level_info['bullets'] != new_level_info['bullets']:
                e.add_field(name=_("Bullets"), value=f"{old_level_info['bullets']} -> {new_level_info['bullets']}")

            if old_level_info['magazines'] != new_level_info['magazines']:
                e.add_field(name=_("Magazines"),
                            value=f"{old_level_info['magazines']} -> {new_level_info['magazines']}")

            if old_level_info['level'] < new_level_info['level']:
                # Level UP
                e.title = _("You leveled up!")
                e.color = discord.Colour.green()
            else:
                # Level DOWN
                e.title = _("You leveled down!")
                e.color = discord.Colour.red()

            asyncio.ensure_future(ctx.send(embed=e))

    def is_powerup_active(self, powerup):
        if self.prestige >= 1 and powerup == "sunglasses":
            return True
        elif self.prestige >= 5 and powerup == "coat":
            return True
        elif self.prestige >= 7 and powerup == "kill_licence":
            return True
        elif powerup in ["sight", "detector", "sand", "mirror", "homing_bullets", "dead", "confiscated",
                         "jammed"]:
            return self.active_powerups[powerup] > 0
        else:
            now = time.time()
            return self.active_powerups[powerup] >= now

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
            if discord_object.name != db_obj.name:
                db_obj.name = discord_object.name
                await db_obj.save()

            return db_obj
        elif isinstance(discord_object, discord.TextChannel):
            db_obj = await DiscordChannel.filter(discord_id=discord_object.id).first()
            if not db_obj:
                db_obj = DiscordChannel(discord_id=discord_object.id, name=discord_object.name,
                                        guild=await get_from_db(discord_object.guild))
                await db_obj.save()

            if discord_object.name != db_obj.name:
                db_obj.name = discord_object.name
                await db_obj.save()

            return db_obj
        elif isinstance(discord_object, discord.Member) and not as_user:
            db_obj = await DiscordMember.filter(user__discord_id=discord_object.id,
                                                guild__discord_id=discord_object.guild.id).first().prefetch_related(
                "user", "guild")
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

            if discord_object.name != db_obj.name or discord_object.discriminator != db_obj.discriminator:
                db_obj.name = discord_object.name
                db_obj.discriminator = discord_object.discriminator
                await db_obj.save()

            return db_obj


async def get_random_player(channel: typing.Union[DiscordChannel, discord.TextChannel]):
    if isinstance(channel, discord.TextChannel):
        db_channel = get_from_db(channel)
    else:
        db_channel = channel

    return random.choice(await Player.filter(channel=db_channel).prefetch_related("member__user"))


async def get_player(member: discord.Member, channel: discord.TextChannel, giveback=False):
    async with DB_LOCKS[(member, channel)]:
        db_obj = await Player.filter(member__user__discord_id=member.id,
                                     channel__discord_id=channel.id).prefetch_related('member__user').first()
        if not db_obj:
            db_obj = Player(channel=await get_from_db(channel), member=await get_from_db(member, as_user=False))
            await db_obj.save()
        elif giveback:
            await db_obj.maybe_giveback()

        return db_obj


async def get_enabled_channels():
    return await DiscordChannel.filter(enabled=True).all()


async def init_db_connection(config, create_dbs=False):
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

    if create_dbs:
        # This would create the databases, something that should be handled by Django.
        await Tortoise.generate_schemas()
