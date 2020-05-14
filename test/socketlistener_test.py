import asyncio
import json
import logging
import socket
import unittest
from unittest.mock import Mock

from motionmonitor import config
from motionmonitor import socketlistener


class TestSocketListener(unittest.TestCase):
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
        mm.config.MOTION_SOCKET_PORT = config.Testing.MOTION_SOCKET_PORT
        mm.config.MOTION_SOCKET_ADDR = config.Testing.MOTION_SOCKET_ADDR
        mm.loop = self.loop

        self.sl = socketlistener.SocketListener(mm)
        self.sl.listen()

    def tearDown(self) -> None:
        self.sl.close()

    def capture_event(self, msg_type, msg):
        self.logger.debug("Got an event of type '{}': {}".format(msg_type, msg))
        self.msg_type = msg_type
        self.msg = msg

    def send_socket_msg(self, msg_dict):
        sock = socket.socket(socket.AF_INET,  # Internet
                             socket.SOCK_DGRAM)  # UDP
        sock.sendto(json.dumps(msg_dict).encode(),
                    (self.sl.mm.config.MOTION_SOCKET_ADDR, self.sl.mm.config.MOTION_SOCKET_PORT))
        sock.close()

    def test_simple(self):
        async def code_for_event_loop():
            self.sl.mm.bus.fire.side_effect = self.capture_event

            self.send_socket_msg({"type": "picture_save"})
        self.loop.run_until_complete(code_for_event_loop())

        self.assertEqual(self.msg["type"], "picture_save")


if __name__ == '__main__':
    unittest.main()
