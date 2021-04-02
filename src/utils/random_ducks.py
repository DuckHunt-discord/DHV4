import pathlib
import random
from functools import partial
from io import BytesIO

import discord
from PIL import Image
from utils.config import load_config

config = load_config()['random_ducks']
random_ducks_assets = pathlib.Path(config['assets_path'])

assert random_ducks_assets.exists()


def get_random_asset_from_directory(directory_name) -> Image.Image:
    directory = random_ducks_assets / directory_name

    assert directory.exists() and directory.is_dir()

    file_path = random.choice(list(directory.glob("*.png")))

    return Image.open(file_path).convert("RGBA")


def create_random_duck(with_background=True) -> Image.Image:
    if with_background:
        image = get_random_asset_from_directory('Background')
        image.alpha_composite(get_random_asset_from_directory(config['composite_order'][0]))
    else:
        image = get_random_asset_from_directory(config['composite_order'][0])

    for directory_name in config['composite_order'][1:]:
        image.alpha_composite(get_random_asset_from_directory(directory_name))

    return image


def get_random_duck_bytes(with_background=True):
    image = create_random_duck(with_background)

    # prepare the stream to save this image into
    buffer = BytesIO()

    # save into the stream, using png format.
    image.save(buffer, "png")
    buffer.seek(0)
    return buffer


async def get_random_duck_file(bot, with_background=True):
    fn = partial(get_random_duck_bytes, with_background)

    buffer = await bot.loop.run_in_executor(None, fn)
    file = discord.File(filename="random_duck.png", fp=buffer)

    return file

if __name__ == '__main__':
    im = create_random_duck()
    im.show()

