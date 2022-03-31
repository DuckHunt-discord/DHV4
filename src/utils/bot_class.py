import collections
import datetime
import typing
from typing import Optional

import aiohttp
import discord
from discord import Guild
from discord.ext import commands
from discord.ext.commands import MaxConcurrency, BucketType
from discord.ext.commands.bot import AutoShardedBot
from tortoise import timezone

from utils import config as config
from utils.ctx_class import MyContext
from utils.events import Events
from utils.logger import FakeLogger
from utils.models import get_from_db, AccessLevel, init_db_connection, DucksLeft

if typing.TYPE_CHECKING:
    # Prevent circular imports
    from utils.ducks import Duck


class MyBot(AutoShardedBot):
    def __init__(self, *args, **kwargs):
        self.logger = FakeLogger()
        self.logger.debug("Running sync init")
        self.config: dict = {}
        self.reload_config()
        # activity = discord.Game(self.config["bot"]["playing"])
        self.current_event: Events = Events.CALM
        activity = discord.Game(self.current_event.value[0])
        super().__init__(*args, command_prefix=get_prefix, activity=activity,
                         case_insensitive=self.config["bot"]["commands_are_case_insensitive"], **kwargs)
        self.commands_used = collections.Counter()
        self.top_users = collections.Counter()
        self.uptime = timezone.now()
        self.shards_ready = set()
        self.socket_stats = collections.Counter()
        self._client_session: Optional[aiohttp.ClientSession] = None
        self.ducks_spawned: collections.defaultdict[
            discord.TextChannel, collections.deque['Duck']] = collections.defaultdict(collections.deque)
        self.enabled_channels: typing.Dict[discord.TextChannel, DucksLeft] = {}
        self.concurrency = MaxConcurrency(number=1, per=BucketType.channel, wait=True)
        self.allow_ducks_spawning = True

        self._duckhunt_public_log = None

        self.logger.debug("End of init, bot object is ready")

    @property
    def client_session(self):
        if self._client_session:
            return self._client_session
        else:
            raise RuntimeError("The bot haven't been setup yet. Ensure you call bot.async_setup asap.")

    @property
    def available_guilds(self) -> typing.Iterable[Guild]:
        return filter(lambda g: not g.unavailable, self.guilds)

    def reload_config(self):
        self.config = config.load_config()

    async def setup_hook(self):
        """
        This function is run once, and is used to setup the bot async features, like the ClientSession from aiohttp.
        """
        self.logger.debug("Running async init")

        self._client_session = aiohttp.ClientSession()  # There is no need to call __aenter__, since that does nothing in that case

        if self.config['database']['enable']:
            await init_db_connection(self.config['database'])

        for cog_name in self.config["cogs"]["cogs_to_load"]:
            try:
                await self.load_extension(cog_name)
                self.logger.debug(f"> {cog_name} loaded!")
            except Exception as e:
                self.logger.exception('> Failed to load extension {}\n{}: {}'.format(cog_name, type(e).__name__, e))

    def get_logging_channel(self):
        if not self._duckhunt_public_log:
            config = self.config['duckhunt_public_log']
            self._duckhunt_public_log = self.get_guild(config['server_id']).get_channel(config['channel_id'])

        return self._duckhunt_public_log

    async def log_to_channel(self, *args, **kwargs):
        channel = self.get_logging_channel()
        message = await channel.send(*args, **kwargs)
        try:
            await message.publish()
            return True
        except discord.Forbidden:
            self.logger.warning(
                "Couldn't publish message to announcement channel, I don't have the required permissions")
            return False
        except discord.HTTPException as e:
            self.logger.exception(f"Couldn't publish message to announcement channel: {e}. "
                                  f"Too many messages published recently ?")
            return False

    async def on_socket_event_type(self, event_type):
        self.socket_stats[event_type] += 1

    async def on_message(self, message):
        if not self.is_ready():
            return  # Ignoring messages when not ready

        if message.author.bot:
            return  # ignore messages from other bots

        ctx = await self.get_context(message, cls=MyContext)
        if ctx.prefix is not None:
            db_user = await get_from_db(ctx.author)

            access = db_user.get_access_level()

            if access != AccessLevel.BANNED:
                if ctx.command:
                    callback = ctx.command.callback
                else:
                    callback = None
                if callback:
                    should_block = getattr(ctx.command.callback, "block_concurrency", True)
                else:
                    should_block = True

                if should_block:
                    await self.concurrency.acquire(message)

                await self.invoke(ctx)

                if should_block:
                    await self.concurrency.release(message)

    async def on_command(self, ctx: MyContext):
        db_user = await get_from_db(ctx.author, as_user=True)
        if db_user.first_use and "help" not in ctx.command.name:
            _ = await ctx.get_translate_function(user_language=True)

            ctx.logger.info(
                f"It's the first time that {ctx.author.name}#{ctx.author.discriminator} is intreracting with us. Sending welcome DM.")
            try:
                await ctx.author.send(
                    _("Hello! The following message (written by the owner of DuckHunt) will give you a brief introduction to the bot, "
                      "and also provide you with links to the DuckHunt wiki.\n"
                      "First of all, thank you for using my bot! If you have any unanswered questions after reading this message and the wiki, "
                      "you are more than welcome to ask for help in the support channels at <{support_server_link}>.\n\n"
                      "When a duck spawns you shoot at it by using the `dh!bang` command.\n"
                      "You can reload your ammunition with `dh!reload` and buy new magazines with `dh!shop magazine` or `dh!shop 2`.\n"
                      "Your scores and channel leaderboards are available online (click the title in `dh!me` after playing for a while), and on Discord."
                      "If you want to learn more about the game, use the wiki! <{wiki_link}>\n"
                      "We also monitor the bot DMs, so if you have further questions, just answer this message!",
                      support_server_link=_("https://duckhunt.me/support"),
                      wiki_link=_("https://duckhunt.me/docs/players-guide/players-quickstart"),
                      ))
            except discord.Forbidden:
                ctx.logger.debug(
                    f"Couldn't send the welcome DM, forbidden.")

            db_user.first_use = False
            await db_user.save()

        self.commands_used[ctx.command.qualified_name] += 1
        self.top_users[ctx.author.id] += 1
        ctx.logger.info(f"{ctx.message.clean_content}")

    async def on_interaction(self, interaction: discord.Interaction):
        data = interaction.data
        self.logger.info(f"Interaction received: {data}", guild=interaction.guild, channel=interaction.channel,
                         member=interaction.user, )

    async def on_shard_ready(self, shard_id):
        self.shards_ready.add(shard_id)

    async def on_disconnect(self):
        self.shards_ready = set()

    async def on_ready(self):
        messages = ["-----------", f"The bot is ready.", f"Logged in as {self.user.name} ({self.user.id})."]
        total_members = len(self.users)
        messages.append(f"I see {len(self.guilds)} guilds, and {total_members} members.")
        messages.append(
            f"To invite your bot to your server, use the following link: https://discord.com/oauth2/authorize?client_id=187636051135823872&scope=bot&permissions=741735489")
        cogs_count = len(self.cogs)
        messages.append(f"{cogs_count} cogs are loaded")
        messages.append("-----------")
        for message in messages:
            self.logger.info(message)


async def get_prefix(bot: MyBot, message: discord.Message):
    forced_prefixes = bot.config["bot"]["prefixes"]

    if not message.guild:
        # Need no prefix when in DMs
        return commands.when_mentioned_or(*forced_prefixes, "")(bot, message)

    else:
        if bot.config["database"]["enable"]:
            db_guild = await get_from_db(message.guild)
            guild_prefix = db_guild.prefix
            if guild_prefix:
                forced_prefixes = [guild_prefix] + forced_prefixes

        return commands.when_mentioned_or(*forced_prefixes)(bot, message)
