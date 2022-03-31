from discord.ext import commands

from utils.bot_class import MyBot


class Cog(commands.Cog):
    hidden = False
    help_priority = 10
    help_color = 'gray'

    display_name = None

    @property
    def name(self):
        return self.display_name or self.qualified_name or type(self).__name__

    def __init__(self, bot: MyBot, *args, **kwargs):
        self.bot = bot
        super().__init__(*args, **kwargs)

    @classmethod
    async def setup(cls, bot: MyBot):
        return await bot.add_cog(cls(bot))

    def config(self):
        config = self.bot.config
        cog_config = config["cogs"].get(self.qualified_name, {})
        return cog_config
