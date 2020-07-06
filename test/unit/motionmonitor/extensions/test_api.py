import asyncio
import base64
import json
import logging
import unittest
from collections import OrderedDict
from datetime import datetime
from unittest import mock
from unittest.mock import Mock, ANY

import aiohttp
import jsonschema
from aiohttp.test_utils import make_mocked_request

from motionmonitor.const import KEY_MM
from motionmonitor.core import Job
from motionmonitor.extensions.api import API, APICameraSnapshotFramesView, APICamerasView, APICameraEntityView, \
    APICameraSnapshotFrameView, APICameraSnapshotTimelapseView, APICameraEventsView, APICameraEventsTimelapseView, \
    APICameraEventEntityView, APICameraEventFramesView, APICameraEventFrameView, APICameraEventTimelapseView, \
    APIJobsView, APIJobEntityView, APIRootView
from motionmonitor.extensions.api.schema import JSONSCHEMA
from motionmonitor.models import Camera, Frame, EventFrame, Event

CAMERA_ID = 1
EVENT_ID = "202006011200-1"


class TestAPIBase(unittest.TestCase):
    def setUp(self) -> None:
        logger = logging.getLogger('motionmonitor')
        logger.setLevel(logging.getLevelName("DEBUG"))
        console_handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        logger.debug("Logger configured")
        self.logger = logger

        self.loop = asyncio.new_event_loop()
        self.mm = Mock()
        self.mm.loop = self.loop
        self.mm.cameras = {}
        self.mm.jobs = OrderedDict()

    def add_camera(self, camera_id: str):
        c = Camera(camera_id)
        self.mm.cameras[camera_id] = c
        return c

    def add_frames(self, count: int, camera_id=CAMERA_ID, timestamp=datetime.now().strftime("%Y%m%d%H%M%S"),
                   frame_num=None):
        added_frames = []
        for i in range(count):
            f = Frame(camera_id, datetime.strptime(timestamp, "%Y%m%d%H%M%S"), frame_num if frame_num else i,
                      "{}.jpeg".format(i))
            self.mm.cameras[camera_id].append_snapshot_frame(f)
            added_frames.append(f)
        return added_frames

    def add_motion_event(self, camera, event_id=EVENT_ID,
                         start_time=datetime.now().strftime("%Y%m%d%H%M%S")):
        e = Event(event_id, camera.id, datetime.strptime(start_time, "%Y%m%d%H%M%S"))
        camera.recent_motion[event_id] = e
        return e

    def add_motion_frames(self, count: int, camera_id=CAMERA_ID, event_id=EVENT_ID,
                          timestamp=datetime.now().strftime("%Y%m%d%H%M%S"),
                          frame_num=None, score=0):
        added_frames = []
        for i in range(count):
            f = EventFrame(camera_id, event_id, datetime.strptime(timestamp, "%Y%m%d%H%M%S"),
                           frame_num if frame_num else i,
                           "{}.jpeg".format(i), score)
            self.mm.cameras[camera_id].recent_motion[event_id].append_frame(f)
            added_frames.append(f)
        return added_frames

    def is_valid_json(self, response):
        self.assertEqual(200, response.status)
        self.assertEqual("application/json", response.content_type)
        json_data = json.loads(response.body)
        jsonschema.validate(json_data, schema=JSONSCHEMA)
        return json_data

    def is_valid_gif(self, response):
        self.assertEqual(200, response.status)
        self.assertEqual("image/gif", response.content_type.lower())
        return response.body

    def is_valid_mjpeg(self, response):
        self.assertEqual(200, response.status)
        print(response.content_type)
        self.assertTrue(response.content_type.startswith("multipart/x-mixed-replace"))


class TestAPIServer(TestAPIBase):
    def setUp(self) -> None:
        super().setUp()
        self.config = {"API": {"ADDRESS": "127.0.0.1", "PORT": "9999"}}
        self.mm.config = self.config

    def test_simple(self):
        api = API(self.mm)
        self.loop.run_until_complete(api.start_extension())

        # If the API has been started, it should be an attribute of the mm instance.
        self.assertEqual(api, self.mm.api)


