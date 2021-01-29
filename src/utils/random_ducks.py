import pathlib
import random
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


if __name__ == '__main__':
    im = create_random_duck()
    im.show()

