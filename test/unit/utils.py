import os
from pathlib import Path

from PIL import Image, ImageDraw


def create_image_file(target_filename):
    img = Image.new('RGB', (640, 480), color=(73, 109, 137))
    d = ImageDraw.Draw(img)
    d.text((18, 18), target_filename, fill=(255, 255, 0))
    print(target_filename)
    target_dir = os.path.dirname(target_filename)

    Path(target_dir).mkdir(parents=True, exist_ok=True)

    img.save(target_filename)
