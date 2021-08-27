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
from utils.concurrency import dont_block
from utils.ctx_class import MyContext
from utils.models import AccessLevel

GIF_STEP = -10
BASE_DURATION = 10
ALLOWED_FORMATS = {"jpeg", "gif", "webp", "png"}


def pad_image_to(image, big_h, big_w, curr_h, curr_w):
    delta_w = big_w - curr_w
    delta_h = big_h - curr_h
    padding = (delta_w // 2, delta_h // 2, delta_w - (delta_w // 2), delta_h - (delta_h // 2))
    return ImageOps.expand(image, padding)


def resize_image_gif(image_bytes, w_pct, h_pct, image_format):
    # Get the PIL Image
    image = Image.open(BytesIO(image_bytes))

    # Resize in case the image is too big
    if image_format == "gif":
        image.thumbnail((750, 750))
    else:
        image.thumbnail((1250, 1250))

    # Get the output buffer
    final_buffer = BytesIO()

    # Get the numpy image
    src = np.array(image)

    # Get the image sizes
    start_h, start_w, _ = src.shape

    # Get the desired sizes
    end_w, end_h = int(start_w * (w_pct/100)), int(start_h * (h_pct/100))

    # The step : positive if growing, negative if not.
    step_h = GIF_STEP if end_h < start_h else - GIF_STEP

    # Find the biggest of the two, for the gif size
    big_h = max(start_h, end_h)

    # Same for width
    step_w = GIF_STEP if end_w < start_w else - GIF_STEP
    big_w = max(start_w, end_w)

    images = [pad_image_to(Image.fromarray(src), big_h, big_w, start_h, start_w)]
    durations = [BASE_DURATION * 5]

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
        durations.append(BASE_DURATION)

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
        durations.append(BASE_DURATION)

    durations[-1] = BASE_DURATION * 15

    images[0].save(final_buffer,
                   format=image_format,
                   save_all=True,
                   append_images=images[1:],
                   duration=BASE_DURATION,
                   loop=0)

    final_buffer.seek(0)
    return final_buffer, start_h, start_w, end_h, end_w


def resize_image(image_bytes, w_pct, h_pct):
    image = Image.open(BytesIO(image_bytes))
    final_buffer = BytesIO()

    src = np.array(image)
    src_h, src_w, _ = src.shape
    dst_h, dst_w = int(src_h * (h_pct/100)), int(src_w * (w_pct/100))

    dst = seam_carving.resize(
        src, (dst_w, dst_h),
        energy_mode='backward',  # Choose from {backward, forward}
        order='width-first',  # Choose from {width-first, height-first}
        keep_mask=None
    )
    dst = Image.fromarray(dst)
    dst.save(final_buffer, "jpeg")

    final_buffer.seek(0)

    return final_buffer, src_h, src_w, dst_h, dst_w


class FunOfTheEyes(Cog):
    hidden = True

    @commands.command(aliases=["resize"])
    @needs_access_level(AccessLevel.BOT_MODERATOR)
    @dont_block
    async def carve(self, ctx: MyContext, who: Optional[discord.User] = None,
                    width_pct: int = 50, height_pct: int = 50, image_format: str = "jpeg"):
        """
        Content-aware carving of an image/avatar, resizing it to reduce the width and height,
        loosing as few details as we can.

        With seam carving algorithm, the image could be intelligently resized while keeping the important contents
        undistorted. The carving process could be further guided, so that an object could be removed from the image
        without apparent artifacts.

        This function only handle normal resizing, without masks.

        The command arguments work as follow :
        - The first argument is optional and can be a mention/user ID of someone to use their avatar.
          If it's not supplied, the bot will look for an attached image.
        - The next two arguments are the width and the height percentages to keep. They must both be > 0, but can also
          go higher than 100 if you want to upscale the image

        - The image format argument can be any of
          • jpeg, for a still image
          • gif, for an animated resizing. Limited quality
          • png for an APNG (Animated PNG - discord doesn't support them well and will only show the first frame,
            open in browser)
          • webp for an animated WebP, a new-ish format that discord doesn't support at all. Try opening those in your
            browser
        """
        if width_pct <= 0 or height_pct <= 0:
            await ctx.send("❌ Please use positive integers for width and height.")
            return
        if image_format not in ALLOWED_FORMATS:
            await ctx.send(f"❌ Please use a format in {ALLOWED_FORMATS}.")
            return

        status_message = await ctx.send("<a:typing:597589448607399949> Downloading image...")
        async with ctx.typing():
            start = time.perf_counter()

            for attachment in ctx.message.attachments:
                if attachment.content_type.startswith('image/'):
                    image_bytes = await attachment.read()
                    break
            else:
                if who:
                    image_bytes = await who.display_avatar.replace(format="jpg", size=512).read()
                else:
                    image_bytes = await ctx.author.display_avatar.replace(format="jpg", size=512).read()

            end_dl = time.perf_counter()
            dl_time = round(end_dl - start, 1)

            await status_message.edit(content=f"✅ Downloading image... {dl_time}s\n"
                                              f"<a:typing:597589448607399949> Processing image...")

            if image_format in {"gif", "webp", "png"}:
                fn = partial(resize_image_gif, image_bytes, width_pct, height_pct, image_format)
            else:
                fn = partial(resize_image, image_bytes, width_pct, height_pct)

            final_buffer, src_h, src_w, dst_h, dst_w = await self.bot.loop.run_in_executor(None, fn)

            end_processing = time.perf_counter()
            processing_time = round(end_processing-end_dl, 1)

            await status_message.edit(content=f"✅ Downloading image... {dl_time}s\n"
                                              f"✅ Processing image... {processing_time}s "
                                              f"({src_w} x {src_h} -> {dst_w} x {dst_h})\n", )

            # prepare the file
            file = discord.File(filename="seam_carving." + image_format, fp=final_buffer)

            # send it
            await ctx.reply(file=file)


setup = FunOfTheEyes.setup
