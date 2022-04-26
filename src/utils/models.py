import asyncio
import collections
import copy
import datetime
import random
import string
import time

import babel.lists
import discord
import typing

from discord.ext import commands
from tortoise import Tortoise, fields, timezone
from tortoise.models import Model

from enum import IntEnum, unique

from utils.coats import Coats
from utils.levels import get_level_info
from utils.translations import translate

DB_LOCKS = collections.defaultdict(asyncio.Lock)
SECOND = 1
MINUTE = 60 * SECOND
HOUR = 60 * MINUTE
DAY = 24 * HOUR


class DefaultDictJSONField(fields.JSONField):
    def __init__(self, default_factory: typing.Callable = int, **kwargs: typing.Any):
        def make_default():
            return collections.defaultdict(default_factory)

        self.default_factory = default_factory
        kwargs["default"] = make_default
        super().__init__(**kwargs)

    def to_python_value(self, value: typing.Optional[typing.Union[str, dict, list]]) -> typing.Optional[
        collections.defaultdict]:
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


class SupportTicket(Model):
    user: fields.ForeignKeyRelation["DiscordUser"] = \
        fields.ForeignKeyField('models.DiscordUser',
                               related_name="support_tickets",
                               db_index=True)

    opened_at = fields.DatetimeField(auto_now_add=True)

    closed = fields.BooleanField(default=False)
    closed_at = fields.DatetimeField(null=True, blank=True)

    closed_by: fields.ForeignKeyRelation["DiscordUser"] = \
        fields.ForeignKeyField('models.DiscordUser',
                               related_name="closed_tickets",
                               on_delete=fields.SET_NULL,
                               db_index=False,
                               null=True)

    close_reason = fields.TextField(blank=True, default="")

    last_tag_used: fields.ForeignKeyRelation["Tag"] = \
        fields.ForeignKeyField('models.Tag',
                               related_name='used_in_tickets',
                               on_delete=fields.SET_NULL,
                               db_index=False,
                               null=True)

    def close(self, by_user: 'DiscordUser', reason: typing.Optional[str] = None):
        if reason is None:
            reason = ""

        self.closed = True
        self.closed_at = timezone.now()
        self.closed_by = by_user
        self.close_reason = reason


class DiscordGuild(Model):
    discord_id = fields.BigIntField(pk=True)
    first_seen = fields.DatetimeField(auto_now_add=True)

    channels: fields.ReverseRelation["DiscordChannel"]
    members: fields.ReverseRelation["DiscordMember"]

    name = fields.TextField()
    prefix = fields.CharField(20, null=True, default="!")
    channel_disabled_message = fields.BooleanField(default=True)

    vip = fields.BooleanField(default=False)

    language = fields.CharField(6, default="en")

    class Meta:
        table = "guilds"

    def __str__(self):
        return self.name

    def __repr__(self):
        return f"<Guild name={self.name}>"


class SunState(IntEnum):
    DAY = 0
    NIGHT = 1


