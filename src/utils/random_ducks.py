import pathlib
import random
from functools import partial
from io import BytesIO
from typing import Tuple, List

import discord
from PIL import Image

from utils.config import load_config

config = load_config()['random_ducks']
random_ducks_assets = pathlib.Path(config['assets_path'])

assert random_ducks_assets.exists()


def get_random_file_from_directory(directory) -> pathlib.Path:
    assert directory.exists(), f"Directory {directory} does not exist"
    assert directory.is_dir(), f"{directory} is not a directory"

    file_path = random.choice(list(directory.glob("*.png")))

    return file_path


def create_random_duck(artist, with_background=True) -> tuple[Image, list[tuple[str, str]]]:
    base_directory = random_ducks_assets / artist
    image_gen = None
    debug = []
    for subdirectory in sorted(base_directory.iterdir(), key=lambda fd: fd.name):
        if subdirectory.is_dir() and subdirectory.name[:3].isdigit():
            if not with_background and subdirectory.name[:3] == "000":
                continue

            new_path = get_random_file_from_directory(subdirectory)
            debug.append((subdirectory.name, new_path.name))

            new_image = Image.open(new_path).convert("RGBA")
            if image_gen is None:
                image_gen = new_image
            else:
                image_gen = Image.alpha_composite(image_gen, new_image)

    assert image_gen is not None, "No image was created"

    return image_gen, debug


def get_random_duck_bytes(artist, with_background=True):
    image, debug = create_random_duck(artist, with_background)

    # prepare the stream to save this image into
    buffer = BytesIO()

    # save into the stream, using png format.
    image.save(buffer, "png")
    buffer.seek(0)
    return buffer, debug


async def get_random_duck_file(bot, artist="Calgeka", with_background=True):
    fn = partial(get_random_duck_bytes, artist, with_background)

    buffer, debug = await bot.loop.run_in_executor(None, fn)
    file = discord.File(filename="random_duck.png", fp=buffer)

    return file, debug


