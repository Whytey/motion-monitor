'''
Created on 24/07/2013

@author: djwhyte
'''

import asyncio
import json
import logging
import socket

from motionmonitor.const import (
    EVENT_MOTION_INTERNAL,
    EVENT_MANAGEMENT_ACTIVITY
)


class SocketListener():
    def __init__(self, mm):
        self.__logger = logging.getLogger("%s.%s" % (self.__class__.__module__, self.__class__.__name__))

        self.mm = mm
        config = mm.config

        self.transport = None

    async def listen(self):
        config = self.mm.config
        address = config["SOCKET_SERVER"]["ADDRESS"]
        port = int(config["SOCKET_SERVER"]["PORT"])
        self.__logger.debug("binding to %s:%d" % (address, port))

        loop = self.mm.loop
        protocol = SocketHandler(self.mm)

        # One protocol instance will be created to serve all client requests
        socket_listener = loop.create_datagram_endpoint(
            lambda: protocol, local_addr=(address, port), reuse_address=True)
        self.transport, p1 = await socket_listener
        # self.transport, p1 = loop.run_until_complete(socket_listener)
        self.__logger.info("Listening...")

    def close(self):
        if self.transport:
            self.transport.close()


class SocketHandler(asyncio.DatagramProtocol):

    def __init__(self, mm):
        self.mm = mm
        self.__logger = logging.getLogger("%s.%s" % (self.__class__.__module__, self.__class__.__name__))
        self.__logger.debug("Handler configured")

    def connection_made(self, transport):
        self.transport = transport

    def __validate_msg(self, msg):
        assert type(msg) == dict, "Message should be a dictionary: %s" % msg
        assert "type" in msg, "Message does not specify what type it is: %s" % msg

        self.__logger.debug("Got a message type of '%s'" % msg["type"])

        if msg["type"] in ["area_detected",
                           "camera_lost",
                           "event_end",
                           "event_start",
                           "motion_detected",
                           "movie_end",
                           "movie_start",
                           "picture_save"]:
            return EVENT_MOTION_INTERNAL

        if msg["type"] in ["sweep", "audit"]:
            return EVENT_MANAGEMENT_ACTIVITY

        assert False, "Unknown message type: %s" % msg["type"]

    def datagram_received(self, data, addr):
        line = data.decode()
        self.__logger.debug('Received %r from %s' % (line, addr))

        msg = json.loads(line)
        msg_type = self.__validate_msg(msg)
        self.mm.bus.fire(msg_type, msg)
