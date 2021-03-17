from discord.ext import commands
from utils.cog_class import Cog
from utils.ctx_class import MyContext
from utils.random_ducks import get_random_duck_file


class RandomDucks(Cog):
    @commands.command(aliases=["rd"])
    async def random_duck(self, ctx: MyContext, with_background=True):
        """
        Shows a random duck image, courtesy of Globloxmen assets.
        This is mostly used to debug the random duck functions,
        and uses the same pipeline as for the random duck avatars.

        You can specify if you want a background or not for your random duck, and it defaults to yes.
        """
        async with ctx.typing():
            _ = await ctx.get_translate_function()
            file = await get_random_duck_file(self.bot, with_background)

            await ctx.send(file=file)


setup = RandomDucks.setup