class DucksLeft:
    """
    This class stores the state of a channel, counting the ducks left.
    """

    def __init__(self, channel, day_ducks=None, night_ducks=None):
        self.channel: discord.TextChannel = channel
        self.db_channel: typing.Optional[DiscordChannel] = None
        self.day_ducks: int = day_ducks
        self.night_ducks: int = night_ducks

    async def compute_ducks_count(self, db_channel=None, now=None):
        if not db_channel:
            db_channel: DiscordChannel = await get_from_db(self.channel)

        self.db_channel = db_channel

        if not now:
            now = int(time.time())

        now = now % DAY

        total_seconds_left = DAY - now
        total_night_seconds = db_channel.night_seconds_left(0)
        night_seconds_left = db_channel.night_seconds_left(now)
        total_day_seconds = DAY - total_night_seconds
        day_seconds_left = total_seconds_left - night_seconds_left

        total_ducks_today = db_channel.ducks_per_day

        day_ducks_count = int(total_ducks_today * 9 / 10)
        night_ducks_count = int(total_ducks_today * 1 / 10)

        # Add missing ducks due to int() conversion to night.
        night_ducks_count += total_ducks_today - day_ducks_count - night_ducks_count

        # The min() here is protecting against having more than a duck every 5 seconds.
        if total_day_seconds:
            self.day_ducks = int(min((day_seconds_left * day_ducks_count) / total_day_seconds, total_day_seconds / 5))
        else:
            # Prevent ZeroDivisionError
            self.day_ducks = 0

        if total_night_seconds:
            self.night_ducks = int(
                min((night_seconds_left * night_ducks_count) / total_night_seconds, total_night_seconds / 5))
        else:
            # Prevent ZeroDivisionError
            self.night_ducks = 0

        return self

    async def maybe_spawn_type(self, now=None) -> typing.Optional[SunState]:
        if not self.db_channel:
            self.db_channel: DiscordChannel = await get_from_db(self.channel)

        db_channel = self.db_channel

        if not now:
            now = int(time.time())

        now = now % DAY

        sun_state = db_channel.day_status(now)

        if sun_state == SunState.DAY:
            if random.randint(0, db_channel.day_seconds_left(now)) < self.day_ducks:
                self.day_ducks -= 1
                return SunState.DAY
        elif sun_state == SunState.NIGHT:
            if random.randint(0, db_channel.night_seconds_left(now)) < self.night_ducks:
                self.night_ducks -= 1
                return SunState.NIGHT
        return None

    @property
    def ducks_left(self):
        return self.night_ducks + self.day_ducks


class DiscordChannel(Model):
    discord_id = fields.BigIntField(pk=True)
    first_seen = fields.DatetimeField(auto_now_add=True)

    guild: fields.ForeignKeyRelation[DiscordGuild] = \
        fields.ForeignKeyField('models.DiscordGuild',
                               related_name="channels")

    players: fields.ReverseRelation["Player"]

    name = fields.TextField()

    webhook_urls = fields.JSONField(default=list)
    api_key = fields.UUIDField(null=True)

    # Generic settings
    use_webhooks = fields.BooleanField(default=True)
    use_emojis = fields.BooleanField(default=True)
    enabled = fields.BooleanField(default=False)

    landmines_commands_enabled = fields.BooleanField(default=False)  # Can members run landmine commands here
    landmines_enabled = fields.BooleanField(default=False)  # Do messages sent here count in the game ?

    anti_trigger_wording = fields.BooleanField(default=False)

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

    levels_to_roles_ids_mapping = fields.JSONField(default=dict)
    prestige_to_roles_ids_mapping = fields.JSONField(default=dict)

    def serialize(self, serialize_fields=None):
        DONT_SERIALIZE = {'guild', 'members', 'playerss', 'webhook_urls', 'api_key'}

        ser = {}

        if serialize_fields is None:
            serialize_fields = self._meta.fields.copy() - DONT_SERIALIZE

        for serialize_field in serialize_fields:
            if serialize_field == "discord_id":
                ser[serialize_field] = str(getattr(self, serialize_field))

            elif isinstance(getattr(self, serialize_field), datetime.datetime):
                ser[serialize_field] = str(getattr(self, serialize_field))

            ser[serialize_field] = getattr(self, serialize_field)

        return ser

    @property
    def night_seconds(self):
        if self.night_start_at == self.night_end_at:
            # Nothing set
            return 0
        elif self.night_start_at < self.night_end_at:
            # Simple case: everything is the same day
            # 16:00            < 23:00
            return self.night_end_at - self.night_start_at
        else:
            # Harder case: night starts in a day and end the next day
            # 21:00            > 06:00
            #       v Time until next day      + v Time left at the start of the day
            return (DAY - self.night_start_at) + self.night_end_at

    def night_seconds_left(self, now=None):
        if now is None:
            now = int(time.time())

        now = now % DAY

        if self.night_start_at == self.night_end_at:
            # Nothing set
            return 0
        elif self.night_start_at < self.night_end_at:
            # Simple case: everything is the same day
            # 16:00            < 23:00
            if self.night_start_at < now <= self.night_end_at:
                # During the night
                return self.night_end_at - now
            elif self.night_end_at < now:
                # After the night
                return 0
            elif now <= self.night_start_at:
                # Before the night
                return self.night_end_at - self.night_start_at
            else:
                # This shouldn't be happening
                raise ArithmeticError(f"Error calculating simpler case in night_seconds_left, debugging follow\n"
                                      f"{now=}, {self.night_start_at=}, {self.night_end_at=}, {self=}")
        else:
            # Harder case: night starts in a day and end the next day
            # 21:00            > 06:00
            #       v Time until next day      + v Time left at the start of the day
            if now <= self.night_end_at:
                # During the first night of the day
                # Seconds left during the first night + seconds in the second night
                return (self.night_end_at - now) + (DAY - self.night_start_at)
            elif self.night_end_at < now <= self.night_start_at:
                # During the day
                return DAY - self.night_start_at
            elif self.night_start_at < now:
                # During the second night, until midnight
                return DAY - now
            else:
                # This shouldn't be happening
                raise ArithmeticError(f"Error calculating harder case in night_seconds_left, debugging follow\n"
                                      f"{now=}, {self.night_start_at=}, {self.night_end_at=}, {self=}")

    def day_status(self, now=None):
        if now is None:
            now = int(time.time())

        now = now % DAY

        if self.night_start_at == self.night_end_at:
            # Nothing set
            return SunState.DAY
        elif self.night_start_at < self.night_end_at:
            # Simple case: everything is the same day
            # 16:00            < 23:00
            if self.night_start_at < now <= self.night_end_at:
                # During the night
                return SunState.NIGHT
            else:
                return SunState.DAY
        else:
            # Harder case: night starts in a day and end the next day
            # 21:00            > 06:00
            if self.night_end_at < now <= self.night_start_at:
                return SunState.DAY
            else:
                return SunState.NIGHT

    def day_seconds_left(self, now=None):
        if now is None:
            now = int(time.time())

        now = now % DAY

        total_seconds_left = DAY - now

        return total_seconds_left - self.night_seconds_left(now)

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


