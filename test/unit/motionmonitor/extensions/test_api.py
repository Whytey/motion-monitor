import asyncio
import logging
import unittest
from unittest.mock import Mock

from motionmonitor.extensions.api import API


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


if __name__ == '__main__':
    unittest.main()