class TestAPIRootView(TestAPIBase):
    def setUp(self) -> None:
        super().setUp()
        self.request = make_mocked_request("GET", APIRootView.url)
        self.request.app[KEY_MM] = self.mm

    def test_get_no_routes(self):
        response = self.loop.run_until_complete(APIRootView().get(self.request))
        json_data = self.is_valid_json(response)
        self.assertEqual(0, len(json_data["entities"]))

    def test_get_one_route(self):
        self.request.app.router.add_route("GET", APIRootView.url, APIRootView.get, name=APIRootView.name)
        response = self.loop.run_until_complete(APIRootView().get(self.request))
        json_data = self.is_valid_json(response)
        self.assertEqual(0, len(json_data["entities"]))


class TestAPICamerasView(TestAPIBase):
    def setUp(self) -> None:
        super().setUp()
        self.request = make_mocked_request("GET", APICamerasView.url)
        self.request.app[KEY_MM] = self.mm

    def test_get_no_cameras(self):
        response = self.loop.run_until_complete(APICamerasView().get(self.request))
        json_data = self.is_valid_json(response)
        self.assertEqual(0, len(json_data["entities"]))

    def test_get_one_camera(self):
        self.add_camera(CAMERA_ID)
        response = self.loop.run_until_complete(APICamerasView().get(self.request))
        json_data = self.is_valid_json(response)
        self.assertEqual(1, len(json_data["entities"]))


class TestAPICameraEntityView(TestAPIBase):
    def setUp(self) -> None:
        super().setUp()
        self.request = make_mocked_request("GET", APICameraEntityView.url, match_info={"camera_id": CAMERA_ID})
        self.request.app[KEY_MM] = self.mm

    def test_get_no_cameras(self):
        with self.assertRaises(aiohttp.web_exceptions.HTTPBadRequest):
            self.loop.run_until_complete(APICameraEntityView().get(self.request))

    def test_get_one_camera(self):
        self.add_camera(CAMERA_ID)
        response = self.loop.run_until_complete(APICameraEntityView().get(self.request))
        json_data = self.is_valid_json(response)
        self.assertEqual(CAMERA_ID, json_data["properties"]["cameraId"])

        # No frames added yet, should have snapshots and motion entities only.
        self.assertEqual(2, len(json_data["entities"]))

        # Check the properties of the camera
        self.assertEqual(CAMERA_ID, json_data["properties"]["cameraId"])
        self.assertEqual(0, json_data["properties"]["state"])

    def test_get_one_camera_with_frames(self):
        self.add_camera(CAMERA_ID)
        frames = self.add_frames(1, CAMERA_ID)
        response = self.loop.run_until_complete(APICameraEntityView().get(self.request))
        json_data = self.is_valid_json(response)

        # Should also have a last-snapshot entity now, too.
        self.assertEqual(3, len(json_data["entities"]))


class TestAPICameraSnapshotFramesView(TestAPIBase):
    def setUp(self) -> None:
        super().setUp()
        self.request = make_mocked_request("GET", APICameraSnapshotFramesView.url, match_info={"camera_id": CAMERA_ID})
        self.request.app[KEY_MM] = self.mm

    def test_get_no_cameras(self):
        with self.assertRaises(aiohttp.web_exceptions.HTTPBadRequest):
            self.loop.run_until_complete(APICameraSnapshotFramesView().get(self.request))

    def test_get_no_snapshots(self):
        self.add_camera(CAMERA_ID)
        response = self.loop.run_until_complete(APICameraSnapshotFramesView().get(self.request))

        json_data = self.is_valid_json(response)
        self.assertEqual(0, len(json_data["entities"]))

    def test_single_snapshot(self):
        self.add_camera(CAMERA_ID)
        frames = self.add_frames(1, CAMERA_ID)

        response = self.loop.run_until_complete(APICameraSnapshotFramesView().get(self.request))

        json_data = self.is_valid_json(response)
        self.assertEqual(1, len(json_data["entities"]))