def get_valid_words(message_content) -> typing.List[str]:
    allowed_chars = string.ascii_letters + string.digits + string.whitespace

    cleaned_content = ''.join(filter(lambda character: character in allowed_chars, message_content))

    words = []

    for word in set(cleaned_content.lower().split()):
        if 3 <= len(word) <= 40 and (len(word) > 25 or len(word) < 15 or not set(word).issubset(set(string.digits))):
            words.append(word)

    return words


class LandminesUserData(Model):
    landmines_bought: fields.ReverseRelation['LandminesPlaced']
    landmines_stopped: fields.ReverseRelation['LandminesPlaced']

    # This is waiting for a fix of https://github.com/tortoise/tortoise-orm/issues/822
    member: fields.ForeignKeyRelation["DiscordMember"] = \
        fields.OneToOneField('models.DiscordMember', related_name='landmines', on_delete=fields.CASCADE, db_index=True)

    # General statistics
    first_played = fields.DatetimeField(auto_now_add=True)
    last_seen = fields.DatetimeField(auto_now_add=True)
    messages_sent = fields.IntField(default=0)
    words_sent = fields.IntField(default=0)
    points_won = fields.IntField(default=0)
    points_recovered = fields.IntField(default=0)
    points_acquired = fields.IntField(default=0)
    points_current = fields.IntField(default=0)
    points_exploded = fields.IntField(default=0)
    points_spent = fields.IntField(default=0)

    # Inventory

    ## Defuse kits
    defuse_kits_bought = fields.IntField(default=0)
    shields_bought = fields.IntField(default=0)

    def add_points_for_message(self, message_content):
        words = get_valid_words(message_content)
        words_count = len(words)
        if words_count > 0:
            self.words_sent += words_count
            self.messages_sent += 1
            earned = max(0, int((words_count + random.randint(-1, words_count))))

            if self.points_current <= -10:
                earned *= max(2, int(abs(self.points_current) / 1000) + 2)

            self.points_acquired += earned
            self.points_current += earned
            return True
        else:
            return False

    def __str__(self):
        return f"@{self.member} landmines data"

    class Meta:
        table = 'landmines_userdata'


