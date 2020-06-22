import logging

from playhouse.db_url import connect

from .models import Event
from motionmonitor.const import EVENT_MOTION_EVENT_START, EVENT_MOTION_EVENT_END, EVENT_NEW_FRAME, \
    EVENT_NEW_MOTION_FRAME
from motionmonitor.extensions.recorder import models

_LOGGER = logging.getLogger(__name__)


def get_extension(mm):
    return [Recorder(mm)]


class Recorder:
    def __init__(self, mm):
        self.mm = mm
        self.__db_url = mm.config["RECORDER"]["URL"]

    async def start_extension(self):
        # Connect to the database and associate it with the models
        database = connect(self.__db_url)
        models.proxy.initialize(database)
        database.create_tables([models.Event], safe=True)


        # Listen for the events we care about
        self.mm.bus.listen(EVENT_MOTION_EVENT_START, self.handle_motion_start)
        # self.mm.bus.listen(EVENT_MOTION_EVENT_END, self.handle_motion_end)
        # self.mm.bus.listen(EVENT_NEW_FRAME, self.handle_snapshot_frame)
        # self.mm.bus.listen(EVENT_NEW_MOTION_FRAME, self.handle_motion_frame)

        # Add the API endpoints that the Recorder provides (/events, /snapshots, /database)
        None #@todo

    def handle_motion_start(self, event):
        native_event = event.data
        _LOGGER.debug("Handling start of motion event: {}".format(native_event))
        e = Event.from_native(native_event)
