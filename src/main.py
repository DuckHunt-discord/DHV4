import asyncio

import discord
import uvloop

from utils.bot_class import MyBot
from utils.config import load_config

asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())


async def main():
    config = load_config()

    # https://discordpy.readthedocs.io/en/latest/api.html#discord.Intents
    intents = discord.Intents.none()
    intents.guilds = True
    intents.messages = True
    intents.reactions = True

    intents.presences = False  # Privileged
    intents.members = False  # Privileged
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

    async with bot:
        await bot.async_setup()

        for cog_name in config["cogs"]["cogs_to_load"]:
            try:
                await bot.load_extension(cog_name)
                bot.logger.debug(f"> {cog_name} loaded!")
            except Exception as e:
                bot.logger.exception('> Failed to load extension {}\n{}: {}'.format(cog_name, type(e).__name__, e))

        await bot.start(config['auth']['discord']['token'])


asyncio.run(main())
