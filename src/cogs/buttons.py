from discord.ext import commands

from utils.bot_class import MyBot
from utils.cog_class import Cog

from utils.views import init_all_persistant_command_views

SECOND = 1
MINUTE = 60 * SECOND
HOUR = 60 * MINUTE
DAY = 24 * HOUR


class Buttons(Cog):
    hidden = True

    def __init__(self, bot: MyBot, *args, **kwargs):
        super().__init__(bot, *args, **kwargs)
        self.persistent_views_added = False

    @Cog.listener()
    async def on_ready(self):
        if not self.persistent_views_added:
            # Register the persistent view for listening here.
            # Note that this does not send the view to any message.
            # In order to do this you need to first send a message with the View, which is shown below.
            # If you have the message_id you can also pass it as a keyword argument, but for this example
            # we don't have one.
            self.bot.logger.debug("Loading persistant views...")
            await init_all_persistant_command_views(self.bot)
            self.bot.logger.info("Command persistant views loaded")

            self.persistent_views_added = True


setup = Buttons.setup
