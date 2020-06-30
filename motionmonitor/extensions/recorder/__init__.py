import json
import logging
from datetime import datetime

from aiohttp import web
from playhouse.db_url import connect

from motionmonitor.const import EVENT_MOTION_EVENT_START, EVENT_NEW_FRAME, EVENT_NEW_MOTION_FRAME
from motionmonitor.extensions.api import BaseAPIView, APIImageView
from motionmonitor.extensions.recorder import models
from motionmonitor.extensions.recorder.models import Event, Frame, EventFrame

_LOGGER = logging.getLogger(__name__)


def get_extension(mm):
    return [Recorder(mm)]


class Recorder:
    """An extension to record data to a database.  Backend database URL is provided in the configuration
    and could be any database supported by the Peewee ORM.  API endpoints are added to the API extension that
    support the retrieving of the database data.

    This extension is somewhat inspired by the Recorder component of Home-Assistant
    - https://www.home-assistant.io/integrations/recorder
    """

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
        self.mm.api.register_view(APISnapshotFrameView)

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


class APISnapshotFrameView(APIImageView):
    url = "/snapshots/{camera_id}/{timestamp}/{frame}"
    name = "api:snapshot-frame"
    description = "Returns the snapshot frame for the specified camera_id, timestamp and frame"

    async def get(self, request):
        camera_id = request.match_info['camera_id']
        timestamp = datetime.strptime(request.match_info['timestamp'], "%Y%m%d%H%M%S")
        frame_num = request.match_info['frame']

        frame = Frame.get(Frame.camera_id == camera_id,
                          Frame.timestamp == timestamp,
                          Frame.frame == frame_num)

        frame_params = {
            "camera_id": frame.camera_id,
            "timestamp": frame.timestamp.strftime("%Y%m%d%H%M%S"),
            "frame": frame.frame
        }

        return self._create_response(request, frame, frame_params, self)


class APISnapshotsView(BaseAPIView):
    url = "/snapshots"
    name = "api:snapshot-frames"
    description = "Lists all snapshot frames in the database.  Recommend filtering by cameraId, dates or pagination " \
                  "is applied."

    async def get(self, request):
        response = self.to_entity_repr(request, classes=["snapshots"])
        for frame in Frame.select():
            response["entities"].append(APISnapshotFrameView.to_entity_repr(request,
                                                                          classes=["snapshot"],
                                                                          rel=["item"],
                                                                          path_params={
                                                                              "camera_id": frame.camera_id,
                                                                              "timestamp": frame.timestamp.strftime("%Y%m%d%H%M%S"),
                                                                              "frame": frame.frame}))

        return web.Response(text=json.dumps(response), content_type='application/json')


class APIDatabaseView:
    pass
