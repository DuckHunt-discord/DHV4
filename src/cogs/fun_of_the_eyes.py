"""
Some commands for the bot owner.
Testing in progress, please keep the lights off.
"""
import time
from functools import partial

import numpy as np
from io import BytesIO
from typing import Optional

import seam_carving
from PIL import Image
import discord
from discord.ext import commands

from utils.checks import needs_access_level
from utils.cog_class import Cog
from utils.ctx_class import MyContext
from utils.models import AccessLevel

GIF_STEP = -10

def resize_image(image_bytes, reduce_width, reduce_height, make_gif=False):
    image = Image.open(BytesIO(image_bytes),)
    final_buffer = BytesIO()

    src = np.array(image)
    src_h, src_w, _ = src.shape

    dst_h, dst_w = src_w - reduce_width, src_h - reduce_height

    assert dst_h > 0
    assert dst_w > 0

    if not make_gif:
        dst = seam_carving.resize(
            src, (dst_w, dst_h),
            energy_mode='backward',  # Choose from {backward, forward}
            order='width-first',  # Choose from {width-first, height-first}
            keep_mask=None
        )
        dst = Image.fromarray(dst)
        dst.save(final_buffer, "jpeg")

    else:
        images = [Image.fromarray(src)]
        for dst_h in range(src_h, src_h - reduce_height, GIF_STEP):
            src = seam_carving.resize(
                src, (src_w, dst_h),
                energy_mode='backward',  # Choose from {backward, forward}
                order='width-first',  # Choose from {width-first, height-first}
                keep_mask=None
            )
            images.append(Image.fromarray(src))

        for dst_w in range(src_w, src_w - reduce_width, GIF_STEP):
            src = seam_carving.resize(
                src, (dst_w, src_h - reduce_height),
                energy_mode='backward',  # Choose from {backward, forward}
                order='width-first',  # Choose from {width-first, height-first}
                keep_mask=None
            )
            images.append(Image.fromarray(src))

        images[0].save(final_buffer,
                       format='gif',
                       save_all=True,
                       append_images=images[1:],
                       duration=10,
                       loop=0)

    final_buffer.seek(0)

    return final_buffer, src_h, src_w


class FunOfTheEyes(Cog):
    @commands.command()
    @needs_access_level(AccessLevel.BOT_MODERATOR)
    async def carve(self, ctx: MyContext, who: Optional[discord.User] = None,
                    reduce_width: int = 200, reduce_height: int = 200, make_gif: bool = False):
        """
        Content-aware carving of an image/avatar, resizing it to reduce the width and height, loosing as few details as we can.
        """
        status_message = await ctx.send("<a:typing:597589448607399949> Downloading image...")
        async with ctx.typing():
            start = time.perf_counter()

            for attachment in ctx.message.attachments:
                if attachment.content_type.startswith('image/'):
                    image_bytes = await attachment.read()
                    break
            else:
                if who:
                    image_bytes = await who.avatar_url_as(format="jpg", size=4096).read()
                else:
                    image_bytes = await ctx.author.avatar_url_as(format="jpg", size=4096).read()

            end_dl = time.perf_counter()
            dl_time = round(end_dl - start, 1)

            await status_message.edit(content=f"✅ Downloading image... {dl_time}s\n"
                                              f"<a:typing:597589448607399949> Processing image...")

            fn = partial(resize_image, image_bytes, reduce_width, reduce_height, make_gif)
            final_buffer, src_h, src_w = await self.bot.loop.run_in_executor(None, fn)

            end_processing = time.perf_counter()
            processing_time = round(end_processing-end_dl, 1)

            await status_message.edit(content=f"✅ Downloading image... {dl_time}s\n"
                                              f"✅ Processing image... {processing_time}s ({src_w}px x {src_h}px)\n", )

            # prepare the file
            if make_gif:
                file = discord.File(filename="seam_carving.gif", fp=final_buffer)
            else:
                file = discord.File(filename="seam_carving.jpg", fp=final_buffer)

            # send it
            await ctx.send(file=file)


setup = FunOfTheEyes.setup
