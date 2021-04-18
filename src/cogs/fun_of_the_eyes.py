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
from PIL import Image, ImageOps
import discord
from discord.ext import commands

from utils.checks import needs_access_level
from utils.cog_class import Cog
from utils.ctx_class import MyContext
from utils.models import AccessLevel

GIF_STEP = -10


class TooSmall(Exception):
    def __init__(self, src_h, src_w, dst_h, dst_w):
        self.src_h = src_h
        self.src_w = src_w
        self.dst_h = dst_h
        self.dst_w = dst_w


def pad_image_to(image, big_h, big_w, curr_h, curr_w):
    delta_w = big_w - curr_w
    delta_h = big_h - curr_h
    padding = (delta_w // 2, delta_h // 2, delta_w - (delta_w // 2), delta_h - (delta_h // 2))
    return ImageOps.expand(image, padding)


def resize_image_gif(image_bytes, w_pct, h_pct):
    # Get the PIL Image
    image = Image.open(BytesIO(image_bytes))

    # Get the output buffer
    final_buffer = BytesIO()

    # Get the numpy image
    src = np.array(image)

    # Get the image sizes
    src_h, src_w, _ = src.shape

    # Get the desired sizes
    dst_h, dst_w = int(src_w * (w_pct/100)), int(src_h * (h_pct/100))

    if dst_h <= 0 or dst_w <= 0:
        raise TooSmall(src_h, src_w, dst_h, dst_w)

    # Get the starting size
    start_h = src_h

    # The ending size
    end_h = src_h - dst_h

    # The step : positive if growing, negative if not.
    step_h = GIF_STEP if end_h < start_h else - GIF_STEP

    # Find the biggest of the two, for the gif size
    big_h = max(start_h, end_h)

    # Same for width
    start_w = src_w
    end_w = dst_w
    step_w = GIF_STEP if end_w < start_w else - GIF_STEP
    big_w = max(start_w, end_w)

    images = [pad_image_to(Image.fromarray(src), big_h, big_w, src_h, src_w)]

    # Resize height
    for curr_h in range(start_h, end_h, step_h):
        # Width not yet resized
        curr_w = start_w

        src = seam_carving.resize(
            src, (curr_w, curr_h),
            energy_mode='backward',  # Choose from {backward, forward}
            order='width-first',  # Choose from {width-first, height-first}
            keep_mask=None
        )

        images.append(pad_image_to(Image.fromarray(src), big_h, big_w, curr_h, curr_w))

    # Resize width

    # The height is resized now
    curr_h = end_h
    for curr_w in range(start_w, end_w, step_w):
        src = seam_carving.resize(
            src, (curr_w, curr_h),
            energy_mode='backward',  # Choose from {backward, forward}
            order='width-first',  # Choose from {width-first, height-first}
            keep_mask=None
        )

        images.append(pad_image_to(Image.fromarray(src), big_h, big_w, curr_h, curr_w))

    images[0].save(final_buffer,
                   format='gif',
                   save_all=True,
                   append_images=images[1:],
                   duration=10,
                   loop=0)

    final_buffer.seek(0)
    return final_buffer, src_h, src_w


def resize_image(image_bytes, w_pct, h_pct):
    image = Image.open(BytesIO(image_bytes))
    final_buffer = BytesIO()

    src = np.array(image)
    src_h, src_w, _ = src.shape
    dst_h, dst_w = int(src_w * (w_pct/100)), int(src_h * (w_pct/100))

    if dst_h <= 0 or dst_w <= 0:
        raise TooSmall(src_h, src_w, dst_h, dst_w)

    dst = seam_carving.resize(
        src, (dst_w, dst_h),
        energy_mode='backward',  # Choose from {backward, forward}
        order='width-first',  # Choose from {width-first, height-first}
        keep_mask=None
    )
    dst = Image.fromarray(dst)
    dst.save(final_buffer, "jpeg")

    final_buffer.seek(0)

    return final_buffer, src_h, src_w


class FunOfTheEyes(Cog):
    @commands.command()
    @needs_access_level(AccessLevel.BOT_MODERATOR)
    async def carve(self, ctx: MyContext, who: Optional[discord.User] = None,
                    width_pct: int = 50, height_pct: int = 50, make_gif: bool = False):
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
                    image_bytes = await who.avatar_url_as(format="jpg", size=512).read()
                else:
                    image_bytes = await ctx.author.avatar_url_as(format="jpg", size=512).read()

            end_dl = time.perf_counter()
            dl_time = round(end_dl - start, 1)

            await status_message.edit(content=f"✅ Downloading image... {dl_time}s\n"
                                              f"<a:typing:597589448607399949> Processing image...")

            if make_gif:
                fn = partial(resize_image_gif, image_bytes, width_pct, height_pct)
            else:
                fn = partial(resize_image, image_bytes, width_pct, height_pct)

            try:
                final_buffer, src_h, src_w = await self.bot.loop.run_in_executor(None, fn)
            except TooSmall as ts:
                await status_message.edit(content=f"✅ Downloading image... {dl_time}s\n"
                                                  f"❌ Processing image... Dimensions too small "
                                                  f"(source: {ts.src_w} x {ts.src_h}, dest: {ts.dst_w} x {ts.dst_h})\n")
                return

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
