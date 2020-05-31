import asyncio
import json
import logging
import unittest
from datetime import datetime
from unittest.mock import Mock
from aiohttp.test_utils import make_mocked_request
from motionmonitor.const import KEY_MM
from motionmonitor.extensions.api import API, APICameraSnapshotsView
from motionmonitor.models import Camera, Frame

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


class TestAPICameraEntityView(unittest.TestCase):
    def test_simple(self):
        pass


class TestAPICameraSnapshotsView(unittest.TestCase):
    def setUp(self) -> None:
        self.endpoint = APICameraSnapshotsView()
        self.loop = asyncio.new_event_loop()

        self.camera = Camera(CAMERA_ID)
        mm = Mock()
        self.config = {"API": {"ADDRESS": "127.0.0.1", "PORT": "9999"}}
        mm.config = self.config
        mm.loop = self.loop
        mm.cameras = {CAMERA_ID: Camera(CAMERA_ID)}
        mm.cameras = {CAMERA_ID: self.camera}

        self.request = make_mocked_request("GET", APICameraSnapshotsView.url, match_info={"camera_id": CAMERA_ID})
        self.request.app[KEY_MM] = mm

    async def _code_for_event_loop(self, request):
        return await self.endpoint.get(request)

    def test_simple(self):
        response = self.loop.run_until_complete(self._code_for_event_loop(self.request))

        self.assertEqual(200, response.status)
        self.assertEqual("application/json", response.content_type)
        json_data = json.loads(response.body)
        self.assertEqual(0, len(json_data["snapshots"]))

    def test_single_snapshot(self):
        f = Frame(self.camera, str(datetime.now()), 1, "filename2")
        self.camera.append_snapshot_frame(f)

        response = self.loop.run_until_complete(self._code_for_event_loop(self.request))

        self.assertEqual(200, response.status)
        self.assertEqual("application/json", response.content_type)
        json_data = json.loads(response.body)
        self.assertEqual(1, len(json_data["snapshots"]))


class TestAPICameraSnapshotEntityView(unittest.TestCase):
    pass

if __name__ == '__main__':
    unittest.main()
