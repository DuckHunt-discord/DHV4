import toml
from discord.ext import commands

from utils.bot_class import MyBot
from utils.checks import server_admin_or_permission


class Cog(commands.Cog):
    def __init__(self, bot: MyBot, *args, **kwargs):
        self.bot = bot
        super().__init__(*args, **kwargs)

    @classmethod
    def setup(cls, bot: MyBot):
        return bot.add_cog(cls(bot))

    def config(self):
        config = self.bot.config
        cog_config = config["cogs"].get(self.qualified_name, {})
        return cog_config

    async def cog_check(self, ctx):
        command = ctx.command
        cog = command.cog
        if len(command.checks) == 0:
            permission_name = f"{cog.qualified_name}.{command.name}"
            my_check = server_admin_or_permission(permission_name).predicate
            ret = super().cog_check(ctx)
            ret = ret and await my_check(ctx)
            return ret
        else:
            return super().cog_check(ctx)
