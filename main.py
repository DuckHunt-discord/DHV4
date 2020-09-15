import asyncio
import uvloop

from utils.config import load_config
from utils.bot_class import MyBot
from utils.models import init_db_connection

asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

config = load_config()

if config['database']['enable']:
    asyncio.ensure_future(init_db_connection(config['database']))

bot = MyBot(description=config["bot"]["description"])

for cog_name in config["cogs"]["cog_reloader"]["cogs_to_load"]:
    try:
        bot.load_extension(cog_name)
        bot.logger.debug(f"> {cog_name} loaded!")
    except Exception as e:
        bot.logger.exception('> Failed to load extension {}\n{}: {}'.format(cog_name, type(e).__name__, e))

bot.run(config['auth']['discord']['token'])