class LandminesPlaced(Model):
    placed_by = fields.ForeignKeyField('models.LandminesUserData', related_name='landmines_bought', on_delete=fields.CASCADE)

    placed = fields.DatetimeField(auto_now_add=True)
    word = fields.CharField(max_length=50)
    message = fields.CharField(blank=True, default="", max_length=2000)

    value = fields.IntField()
    exploded = fields.IntField(null=True)

    tripped = fields.BooleanField(default=False)
    disarmed = fields.BooleanField(default=False)

    stopped_by = fields.ForeignKeyField('models.LandminesUserData', null=True, blank=True, on_delete=fields.SET_NULL,
                                        related_name='landmines_stopped')
    stopped_at = fields.DatetimeField(null=True)

    def base_value(self) -> int:
        return self.value * len(self.word)

    def value_for(self, db_target: LandminesUserData) -> int:
        base_value = self.base_value()

        current_points = db_target.points_current

        points_left = current_points - base_value

        if points_left < 0:
            beginner_value = base_value + points_left + (-points_left / 4)
        else:
            beginner_value = base_value

        return max(10, int(beginner_value))

    def __str__(self):
        return f"{self.placed_by.member_id} landmine on {self.word} for {self.value}"

    class Meta:
        table = 'landmines_placed'


class LandminesProtects(Model):
    protected_by = fields.ForeignKeyField('models.LandminesUserData', related_name='words_protected', on_delete=fields.CASCADE)
    placed = fields.DatetimeField(auto_now_add=True)
    protect_count = fields.IntField(default=0)
    word = fields.CharField(max_length=50)
    message = fields.CharField(blank=True, default="", max_length=2000)

    def __str__(self):
        return f"{self.protected_by.member} protected word on {self.word}"

    class Meta:
        table = 'landmines_protected'


async def get_word_protect_for(guild, word):
    if not isinstance(guild, DiscordGuild):
        db_guild = await get_from_db(guild)
    else:
        db_guild = guild

    return await LandminesProtects \
        .filter(word=word) \
        .filter(protected_by__member__guild=db_guild) \
        .first()


class UserInventory(Model):
    # There is another bug in tortoise preventing this.
    # But you can't add a primary key on a ForeignKey like you can in django
    # Or you won't be able to save the model
    # So, until they fix https://github.com/tortoise/tortoise-orm/issues/822
    # I'm defining the field as a BigIntField which should hopefully fix the save issues
    # But we will loose all the fk goodness such as prefetching, CASCADING, ...
    # Welp.

    # user: fields.ForeignKeyRelation["DiscordUser"] = \
    #     fields.OneToOneField('models.DiscordUser', related_name='inventory', on_delete=fields.CASCADE, pk=True)

    user_id = fields.BigIntField(pk=True)

    # Boxes
    lootbox_welcome_left = fields.IntField(default=1)
    lootbox_boss_left = fields.IntField(default=0)
    lootbox_vote_left = fields.IntField(default=0)

    # Unobtainable items
    item_vip_card_left = fields.IntField(default=0)

    # Loot
    item_mini_exp_boost_left = fields.IntField(default=0)
    item_norm_exp_boost_left = fields.IntField(default=0)
    item_maxi_exp_boost_left = fields.IntField(default=0)
    item_one_bullet_left = fields.IntField(default=0)
    item_spawn_ducks_left = fields.IntField(default=0)
    item_refill_magazines_left = fields.IntField(default=0)

    def __str__(self):
        return f"{self.user_id} inventory"

    def __repr__(self):
        return f"<Inventory user_id={self.user_id}>"

    class Meta:
        table = 'inventories'