class TestAPICameraSnapshotFrameView(TestAPIBase):
    timestamp = "20200601120000"
    frame_num = 1
    mocked_bytes = b'12345'

    def setUp(self) -> None:
        super().setUp()
        self.request = make_mocked_request("GET", APICameraSnapshotFrameView.url, match_info={"camera_id": CAMERA_ID,
                                                                                              "timestamp": self.timestamp,
                                                                                              "frame": self.frame_num})
        self.request.app[KEY_MM] = self.mm

    def test_get_no_cameras(self):
        with self.assertRaises(aiohttp.web_exceptions.HTTPBadRequest):
            self.loop.run_until_complete(APICameraSnapshotFrameView().get(self.request))

    def test_get_no_snapshots(self):
        self.add_camera(CAMERA_ID)
        with self.assertRaises(aiohttp.web_exceptions.HTTPBadRequest):
            self.loop.run_until_complete(APICameraSnapshotFrameView().get(self.request))

    @mock.patch('motionmonitor.extensions.api.convert_frames')
    def test_get_snapshot_as_json(self, mock_convert_frames):
        mock_convert_frames.return_value = self.mocked_bytes
        self.add_camera(CAMERA_ID)
        self.add_frames(1, CAMERA_ID, self.timestamp, self.frame_num)
        response = self.loop.run_until_complete(APICameraSnapshotFrameView().get(self.request))
        json_data = self.is_valid_json(response)

        # The convert will have been called with defaults; JPEG and None
        mock_convert_frames.assert_called_with(ANY, "JPEG", None)

        # Confirm the properties of the JSON response
        self.assertEqual(CAMERA_ID, json_data["properties"]["cameraId"])
        self.assertEqual(self.timestamp, json_data["properties"]["timestamp"])
        self.assertEqual(self.frame_num, json_data["properties"]["frame"])
        self.assertEqual(base64.b64encode(self.mocked_bytes).decode('ascii'), json_data["properties"]["jpegBytes"])

    @mock.patch('motionmonitor.extensions.api.convert_frames')
    def test_get_snapshot_as_scaled_gif(self, mock_convert_frames):
        mock_convert_frames.return_value = self.mocked_bytes
        self.add_camera(CAMERA_ID)
        self.add_frames(1, CAMERA_ID, self.timestamp, self.frame_num)

        # Configure the URL query string
        self.request = make_mocked_request("GET", APICameraSnapshotFrameView.url + "?format=GIF&scale=0.5",
                                           match_info={"camera_id": CAMERA_ID,
                                                       "timestamp": self.timestamp,
                                                       "frame": self.frame_num})
        self.request.app[KEY_MM] = self.mm

        response = self.loop.run_until_complete(APICameraSnapshotFrameView().get(self.request))
        image_bytes = self.is_valid_gif(response)

        self.assertEqual(self.mocked_bytes, image_bytes)

        # The convert will have been called with defaults; GIF and 0.5
        mock_convert_frames.assert_called_with(ANY, "GIF", 0.5)

    @mock.patch('motionmonitor.extensions.api.convert_frames')
    def test_get_snapshot_invalid_format(self, mock_convert_frames):
        mock_convert_frames.return_value = self.mocked_bytes
        self.add_camera(CAMERA_ID)
        self.add_frames(1, CAMERA_ID, self.timestamp, self.frame_num)

        # Configure the URL query string
        self.request = make_mocked_request("GET", APICameraSnapshotFrameView.url + "?format=BAD_FORMAT&scale=0.5",
                                           match_info={"camera_id": CAMERA_ID,
                                                       "timestamp": self.timestamp,
                                                       "frame": self.frame_num})
        self.request.app[KEY_MM] = self.mm

        response = self.loop.run_until_complete(APICameraSnapshotFrameView().get(self.request))
        self.assertEqual(400, response.status)

    @mock.patch('motionmonitor.extensions.api.convert_frames')
    def test_get_snapshot_invalid_scale(self, mock_convert_frames):
        mock_convert_frames.return_value = self.mocked_bytes
        self.add_camera(CAMERA_ID)
        self.add_frames(1, CAMERA_ID, self.timestamp, self.frame_num)

        # Configure the URL query string
        self.request = make_mocked_request("GET", APICameraSnapshotFrameView.url + "?&scale=SMALL",
                                           match_info={"camera_id": CAMERA_ID,
                                                       "timestamp": self.timestamp,
                                                       "frame": self.frame_num})
        self.request.app[KEY_MM] = self.mm
        with self.assertRaises(aiohttp.web_exceptions.HTTPBadRequest):
            response = self.loop.run_until_complete(APICameraSnapshotFrameView().get(self.request))

    def test_delete(self):
        with self.assertRaises(aiohttp.web_exceptions.HTTPNotImplemented):
            response = self.loop.run_until_complete(APICameraSnapshotFrameView().delete(self.request))


