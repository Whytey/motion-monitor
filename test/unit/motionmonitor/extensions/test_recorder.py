import asyncio
import base64
import unittest
from datetime import datetime
from unittest import mock
from unittest.mock import Mock, ANY

import peewee as pw
from aiohttp.test_utils import make_mocked_request
from aiohttp.web_exceptions import HTTPBadRequest, HTTPNotImplemented

import motionmonitor
from motionmonitor.const import KEY_MM
from motionmonitor.core import EventBus
from motionmonitor.extensions.recorder import Recorder, APISnapshotsView, APISnapshotFrameView, APIEventsView, \
    APIEventEntityView, APIEventFrameView
from motionmonitor.extensions.recorder import models as db_models
from test.unit.motionmonitor.extensions.test_api import TestAPIBase

CAMERA_ID = 1
EVENT_ID = "202006011200-1"


class RecorderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.mm = Mock()
        self.mm.config = {"RECORDER": {"URL": "sqlite:///:memory:"}}
        self.mm.bus = EventBus(self.mm)
        self.mm.loop = asyncio.new_event_loop()
        recorder = Recorder(self.mm)

        self.mm.loop.run_until_complete(recorder.start_extension())

    def test_get_extension(self):
        from motionmonitor.extensions.recorder import get_extension
        extensions = get_extension(self.mm)
        self.assertEqual(1, len(extensions))
        self.assertIsInstance(extensions[0], Recorder)

    def test_handle_event(self):
        event = motionmonitor.models.Event("EVENTID", "CAMERAID", datetime.now())
        self.mm.bus.fire(motionmonitor.const.EVENT_MOTION_EVENT_START, event)

        # Check we now have a row in the Events table.
        self.assertEqual(1, db_models.Event.select().count())

    def test_handle_snapshot_frame(self):
        frame = motionmonitor.models.Frame("CAMERAID", datetime.now(), 0, "filename.jpg")
        self.mm.bus.fire(motionmonitor.const.EVENT_NEW_FRAME, frame)

        # Check we now have a row in the Events table.
        self.assertEqual(1, db_models.Frame.select().count())

    def test_handle_motion_frame(self):
        frame = motionmonitor.models.EventFrame("CAMERAID", "EVENTID", datetime.now(), 0, "filename.jpg", 100)
        self.mm.bus.fire(motionmonitor.const.EVENT_NEW_MOTION_FRAME, frame)

        # Check we now have a row in the Events table.
        self.assertEqual(1, db_models.EventFrame.select().count())


class RecorderAPISnapshotsViewTests(TestAPIBase):
    def setUp(self) -> None:
        super().setUp()

        # Setup the database
        sqlite_mem = pw.SqliteDatabase(":memory:")
        db_models.proxy.initialize(sqlite_mem)
        sqlite_mem.create_tables([db_models.Frame], safe=False)

        self.request = make_mocked_request("GET", APISnapshotsView.url)
        self.request.app[KEY_MM] = self.mm

    def test_get_no_snapshots(self):
        response = self.loop.run_until_complete(APISnapshotsView().get(self.request))
        json_data = self.is_valid_json(response)
        self.assertEqual(0, len(json_data["entities"]))

    def test_get_one_snapshot(self):
        now = datetime.now()
        filename = "filename.jpg"
        f = db_models.Frame(camera_id=CAMERA_ID, timestamp=now, frame=0, filename=filename)
        f.save()

        response = self.loop.run_until_complete(APISnapshotsView().get(self.request))
        json_data = self.is_valid_json(response)
        self.assertEqual(1, len(json_data["entities"]))


class RecorderAPISnapshotFrameViewTests(TestAPIBase):
    timestamp = "20200601120000"
    frame_num = 2
    mocked_bytes = b'12345'

    def setUp(self) -> None:
        super().setUp()

        # Setup the database
        sqlite_mem = pw.SqliteDatabase(":memory:")
        db_models.proxy.initialize(sqlite_mem)
        sqlite_mem.create_tables([db_models.Frame], safe=False)

        self.request = make_mocked_request("GET", APISnapshotFrameView.url, match_info={"camera_id": CAMERA_ID,
                                                                                        "timestamp": self.timestamp,
                                                                                        "frame": self.frame_num})
        self.request.app[KEY_MM] = self.mm

    def test_get_not_exists(self):
        with self.assertRaises(HTTPBadRequest):
            self.loop.run_until_complete(APISnapshotFrameView().get(self.request))

    @mock.patch('motionmonitor.extensions.api.convert_frames')
    def test_get_one_snapshot(self, mock_convert_frames):
        mock_convert_frames.return_value = self.mocked_bytes

        now = datetime.strptime(self.timestamp, "%Y%m%d%H%M%S")
        filename = "filename.jpg"
        f = db_models.Frame(camera_id=CAMERA_ID, timestamp=now, frame=self.frame_num, filename=filename)
        f.save()

        response = self.loop.run_until_complete(APISnapshotFrameView().get(self.request))
        json_data = self.is_valid_json(response)

        # The convert will have been called with defaults; JPEG and None
        mock_convert_frames.assert_called_with(ANY, "JPEG", None)

        # Confirm the properties of the JSON response
        self.assertEqual(CAMERA_ID, json_data["properties"]["cameraId"])
        self.assertEqual(self.timestamp, json_data["properties"]["timestamp"])
        self.assertEqual(self.frame_num, json_data["properties"]["frame"])
        self.assertEqual(base64.b64encode(self.mocked_bytes).decode('ascii'), json_data["properties"]["jpegBytes"])