class DiscordUser(Model):
    discord_id = fields.BigIntField(pk=True)
    first_seen = fields.DatetimeField(auto_now_add=True)

    support_tickets: fields.ReverseRelation[SupportTicket]
    closed_tickets: fields.ReverseRelation[SupportTicket]
    # inventory: fields.OneToOneRelation[UserInventory]

    members: fields.ReverseRelation["DiscordMember"]

    votes: fields.ReverseRelation["Vote"]
    tags: fields.ReverseRelation["Tag"]
    tags_aliases: fields.ReverseRelation["TagAlias"]

    name = fields.TextField()
    discriminator = fields.CharField(4)

    trophys = fields.JSONField(default=dict)

    ping_friendly = fields.BooleanField(default=True)

    language = fields.CharField(6, default="en")
    first_use = fields.BooleanField(default=True)

    access_level_override = fields.IntEnumField(enum_type=AccessLevel, default=AccessLevel.DEFAULT)

    boss_kills = fields.IntField(default=0)

    async def get_or_create_support_ticket(self) -> SupportTicket:
        support_ticket: typing.Optional[SupportTicket] = await SupportTicket.filter(user=self, closed=False).first()

        if not support_ticket:
            support_ticket = SupportTicket(user=self)

        return support_ticket

    async def support_ticket_count(self, **filter_kwargs) -> int:
        return await SupportTicket.filter(user=self, **filter_kwargs).count()

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

    channel: fields.ForeignKeyRelation[DiscordChannel] = \
        fields.ForeignKeyField('models.DiscordChannel',
                               related_name="players")
    member: fields.ForeignKeyRelation["DiscordMember"] = \
        fields.ForeignKeyField('models.DiscordMember',
                               related_name="players")

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

    weapon_sabotaged_by: fields.ForeignKeyNullableRelation["Player"] = \
        fields.ForeignKeyField('models.Player',
                               related_name="sabotaged_weapons",
                               null=True,
                               on_delete=fields.SET_NULL
                               )

    sabotaged_weapons: fields.ReverseRelation["Player"]

    # Killed ducks stats
    best_times = DefaultDictJSONField(default_factory=lambda: 660)
    killed = DefaultDictJSONField()
    hugged = DefaultDictJSONField()
    hurted = DefaultDictJSONField()
    resisted = DefaultDictJSONField()
    frightened = DefaultDictJSONField()

    PRESTIGE_SAVED_FIELDS = {'id', 'first_seen', 'channel', 'channel_id', 'member', 'member_id', 'prestige',
                             'prestige_last_daily', 'stored_achievements', 'sabotaged_weapons', 'experience',
                             'givebacks'}

    async def do_prestige(self, bot, kept_exp):
        """
        Reset a player data, persisting his/her ID. What's left to do is.
        """
        self.prestige += 1
        self.experience = kept_exp

        meta = self._meta
        reset_fields_names = meta.fields.copy() - self.PRESTIGE_SAVED_FIELDS

        # Set (almost) everything back to default
        for reset_fields_name in reset_fields_names:
            field_object = meta.fields_map[reset_fields_name]
            default = field_object.default

            if callable(field_object.default):
                setattr(self, reset_fields_name, default())
            else:
                setattr(self, reset_fields_name, default)

        # Fix auto_now_add fields since they don't get back to defaults
        self.prestige_last_daily = timezone.now() - datetime.timedelta(days=1)
        self.last_giveback = timezone.now()

        level_info = self.level_info()
        self.magazines = level_info["magazines"]
        self.bullets = level_info["bullets"]

        await self.change_roles(bot)

    def serialize(self, serialize_fields=None):
        DONT_SERIALIZE = {'weapon_sabotaged_by', 'sabotaged_weapons', 'channel', 'member'}
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
            clover_exp = self.active_powerups['clover_exp']
            if self.get_current_coat_color() == Coats.DARK_GREEN:
                clover_exp += 1
            return clover_exp
        return 0

    def get_current_coat_color(self) -> typing.Optional[Coats]:
        if self.is_powerup_active('coat'):
            color_name = self.active_powerups.get('coat_color', None)
            if color_name:
                return Coats[color_name]
            else:
                # This is for older players that bought a "no_colored" coat.
                return Coats.DEFAULT
        else:
            return None

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

    async def edit_experience_with_levelups(self, ctx, delta, bot=None):
        old_level_info = self.level_info()
        self.experience += delta
        new_level_info = self.level_info()

        if old_level_info['level'] == new_level_info['level']:
            return
        else:
            # Send level up embed.
            guild: discord.Guild = ctx.guild

            if isinstance(ctx, discord.TextChannel):
                db_guild = await get_from_db(guild)
                language_code = db_guild.language

                def _(message):
                    return translate(message, language_code)
            else:
                _ = await ctx.get_translate_function()
                bot = ctx.bot

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
            asyncio.ensure_future(self.change_roles(bot))

    async def change_roles(self, bot):
        new_level_info = self.level_info()
        new_level = new_level_info['level']

        db_member: DiscordMember = await self.member
        db_channel: DiscordChannel = await self.channel
        db_user: DiscordUser = await db_member.user
        guild: discord.Guild = bot.get_guild(db_member.guild_id)
        channel: discord.TextChannel = guild.get_channel(db_channel.discord_id)

        # Now is time to give roles.
        roles_mapping: typing.Dict[str, str] = db_channel.levels_to_roles_ids_mapping
        prestige_mapping: typing.Dict[str, str] = db_channel.prestige_to_roles_ids_mapping
        #             (int-like) level nb, discord role ID

        if not len(roles_mapping) and not len(prestige_mapping):
            # Nothing in there, nothing to do, fast path.
            return
        try:
            member = await guild.fetch_member(db_user.discord_id)
        except discord.NotFound:
            # Member left.
            bot.logger.info(f"Can't edit {db_user.discord_id} roles for level change: user NotFound.", guild=guild,
                            channel=channel)
            return

        managed_ids = list(roles_mapping.values())
        managed_ids.extend(list(prestige_mapping.values()))

        # Remove all managed roles
        member_roles = member.roles
        new_member_roles = [r for r in member_roles if str(r.id) not in managed_ids]
        changed = len(member_roles) != len(new_member_roles)

        level_role = None

        for level_id, role_id in sorted(roles_mapping.items(), key=lambda kv: -int(kv[0])):
            # Top level first
            if int(level_id) <= new_level:
                level_role = guild.get_role(int(role_id))
                if level_role:
                    new_member_roles.append(level_role)
                    changed = True
                    break

        for prestige_id, role_id in sorted(prestige_mapping.items(), key=lambda kv: -int(kv[0])):
            if int(prestige_id) <= self.prestige:
                role = guild.get_role(int(role_id))
                if role:
                    if role != level_role:
                        new_member_roles.append(role)
                    changed = True
                    break

        if changed:
            try:
                bot.logger.info(f"Editing {member.name} ({member.id}) roles for level change.", guild=guild,
                                channel=channel)

                bot.logger.debug(f"Roles transition for {member.id}: {member_roles} -> {new_member_roles}", guild=guild, channel=channel)
                await member.edit(roles=new_member_roles, reason="Level change")
            except discord.Forbidden as e:
                # Can't set the new roles.
                bot.logger.warning(f"Can't set {member.id} roles on {guild.id}: Forbidden - {e}", guild=guild,
                                   channel=channel)
        else:
            bot.logger.debug(f"Not editing {member.name} ({member.id}) roles for level change, no change.", guild=guild,
                             channel=channel)

    def is_powerup_active(self, powerup):
        if self.prestige >= 1 and powerup == "sunglasses":
            return True
        elif self.prestige >= 5 and powerup == "coat":
            return True
        elif self.prestige >= 7 and powerup == "kill_licence":
            return True
        elif powerup in ["coat_color", "clover_exp"]:
            return False
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
    landmines: fields.ReverseRelation['LandminesUserData']

    id = fields.IntField(pk=True)
    guild: fields.ForeignKeyRelation[DiscordGuild] = \
        fields.ForeignKeyField('models.DiscordGuild',
                               related_name="members")
    user: fields.ForeignKeyRelation[DiscordUser] = \
        fields.ForeignKeyField('models.DiscordUser',
                               related_name="members")

    players: fields.ReverseRelation["Player"]

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


