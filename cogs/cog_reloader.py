# coding=utf-8
"""
Reloads cogs, as a nice way to quickly change code without restarting the bot
Doesn't let itself be reloaded by default to protect itself from breaking (config.toml to change)
"""
from discord.ext import commands

from utils.cog_class import Cog
from utils.ctx_class import MyContext
from utils.bot_class import MyBot


class CogReloader(Cog):
    @commands.command(hidden=True)
    async def reload(self, ctx: MyContext, *extensions):
        """
        Reload any given extension, or reload all with reload all
        """
        _ = await ctx.get_translate_function()

        all_extensions = self.config()["cogs_to_load"]
        msgs = []
        if len(extensions) == 0:
            str_ext = "\n".join(all_extensions)
            await ctx.send(_(f"List of extensions: ```\n{str_ext}```"))
            return
        if extensions[0] == "all":
            extensions = all_extensions
            msgs.append(_("Reloading all extensions!"))
        for ext in extensions:
            if ext in self.disable_reload_for:
                msgs.append(_(f"Can't reload `{ext}`!"))
                continue
            try:
                self.bot.reload_extension(ext)
            except Exception as e:
                msgs.append(_(f"Error while reloading extension {ext}: "
                              f"```{type(e).__name__}\n{str(e)}```"))
            else:
                msgs.append(_(f"Sucessfully reloaded `{ext}`!"))
        await ctx.send("\n".join(msgs))

    def setup(self, bot: MyBot):
        super().setup(bot)
        # noinspection PyAttributeOutsideInit
        self.disable_reload_for = self.config()["disable_reload_for"]


setup = CogReloader.setup