class RecorderAPIEventsViewTests(TestAPIBase):
    def setUp(self) -> None:
        super().setUp()

        # Setup the database
        sqlite_mem = pw.SqliteDatabase(":memory:")
        db_models.proxy.initialize(sqlite_mem)
        sqlite_mem.create_tables([db_models.Event], safe=False)

        self.request = make_mocked_request("GET", APIEventsView.url)
        self.request.app[KEY_MM] = self.mm

    def test_get_no_events(self):
        response = self.loop.run_until_complete(APIEventsView().get(self.request))
        json_data = self.is_valid_json(response)
        self.assertEqual(0, len(json_data["entities"]))

    def test_get_one_event(self):
        now = datetime.now()

        e = db_models.Event(event_id=EVENT_ID, camera_id=CAMERA_ID, start_time=now)
        e.save()

        response = self.loop.run_until_complete(APIEventsView().get(self.request))
        json_data = self.is_valid_json(response)
        self.assertEqual(1, len(json_data["entities"]))


class RecorderAPIEventEntityViewTests(TestAPIBase):
    def setUp(self) -> None:
        super().setUp()

        # Setup the database
        sqlite_mem = pw.SqliteDatabase(":memory:")
        db_models.proxy.initialize(sqlite_mem)
        sqlite_mem.create_tables([db_models.Event, db_models.EventFrame], safe=False)

        self.request = make_mocked_request("GET", APIEventEntityView.url, match_info={"event_id": EVENT_ID})
        self.request.app[KEY_MM] = self.mm

    def test_get_not_exists(self):
        with self.assertRaises(HTTPBadRequest):
            self.loop.run_until_complete(APIEventEntityView().get(self.request))

    def test_get_event_no_frames(self):
        now = datetime.now()

        e = db_models.Event(event_id=EVENT_ID, camera_id=CAMERA_ID, start_time=now)
        e.save()

        response = self.loop.run_until_complete(APIEventEntityView().get(self.request))
        json_data = self.is_valid_json(response)
        self.assertEqual(0, len(json_data["entities"]))

        # Check the properties of the event
        self.assertEqual(CAMERA_ID, json_data["properties"]["cameraId"])
        self.assertEqual(EVENT_ID, json_data["properties"]["eventId"])
        self.assertEqual(now.strftime("%Y%m%d%H%M%S"), json_data["properties"]["startTime"])

    def test_get_event_one_frames(self):
        now = datetime.now()
        frame_num = 1
        score = 100
        filename = "filename.jpg"

        e = db_models.Event(event_id=EVENT_ID, camera_id=CAMERA_ID, start_time=now)
        e.save()

        f = db_models.EventFrame(event_id=EVENT_ID, camera_id=CAMERA_ID, timestamp=now, frame=frame_num, score=score,
                                 filename=filename)
        f.save()

        response = self.loop.run_until_complete(APIEventEntityView().get(self.request))
        json_data = self.is_valid_json(response)
        self.assertEqual(2, len(json_data["entities"]))

    def test_delete(self):
        with self.assertRaises(HTTPNotImplemented):
            self.loop.run_until_complete(APIEventEntityView().delete(self.request))


class RecorderAPIEventFrameViewTests(TestAPIBase):
    timestamp = "20200601120000"
    frame_num = 2
    mocked_bytes = b'12345'

    def setUp(self) -> None:
        super().setUp()

        # Setup the database
        sqlite_mem = pw.SqliteDatabase(":memory:")
        db_models.proxy.initialize(sqlite_mem)
        sqlite_mem.create_tables([db_models.Event, db_models.EventFrame], safe=False)

        self.request = make_mocked_request("GET", APIEventFrameView.url, match_info={"event_id": EVENT_ID,
                                                                                     "timestamp": self.timestamp,
                                                                                     "frame": self.frame_num})
        self.request.app[KEY_MM] = self.mm

    def test_get_not_exists(self):
        with self.assertRaises(HTTPBadRequest):
            self.loop.run_until_complete(APIEventFrameView().get(self.request))

    @mock.patch('motionmonitor.extensions.api.convert_frames')
    def test_get_one_snapshot(self, mock_convert_frames):
        mock_convert_frames.return_value = self.mocked_bytes

        now = datetime.strptime(self.timestamp, "%Y%m%d%H%M%S")
        filename = "filename.jpg"
        f = db_models.EventFrame(camera_id=CAMERA_ID, event_id=EVENT_ID, timestamp=now, frame=self.frame_num, filename=filename)
        f.save()

        response = self.loop.run_until_complete(APIEventFrameView().get(self.request))
        json_data = self.is_valid_json(response)

        # The convert will have been called with defaults; JPEG and None
        mock_convert_frames.assert_called_with(ANY, "JPEG", None)

        # Confirm the properties of the JSON response
        self.assertEqual(CAMERA_ID, json_data["properties"]["cameraId"])
        self.assertEqual(self.timestamp, json_data["properties"]["timestamp"])
        self.assertEqual(self.frame_num, json_data["properties"]["frame"])
        self.assertEqual(base64.b64encode(self.mocked_bytes).decode('ascii'), json_data["properties"]["jpegBytes"])

    def test_delete(self):
        with self.assertRaises(HTTPNotImplemented):
            self.loop.run_until_complete(APIEventFrameView().delete(self.request))


if __name__ == '__main__':
    unittest.main()