class BotList(Model):
    votes: fields.ReverseRelation["Vote"]

    # **Generic Data**
    key = fields.CharField(help_text="The unique key to recognise the bot list",
                           max_length=50,
                           pk=True)

    name = fields.CharField(help_text="Name of the bot list",
                            max_length=128)

    bot_url = fields.TextField(help_text="URL for the main bot page")

    notes = fields.TextField(help_text="Informations about this bot list",
                             blank=True)

    auth = fields.TextField(help_text="Token used to authenticate requests to/from the bot")

    # **Votes**
    can_vote = fields.BooleanField(help_text="Can people vote (more than once) on that list ?",
                                   default=True)

    vote_url = fields.TextField(help_text="URL for an user to vote")

    vote_every = fields.TimeDeltaField(help_text="How often can users vote ?",
                                       null=True)

    check_vote_url = fields.TextField(help_text="URL the bot can use to check if an user voted recently")

    check_vote_key = fields.CharField(help_text="Key in the returned JSON to check for presence of vote",
                                      default="voted",
                                      max_length=128)

    check_vote_negate = fields.BooleanField(
        help_text="Does the boolean says if the user has voted (True) or if they can vote (False) ?",
        default=True)

    webhook_handler = fields.CharField(help_text="What is the function that'll receive the request from the vote hooks",
                                       choices=(("generic", "generic"),
                                                ("top.gg", "top.gg"),
                                                ("None", "None")),
                                       default="generic",
                                       max_length=20)

    webhook_authorization_header = fields.CharField(
        help_text="Name of the header used to authenticate webhooks requests",
        default="Authorization",
        max_length=20)

    webhook_user_id_json_field = fields.CharField(help_text="Key that gives the user ID in the provided JSON",
                                                  default="id",
                                                  max_length=20)

    webhook_auth = fields.TextField(
        help_text="Secret used for authentication of the webhooks messages if not the same the auth token",
        blank=True)

    # **Statistics**

    post_stats_method = fields.CharField(help_text="What HTTP method should be used to send the stats",
                                         choices=(("POST", "POST"),
                                                  ("PATCH", "PATCH"),
                                                  ("None", "None")),
                                         default="POST",
                                         max_length=10)

    post_stats_url = fields.TextField(help_text="Endpoint that will receive statistics")

    post_stats_server_count_key = fields.CharField(help_text="Name of the server count key in the statistics JSON",
                                                   default="server_count",
                                                   blank=True,
                                                   max_length=128)

    post_stats_shard_count_key = fields.CharField(help_text="Name of the shard count key in the statistics JSON",
                                                  default="shard_count",
                                                  blank=True,
                                                  max_length=128)

    # **Others**

    bot_verified = fields.BooleanField(help_text="Whether the bot was verified by the bot list staff",
                                       default=False)

    bot_certified = fields.BooleanField(help_text="Whether the bot was certified on that bot list",
                                        default=False)

    embed_code = fields.TextField(help_text="Code to show this bot list embed. This HTML won't be escaped.",
                                  blank=True)