class TestAPICameraSnapshotTimelapseView(TestAPIBase):
    mocked_bytes = b'12345'

    def setUp(self) -> None:
        super().setUp()
        self.request = make_mocked_request("GET", APICameraSnapshotTimelapseView.url,
                                           match_info={"camera_id": CAMERA_ID})
        self.request.app[KEY_MM] = self.mm

    def test_get_no_cameras(self):
        with self.assertRaises(aiohttp.web_exceptions.HTTPBadRequest):
            self.loop.run_until_complete(APICameraSnapshotTimelapseView().get(self.request))

    @mock.patch('motionmonitor.extensions.api.animate_frames')
    def test_get_timelapse_default(self, mock_animate_frames):
        mock_animate_frames.return_value = self.mocked_bytes
        self.add_camera(CAMERA_ID)
        self.add_frames(1, CAMERA_ID)

        response = self.loop.run_until_complete(APICameraSnapshotTimelapseView().get(self.request))
        image_bytes = self.is_valid_gif(response)

        self.assertEqual(self.mocked_bytes, image_bytes)

        # The animate will have been called with defaults; None
        mock_animate_frames.assert_called_with(ANY, None)

    @mock.patch('motionmonitor.extensions.api.convert_frames')
    def test_get_timelapse_as_scaled_mjpeg(self, mock_convert_frames):
        mock_convert_frames.return_value = self.mocked_bytes
        self.add_camera(CAMERA_ID)
        self.add_frames(1, CAMERA_ID)

        self.request = make_mocked_request("GET", APICameraSnapshotTimelapseView.url + "?format=mjpeg&scale=0.5",
                                           match_info={"camera_id": CAMERA_ID})
        self.request.app[KEY_MM] = self.mm

        response = self.loop.run_until_complete(APICameraSnapshotTimelapseView().get(self.request))
        self.is_valid_mjpeg(response)

        # The animate will have been called with defaults; None
        mock_convert_frames.assert_called_with(ANY, "JPEG", 0.5)

    @mock.patch('motionmonitor.extensions.api.convert_frames')
    def test_get_timelapse_invalid_format(self, mock_convert_frames):
        mock_convert_frames.return_value = self.mocked_bytes
        self.add_camera(CAMERA_ID)
        self.add_frames(1, CAMERA_ID)

        self.request = make_mocked_request("GET", APICameraSnapshotTimelapseView.url + "?format=Bad_Format&scale=0.5",
                                           match_info={"camera_id": CAMERA_ID})
        self.request.app[KEY_MM] = self.mm

        with self.assertRaises(aiohttp.web_exceptions.HTTPBadRequest):
            response = self.loop.run_until_complete(APICameraSnapshotTimelapseView().get(self.request))


