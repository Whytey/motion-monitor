import logging

_LOGGER = logging.getLogger(__name__)


def get_extension(mm):
    return [Recorder(mm)]


class Recorder:
    def __init__(self, mm):
        self.mm = mm

    async def start_extension(self):
        pass