class Vote(Model):
    user: fields.ForeignKeyRelation[DiscordUser] = \
        fields.ForeignKeyField('models.DiscordUser',
                               related_name="votes")

    bot_list: fields.ForeignKeyRelation[BotList] = \
        fields.ForeignKeyField('models.BotList', related_name="votes")

    at = fields.DatetimeField(auto_now_add=True)
    multiplicator = fields.IntField(default=1)


class Tag(Model):
    owner: fields.ForeignKeyRelation[DiscordUser] = \
        fields.ForeignKeyField('models.DiscordUser',
                               related_name='tags')

    aliases: fields.ReverseRelation["TagAlias"]
    used_in_tickets: fields.ReverseRelation["SupportTicket"]

    # Statistics
    created = fields.DatetimeField(auto_now_add=True)
    last_modified = fields.DatetimeField(auto_now=True)
    uses = fields.IntField(default=0)
    revisions = fields.IntField(default=0)

    # Tag
    official = fields.BooleanField(default=False)
    name = fields.CharField(max_length=90, db_index=True, unique=True)
    content = fields.TextField()

    @property
    def pages(self):
        return [page.strip(" \n") for page in "\n".join(self.content.splitlines()).split('\n\n---')]

    def __str__(self):
        return f"{self.name}"


class TagAlias(Model):
    owner: fields.ForeignKeyRelation[DiscordUser] = \
        fields.ForeignKeyField('models.DiscordUser',
                               related_name='tags_aliases')
    tag: fields.ForeignKeyRelation[Tag] = \
        fields.ForeignKeyField('models.Tag', related_name='aliases')

    uses = fields.IntField(default=0)

    name = fields.CharField(max_length=90, db_index=True, unique=True)

    def __str__(self):
        return f"{self.name} -> {self.tag.name}"


