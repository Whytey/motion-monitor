import logging
from collections import OrderedDict
from io import BytesIO

from PIL import Image as PILImage

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


def convert_image(frame, img_format: str, scale: float) -> bytes:
    """Given an image file at a path, will return the bytes of that file.  If provided, will also scale
    the size of the image and convert to the required format.
    """

    path = frame.filename

    with open(path, "rb") as image_file:
        im = PILImage.open(image_file)
        converted_img = BytesIO()
        if scale:
            _LOGGER.debug("Scaling the image")
            (width, height) = (int(im.width * scale), int(im.height * scale))
            _LOGGER.debug("Original size is {}wx{}h, new size is {}wx{}h".format(im.width, im.height, width, height))
            im = im.resize([width, height])
        im.save(converted_img, img_format)
        file_bytes = converted_img.getvalue()
        return file_bytes
