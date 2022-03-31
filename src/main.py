import asyncio

import discord
import uvloop

from utils.bot_class import MyBot
from utils.config import load_config

asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

config = load_config()

# https://discordpy.readthedocs.io/en/latest/api.html#discord.Intents
intents = discord.Intents.none()
intents.message_content = True  # Privileged
intents.messages = True
intents.guilds = True
intents.reactions = True

intents.members = False  # Privileged
intents.presences = False  # Privileged
intents.bans = False
intents.emojis = False
intents.integrations = False
intents.webhooks = False
intents.invites = False
intents.voice_states = False
intents.typing = False

# https://discordpy.readthedocs.io/en/latest/api.html#discord.AllowedMentions
allowed_mentions = discord.AllowedMentions(
    everyone=False,
    roles=False,
    users=True,
)

bot = MyBot(
    description=config["bot"]["description"],
    intents=intents,
    allowed_mentions=allowed_mentions,
    enable_debug_events=False,
    chunk_guilds_at_startup=False,
)


async def main():
    async with bot:
        await bot.start(config['auth']['discord']['token'])


asyncio.run(main())