class TestAPICameraEventsView(TestAPIBase):
    def setUp(self) -> None:
        super().setUp()
        self.request = make_mocked_request("GET", APICameraEventsView.url, match_info={"camera_id": CAMERA_ID})
        self.request.app[KEY_MM] = self.mm

    def test_get_no_cameras(self):
        with self.assertRaises(aiohttp.web_exceptions.HTTPBadRequest):
            self.loop.run_until_complete(APICameraEventsView().get(self.request))

    def test_get_no_events(self):
        self.add_camera(CAMERA_ID)
        response = self.loop.run_until_complete(APICameraEventsView().get(self.request))
        json_data = self.is_valid_json(response)

        self.assertEqual(0, len(json_data["entities"]))

    def test_get_one_events(self):
        c = self.add_camera(CAMERA_ID)
        self.add_motion_event(c, EVENT_ID)
        self.add_motion_frames(1, CAMERA_ID, EVENT_ID)
        response = self.loop.run_until_complete(APICameraEventsView().get(self.request))
        json_data = self.is_valid_json(response)

        self.assertEqual(1, len(json_data["entities"]))


class TestAPICameraEventsTimelapseView(TestAPIBase):
    mocked_bytes = b'12345'

    def setUp(self) -> None:
        super().setUp()
        self.request = make_mocked_request("GET", APICameraEventsTimelapseView.url, match_info={"camera_id": CAMERA_ID})
        self.request.app[KEY_MM] = self.mm

    def test_get_no_cameras(self):
        with self.assertRaises(aiohttp.web_exceptions.HTTPBadRequest):
            self.loop.run_until_complete(APICameraEventsTimelapseView().get(self.request))

    @mock.patch('motionmonitor.extensions.api.animate_frames')
    def test_get_timelapse_default(self, mock_animate_frames):
        mock_animate_frames.return_value = self.mocked_bytes
        c = self.add_camera(CAMERA_ID)
        self.add_motion_event(c, EVENT_ID)
        self.add_motion_frames(1, CAMERA_ID, EVENT_ID)

        response = self.loop.run_until_complete(APICameraEventsTimelapseView().get(self.request))
        image_bytes = self.is_valid_gif(response)

        self.assertEqual(self.mocked_bytes, image_bytes)

        # The animate will have been called with defaults; None
        mock_animate_frames.assert_called_with(ANY, None)


class TestAPICameraEventEntityView(TestAPIBase):
    start_time = "20200601120000"

    def setUp(self) -> None:
        super().setUp()
        self.request = make_mocked_request("GET", APICameraEventEntityView.url, match_info={"camera_id": CAMERA_ID,
                                                                                            "event_id": EVENT_ID})
        self.request.app[KEY_MM] = self.mm

    def test_get_no_cameras(self):
        with self.assertRaises(aiohttp.web_exceptions.HTTPBadRequest):
            self.loop.run_until_complete(APICameraEventEntityView().get(self.request))

    def test_get_no_events(self):
        c = self.add_camera(CAMERA_ID)
        with self.assertRaises(aiohttp.web_exceptions.HTTPBadRequest):
            self.loop.run_until_complete(APICameraEventEntityView().get(self.request))

    def test_get_event(self):
        c = self.add_camera(CAMERA_ID)
        self.add_motion_event(c, EVENT_ID, self.start_time)
        self.add_motion_frames(1, CAMERA_ID, EVENT_ID)

        response = self.loop.run_until_complete(APICameraEventEntityView().get(self.request))
        json_data = self.is_valid_json(response)

        # Confirm the properties of the JSON response
        self.assertEqual(EVENT_ID, json_data["properties"]["eventId"])
        self.assertEqual(CAMERA_ID, json_data["properties"]["cameraId"])
        self.assertEqual(self.start_time, json_data["properties"]["startTime"])

    def test_delete(self):
        with self.assertRaises(aiohttp.web_exceptions.HTTPNotImplemented):
            response = self.loop.run_until_complete(APICameraEventEntityView().delete(self.request))


