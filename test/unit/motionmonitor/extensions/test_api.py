import asyncio
import base64
import json
import logging
import unittest
from datetime import datetime
from unittest import mock
from unittest.mock import Mock, ANY

import aiohttp
import jsonschema
from aiohttp.test_utils import make_mocked_request

from motionmonitor.const import KEY_MM
from motionmonitor.extensions.api import API, APICameraSnapshotFramesView, APICamerasView, APICameraEntityView, \
    APICameraSnapshotFrameView
from motionmonitor.extensions.api.schema import JSONSCHEMA
from motionmonitor.models import Camera, Frame

CAMERA_ID = "1"


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

    def is_valid_json(self, response):
        self.assertEqual(200, response.status)
        self.assertEqual("application/json", response.content_type)
        json_data = json.loads(response.body)
        jsonschema.validate(json_data, schema=JSONSCHEMA)
        return json_data


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
        # The convert will have been called with defaults; JPEG and None
        mock_convert_frames.assert_called_with(ANY, "GIF", 0.5)


if __name__ == '__main__':
    unittest.main()
