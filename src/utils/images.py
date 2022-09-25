from random import choice
from pathlib import Path

from discord import File


IMAGE_EXTS = ["*.png", "*.jpg", "*.jpeg", "*.gif"]

all_images = []
for ext in IMAGE_EXTS:
    all_images.extend(Path("assets/Random").rglob(ext))


def get_random_image() -> File:
    image_path = choice(all_images)
    f = File(str(image_path), filename=image_path.name)

    return f