class TestAPICameraEventFramesView(TestAPIBase):
    start_time = "20200601120000"

    def setUp(self) -> None:
        super().setUp()
        self.request = make_mocked_request("GET", APICameraEventFramesView.url, match_info={"camera_id": CAMERA_ID,
                                                                                            "event_id": EVENT_ID})
        self.request.app[KEY_MM] = self.mm

    def test_get_no_cameras(self):
        with self.assertRaises(aiohttp.web_exceptions.HTTPBadRequest):
            self.loop.run_until_complete(APICameraEventFramesView().get(self.request))

    def test_get_no_events(self):
        c = self.add_camera(CAMERA_ID)
        with self.assertRaises(aiohttp.web_exceptions.HTTPBadRequest):
            self.loop.run_until_complete(APICameraEventFramesView().get(self.request))

    def test_get_no_frames(self):
        c = self.add_camera(CAMERA_ID)
        self.add_motion_event(c, EVENT_ID, self.start_time)

        response = self.loop.run_until_complete(APICameraEventFramesView().get(self.request))
        json_data = self.is_valid_json(response)

        self.assertEqual(0, len(json_data["entities"]))

    def test_get_one_frame(self):
        c = self.add_camera(CAMERA_ID)
        self.add_motion_event(c, EVENT_ID, self.start_time)
        self.add_motion_frames(1, CAMERA_ID, EVENT_ID)

        response = self.loop.run_until_complete(APICameraEventFramesView().get(self.request))
        json_data = self.is_valid_json(response)

        self.assertEqual(1, len(json_data["entities"]))


class TestAPICameraEventFrameView(TestAPIBase):
    timestamp = "20200601120000"
    frame_num = 0
    score = 999
    mocked_bytes = b'12345'

    def setUp(self) -> None:
        super().setUp()
        self.request = make_mocked_request("GET", APICameraEventFrameView.url, match_info={"camera_id": CAMERA_ID,
                                                                                           "event_id": EVENT_ID,
                                                                                           "timestamp": self.timestamp,
                                                                                           "frame": self.frame_num})
        self.request.app[KEY_MM] = self.mm

    def test_get_no_cameras(self):
        with self.assertRaises(aiohttp.web_exceptions.HTTPBadRequest):
            self.loop.run_until_complete(APICameraEventFrameView().get(self.request))

    def test_get_no_events(self):
        c = self.add_camera(CAMERA_ID)
        with self.assertRaises(aiohttp.web_exceptions.HTTPBadRequest):
            self.loop.run_until_complete(APICameraEventFrameView().get(self.request))

    @mock.patch('motionmonitor.extensions.api.convert_frames')
    def test_get_event_frame_as_json(self, mock_convert_frames):
        mock_convert_frames.return_value = self.mocked_bytes
        c = self.add_camera(CAMERA_ID)
        self.add_motion_event(c, EVENT_ID, self.timestamp)
        self.add_motion_frames(1, CAMERA_ID, EVENT_ID, self.timestamp, self.frame_num, self.score)

        response = self.loop.run_until_complete(APICameraEventFrameView().get(self.request))
        json_data = self.is_valid_json(response)

        # The convert will have been called with defaults; JPEG and None
        mock_convert_frames.assert_called_with(ANY, "JPEG", None)

        # Confirm the properties of the JSON response
        self.assertEqual(CAMERA_ID, json_data["properties"]["cameraId"])
        self.assertEqual(EVENT_ID, json_data["properties"]["eventId"])
        self.assertEqual(self.timestamp, json_data["properties"]["timestamp"])
        self.assertEqual(self.score, json_data["properties"]["score"])
        self.assertEqual(self.frame_num, json_data["properties"]["frame"])
        self.assertEqual(base64.b64encode(self.mocked_bytes).decode('ascii'), json_data["properties"]["jpegBytes"])

    @mock.patch('motionmonitor.extensions.api.convert_frames')
    def test_get_event_frame_as_scaled_gif(self, mock_convert_frames):
        mock_convert_frames.return_value = self.mocked_bytes
        c = self.add_camera(CAMERA_ID)
        self.add_motion_event(c, EVENT_ID, self.timestamp)
        self.add_motion_frames(1, CAMERA_ID, EVENT_ID, self.timestamp, self.frame_num, self.score)

        response = self.loop.run_until_complete(APICameraEventFrameView().get(self.request))
        json_data = self.is_valid_json(response)

        # Configure the URL query string
        self.request = make_mocked_request("GET", APICameraEventFrameView.url + "?format=GIF&scale=0.5",
                                           match_info={"camera_id": CAMERA_ID,
                                                       "event_id": EVENT_ID,
                                                       "timestamp": self.timestamp,
                                                       "frame": self.frame_num})
        self.request.app[KEY_MM] = self.mm

        response = self.loop.run_until_complete(APICameraEventFrameView().get(self.request))
        image_bytes = self.is_valid_gif(response)

        self.assertEqual(self.mocked_bytes, image_bytes)

        # The convert will have been called with defaults; GIF and 0.5
        mock_convert_frames.assert_called_with(ANY, "GIF", 0.5)

    def test_delete(self):
        with self.assertRaises(aiohttp.web_exceptions.HTTPNotImplemented):
            response = self.loop.run_until_complete(APICameraEventFrameView().delete(self.request))


