import random
from pathlib import Path

import discord

IMAGE_EXTS = ["*.png", "*.jpg", "*.jpeg", "*.gif"]

all_images = []
for ext in IMAGE_EXTS:
    all_images.extend(Path("assets/Random").rglob(ext))


def get_random_image() -> discord.File:
    image_path = random.choice(all_images)
    f = discord.File(str(image_path), filename=image_path.name)

    return f

