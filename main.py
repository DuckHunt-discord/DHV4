import asyncio
import uvloop

from utils.config import load_config
from utils.bot_class import MyBot

asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

config = load_config()

bot = MyBot(description=config["bot"]["description"])

for cog_name in config["cogs"]["cogs_to_load"]:
    try:
        bot.load_extension(cog_name)
        bot.logger.debug(f"> {cog_name} loaded!")
    except Exception as e:
        bot.logger.exception('> Failed to load extension {}\n{}: {}'.format(cog_name, type(e).__name__, e))

bot.run(config['auth']['discord']['token'])
