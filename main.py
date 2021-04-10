# coding=utf-8
import asyncio

import discord
import uvloop

from utils.bot_class import MyBot
from utils.config import load_config
from utils.custom_help import EmbedHelpCommand
from utils.models import init_db_connection

asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

config = load_config()

if config['database']['enable']:
    asyncio.ensure_future(init_db_connection(config['database']))

# https://discordpy.readthedocs.io/en/latest/api.html#discord.Intents
intents = discord.Intents.none()
intents.guilds =       True
intents.messages =     True
intents.reactions =    True
intents.presences =    False  # Privileged
intents.members =      False  # Privileged
intents.bans =         False
intents.emojis =       False
intents.integrations = False
intents.webhooks =     False
intents.invites =      False
intents.voice_states = False
intents.typing =       False

# https://discordpy.readthedocs.io/en/latest/api.html#discord.AllowedMentions
allowed_mentions = discord.AllowedMentions(
    everyone=False,
    roles=False,
    users=True,
)

bot = MyBot(description=config["bot"]["description"], intents=intents, allowed_mentions=allowed_mentions,
            help_command=EmbedHelpCommand())

for cog_name in config["cogs"]["cogs_to_load"]:
    try:
        bot.load_extension(cog_name)
        bot.logger.debug(f"> {cog_name} loaded!")
    except Exception as e:
        bot.logger.exception('> Failed to load extension {}\n{}: {}'.format(cog_name, type(e).__name__, e))

bot.run(config['auth']['discord']['token'])
