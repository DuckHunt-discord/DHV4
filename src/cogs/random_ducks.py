import datetime
from functools import partial
from io import BytesIO

import discord
from discord.ext import commands
from utils.cog_class import Cog
from utils.ctx_class import MyContext
from utils.random_ducks import create_random_duck


class RandomDucks(Cog):

    @staticmethod
    def get_random_duck_bytes(with_background=True):
        image = create_random_duck(with_background)

        # prepare the stream to save this image into
        buffer = BytesIO()

        # save into the stream, using png format.
        image.save(buffer, "png")
        buffer.seek(0)
        return buffer

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
            fn = partial(self.get_random_duck_bytes, with_background)

            buffer = await self.bot.loop.run_in_executor(None, fn)
            file = discord.File(filename="random_duck.png", fp=buffer)

            await ctx.send(file=file)

setup = RandomDucks.setup
