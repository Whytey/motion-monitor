import json
import logging

from aiohttp import web
from playhouse.db_url import connect

from motionmonitor.const import EVENT_MOTION_EVENT_START, EVENT_NEW_FRAME, EVENT_NEW_MOTION_FRAME
from motionmonitor.extensions.api import BaseAPIView
from motionmonitor.extensions.recorder import models
from motionmonitor.extensions.recorder.models import Event, Frame, EventFrame

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
        database.create_tables([models.Event, models.Frame, models.EventFrame], safe=True)

        # Listen for the events we care about
        self.mm.bus.listen(EVENT_MOTION_EVENT_START, self._handle_motion_start)
        self.mm.bus.listen(EVENT_NEW_FRAME, self._handle_snapshot_frame)
        self.mm.bus.listen(EVENT_NEW_MOTION_FRAME, self._handle_motion_frame)

        # Add the API endpoints that the Recorder provides (/events, /snapshots, /database)
        self.mm.api.register_view(APISnapshotsView)

    def _handle_motion_start(self, event):
        native_event = event.data
        _LOGGER.debug("Inserting a motion event: {}".format(native_event))
        Event.from_native(native_event).save()

    def _handle_snapshot_frame(self, event):
        native_frame = event.data
        _LOGGER.debug("Inserting a snapshot frame: {}".format(native_frame))
        Frame.from_native(native_frame).save()

    def _handle_motion_frame(self, event):
        native_frame = event.data
        _LOGGER.debug("Inserting a event frame: {}".format(native_frame))
        EventFrame.from_native(native_frame).save()


class APIEventsView:
    pass


class APISnapshotsView(BaseAPIView):
    url = "/snapshots"
    name = "api:snapshot-frames"
    description = "Lists all snapshot frames in the database.  Recommend filtering by cameraId, dates or pagination " \
                  "is applied."

    async def get(self, request):
        response = {"frames": []}
        for frame in Frame.select():
            response["frames"].append(frame.to_native().to_json())
        return web.Response(text=json.dumps(response), content_type='application/json')


class APIDatabaseView:
    pass