class TestAPICameraEventTimelapseView(TestAPIBase):
    mocked_bytes = b'12345'

    def setUp(self) -> None:
        super().setUp()
        self.request = make_mocked_request("GET", APICameraEventTimelapseView.url, match_info={"camera_id": CAMERA_ID,
                                                                                               "event_id": EVENT_ID})
        self.request.app[KEY_MM] = self.mm

    def test_get_no_cameras(self):
        with self.assertRaises(aiohttp.web_exceptions.HTTPBadRequest):
            self.loop.run_until_complete(APICameraEventTimelapseView().get(self.request))

    def test_get_no_events(self):
        c = self.add_camera(CAMERA_ID)
        with self.assertRaises(aiohttp.web_exceptions.HTTPBadRequest):
            self.loop.run_until_complete(APICameraEventTimelapseView().get(self.request))

    @mock.patch('motionmonitor.extensions.api.animate_frames')
    def test_get_timelapse_default(self, mock_animate_frames):
        mock_animate_frames.return_value = self.mocked_bytes
        c = self.add_camera(CAMERA_ID)
        self.add_motion_event(c, EVENT_ID)
        self.add_motion_frames(1, CAMERA_ID, EVENT_ID)

        response = self.loop.run_until_complete(APICameraEventTimelapseView().get(self.request))
        image_bytes = self.is_valid_gif(response)

        self.assertEqual(self.mocked_bytes, image_bytes)

        # The animate will have been called with defaults; None
        mock_animate_frames.assert_called_with(ANY, None)


class TestAPIJobsView(TestAPIBase):
    job_name = "Test Job"

    def setUp(self) -> None:
        super().setUp()
        self.request = make_mocked_request("GET", APIJobsView.url)
        self.request.app[KEY_MM] = self.mm

    def test_get_no_jobs(self):
        response = self.loop.run_until_complete(APIJobsView().get(self.request))
        json_data = self.is_valid_json(response)

        self.assertEqual(0, len(json_data["entities"]))

    def test_get_one_job(self):
        job = Job(self.job_name)
        self.mm.jobs[self.job_name] = job
        response = self.loop.run_until_complete(APIJobsView().get(self.request))
        json_data = self.is_valid_json(response)

        self.assertEqual(1, len(json_data["entities"]))


class TestAPIJobEntityView(TestAPIBase):
    job_name = "Test Job"

    def setUp(self) -> None:
        super().setUp()
        self.request = make_mocked_request("GET", APIJobEntityView.url, match_info={"job_id": self.job_name})
        self.request.app[KEY_MM] = self.mm

    def test_get_no_jobs(self):
        with self.assertRaises(aiohttp.web_exceptions.HTTPNotImplemented):
            response = self.loop.run_until_complete(APIJobEntityView().get(self.request))


if __name__ == '__main__':
    unittest.main()