class BotState(Model):
    datetime = fields.DatetimeField(auto_now_add=True)

    measure_interval = fields.IntField()  # The event stats are (usually) based on a 10 minutes interval
    ws_send = fields.IntField()
    ws_recv = fields.IntField()
    messages = fields.IntField()
    commands = fields.IntField()
    command_errors = fields.IntField()
    command_completions = fields.IntField()

    guilds = fields.IntField()
    users = fields.IntField()
    shards = fields.IntField()
    ready = fields.BooleanField()
    ws_ratelimited = fields.BooleanField()
    ws_latency = fields.FloatField()  # miliseconds

    class Meta:
        table = 'botstate'


async def get_tag(name, increment_uses=True) -> typing.Optional[Tag]:
    tag: typing.Optional[Tag] = await Tag.filter(name=name).first()
    if tag:
        if increment_uses:
            tag.uses += 1
            await tag.save()
        return tag
    else:
        # Search for an alias
        alias: typing.Optional[TagAlias] = await TagAlias.filter(name=name).prefetch_related("tag").first()
        if alias:
            tag: Tag = alias.tag
            if increment_uses:
                alias.uses += 1
                tag.uses += 1

                await alias.save()
                await tag.save()
            return tag
        else:
            # No alias and no tag
            return None


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
        elif isinstance(discord_object, discord.TextChannel) or isinstance(discord_object, discord.VoiceChannel):
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
        elif isinstance(discord_object, discord.User) or isinstance(discord_object, discord.ClientUser) or (isinstance(discord_object, discord.Member) and as_user):
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
        elif isinstance(discord_object, discord.Thread):
            return await get_from_db(discord_object.parent)
        else:
            obj_type_name = type(discord_object).__name__
            print(f"Unknown object type passed to get_from_db <type:{obj_type_name}>, <obj:{discord_object}>")


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


async def get_user_inventory(user: typing.Union[DiscordUser, discord.User, discord.Member]) -> UserInventory:
    if not isinstance(user, DiscordUser):
        db_user = await get_from_db(user, as_user=True)
    else:
        db_user = user

    async with DB_LOCKS[(db_user,)]:
        inventory, created = await UserInventory.get_or_create(user_id=db_user.discord_id)

    return inventory


async def get_member_landminesdata(member: typing.Union[DiscordMember, discord.Member]) -> LandminesUserData:
    if not isinstance(member, DiscordMember):
        db_member = await get_from_db(member)
    else:
        db_member = member

    async with DB_LOCKS[(db_member,)]:
        eventdata, created = await LandminesUserData.get_or_create(member_id=db_member.pk)

    return eventdata


async def get_landmine(guild: typing.Union[DiscordGuild, discord.Guild], message_content: str, as_list:bool = False) -> typing.Union[typing.Optional[LandminesPlaced], typing.List[LandminesPlaced]]:
    if not isinstance(guild, DiscordGuild):
        db_guild = await get_from_db(guild)
    else:
        db_guild = guild

    words = get_valid_words(message_content)
    if words:
        qs = LandminesPlaced \
            .filter(tripped=False, disarmed=False) \
            .order_by('placed') \
            .filter(word__in=words) \
            .filter(placed_by__member__guild=db_guild) \

        if as_list:
            return await qs
        else:
            return await qs.first()

    else:
        if as_list:
            return []
        else:
            return None


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
