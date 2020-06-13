import asyncio
import json
import logging
import unittest
from datetime import datetime
from unittest.mock import Mock

from aiohttp.test_utils import make_mocked_request

from motionmonitor.config import ConfigReader
from motionmonitor.const import KEY_MM
from motionmonitor.extensions.api import API, APICameraSnapshotFramesView, APICamerasView, APICameraEntityView, \
    APICameraSnapshotFrameView
from motionmonitor.models import Camera, Frame
from test.unit.utils import create_image_file

CAMERA_ID = "1"


class TestAPIServer(unittest.TestCase):
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

        mm = Mock()
        self.config = {"API": {"ADDRESS": "127.0.0.1", "PORT": "9999"}}

        mm.config = self.config
        mm.loop = self.loop

        self.api = API(mm)

        async def start_socket():
            await self.api.start_extension()

        self.loop.run_until_complete(start_socket())

    def test_simple(self):
        # If the API has been started, it should be an attribute of the mm instance.
        self.assertEqual(self.api, self.api.mm.api)


class TestAPICamerasView(unittest.TestCase):

    def setUp(self) -> None:
        self.loop = asyncio.new_event_loop()

        self.camera = Camera(CAMERA_ID)
        mm = Mock()
        mm.loop = self.loop
        mm.cameras = {CAMERA_ID: self.camera}

        self.request = make_mocked_request("GET", APICamerasView.url)
        self.request.app[KEY_MM] = mm

    def test_simple(self):
        response = self.loop.run_until_complete(APICamerasView().get(self.request))
        self.assertEqual(200, response.status)
        self.assertEqual("application/json", response.content_type)
        json_data = json.loads(response.body)
        self.assertEqual(1, len(json_data["entities"]))
        self.assertIsNotNone(json_data["entities"][0]["href"])


class TestAPICameraEntityView(unittest.TestCase):
    def setUp(self) -> None:
        self.loop = asyncio.new_event_loop()

        self.camera = Camera(CAMERA_ID)
        mm = Mock()
        mm.loop = self.loop
        mm.cameras = {CAMERA_ID: self.camera}

        self.request = make_mocked_request("GET", APICameraEntityView.url, match_info={"camera_id": CAMERA_ID})
        self.request.app[KEY_MM] = mm

    def test_simple(self):
        response = self.loop.run_until_complete(APICameraEntityView().get(self.request))
        self.assertEqual(200, response.status)
        self.assertEqual("application/json", response.content_type)
        json_data = json.loads(response.body)
        self.assertEqual(CAMERA_ID, json_data["properties"]["cameraId"])


class TestAPICameraSnapshotsView(unittest.TestCase):
    def setUp(self) -> None:
        self.loop = asyncio.new_event_loop()

        self.camera = Camera(CAMERA_ID)
        mm = Mock()
        mm.loop = self.loop
        mm.cameras = {CAMERA_ID: self.camera}

        self.request = make_mocked_request("GET", APICameraSnapshotFramesView.url, match_info={"camera_id": CAMERA_ID})
        self.request.app[KEY_MM] = mm

    def test_simple(self):
        response = self.loop.run_until_complete(APICameraSnapshotFramesView().get(self.request))

        self.assertEqual(200, response.status)
        self.assertEqual("application/json", response.content_type)
        json_data = json.loads(response.body)
        self.assertEqual(0, len(json_data["entities"]))

    def test_single_snapshot(self):
        f = Frame(self.camera, datetime.now(), 1, "filename2")
        self.camera.append_snapshot_frame(f)

        response = self.loop.run_until_complete(APICameraSnapshotFramesView().get(self.request))

        self.assertEqual(200, response.status)
        self.assertEqual("application/json", response.content_type)
        json_data = json.loads(response.body)
        self.assertEqual(1, len(json_data["entities"]))


class TestAPICameraSnapshotEntityView(unittest.TestCase):
    def setUp(self) -> None:
        config = ConfigReader().read_config("motion-monitor.ini.test", False)
        filename = config["GENERAL"]["TARGET_DIR"] + "TestFile.jpg"
        create_image_file(filename)

        self.loop = asyncio.new_event_loop()

        self.camera = Camera(CAMERA_ID)
        timestamp = datetime.now()
        f = Frame(self.camera.id, timestamp, 1, filename)
        self.camera.append_snapshot_frame(f)

        mm = Mock()
        mm.loop = self.loop
        mm.cameras = {CAMERA_ID: self.camera}

        self.request = make_mocked_request("GET", APICameraSnapshotFrameView.url, match_info={"camera_id": CAMERA_ID,
                                                                                              "timestamp": timestamp.strftime(
                                                                                                  "%Y%m%d%H%M%S"),
                                                                                              "frame": 1})
        self.request.app[KEY_MM] = mm

    def test_simple(self):
        response = self.loop.run_until_complete(APICameraSnapshotFrameView().get(self.request))
        self.assertEqual(200, response.status)
        self.assertEqual("application/json", response.content_type)
        json_data = json.loads(response.body)


if __name__ == '__main__':
    unittest.main()
