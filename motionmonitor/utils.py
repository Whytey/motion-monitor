import logging
from collections import OrderedDict
from io import BytesIO

from PIL import Image

_LOGGER = logging.getLogger(__name__)


class FixedSizeOrderedDict(OrderedDict):
    # A specialisation of OrderedDict that enforces a max size, similar to deque
    def __init__(self, *args, max=0, **kwargs):
        self._max = max
        super().__init__(*args, **kwargs)

    def __setitem__(self, key, value):
        OrderedDict.__setitem__(self, key, value)
        if self._max > 0:
            if len(self) > self._max:
                self.popitem(False)


def animate_frames(frames: [], scale=None) -> bytes:
    _LOGGER.debug("Have {} frames to animate.".format(len(frames)))
    images = []
    for frame in frames:
        _LOGGER.debug("Working through {}".format(frame))
        path = frame.filename

        with open(path, "rb") as image_file:
            im = Image.open(image_file)
            im.load()
            (width, height) = (im.width, im.height)
            if scale:
                (width, height) = (int(im.width * scale), int(im.height * scale))
                _LOGGER.debug("Original size is {}wx{}h, new size is {}wx{}h".format(im.width, im.height,
                                                                                     width, height))
                im = im.resize([width, height])
            images.append(im)
    animated_img = BytesIO()
    im = Image.new('RGB', (width, height))
    im.save(animated_img, format="GIF", save_all=True, append_images=images, optimize=False, duration=10, loop=0)
    return animated_img.getvalue()


def convert_frames(frame, img_format: str, scale=None) -> bytes:
    """Given an Frame object, will return the bytes of that Frame's file.  If provided, will also scale
    the size of the image and convert to the required format.
    """

    path = frame.filename

    with open(path, "rb") as image_file:
        im = Image.open(image_file)
        converted_img = BytesIO()
        if scale:
            _LOGGER.debug("Scaling the image")
            (width, height) = (int(im.width * scale), int(im.height * scale))
            _LOGGER.debug("Original size is {}wx{}h, new size is {}wx{}h".format(im.width, im.height, width, height))
            im = im.resize([width, height])
        im.save(converted_img, img_format)
        return converted_img.getvalue()


def stringify_dict(d: dict) -> dict:
    """Given a dictionary, converts both the keys and values of it to string and returns it."""
    return {str(key): str(value) for key, value in d.items()}


def lower_camel_casify_dict_keys(d: dict) -> dict:
    """Given a dictionary, changes the key from snake case to lower camel case."""
    return {to_camel_case(key): value for key, value in d.items()}


def to_camel_case(snake_str: str) -> str:
    components = snake_str.split('_')
    # We capitalize the first letter of each component except the first one
    # with the 'title' method and join them together.
    return components[0] + ''.join(x.title() for x in components[1:])
