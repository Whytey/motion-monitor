'''
Created on 24/07/2013

@author: djwhyte
'''

import asyncio
import json
import logging
from datetime import datetime

from motionmonitor.models import EventFrame, Event, Frame
from motionmonitor.const import (
    EVENT_MOTION_INTERNAL,
    EVENT_MANAGEMENT_ACTIVITY,
    EVENT_NEW_FRAME,
    EVENT_NEW_MOTION_FRAME,
    EVENT_MOTION_EVENT_START,
    EVENT_MOTION_EVENT_END
)


def get_extension(mm):
    return SocketListener(mm)


class SocketListener:
    def __init__(self, mm):
        self.__logger = logging.getLogger("%s.%s" % (self.__class__.__module__, self.__class__.__name__))

        self.mm = mm
        self.transport = None

    async def start_extension(self):
        config = self.mm.config
        address = config["SOCKET_SERVER"]["ADDRESS"]
        port = int(config["SOCKET_SERVER"]["PORT"])
        self.__logger.debug("binding to %s:%d" % (address, port))

        loop = self.mm.loop
        protocol = SocketHandler(self.mm)

        # One protocol instance will be created to serve all client requests
        socket_listener = loop.create_datagram_endpoint(
            lambda: protocol, local_addr=(address, port))
        self.transport, p1 = await socket_listener
        # self.transport, p1 = loop.run_until_complete(socket_listener)
        self.__logger.info("Listening...")

    def close(self):
        if self.transport:
            self.__logger.info("Closing the transport.")
            self.transport.close()


class SocketHandler(asyncio.DatagramProtocol):
    FTYPE_IMAGE = 1
    FTYPE_IMAGE_SNAPSHOT = 2
    FTYPE_IMAGE_MOTION = 4
    FTYPE_MPEG = 8
    FTYPE_MPEG_MOTION = 16
    FTYPE_MPEG_TIMELAPSE = 32

    def __init__(self, mm):
        self.mm = mm
        self.__logger = logging.getLogger("%s.%s" % (self.__class__.__module__, self.__class__.__name__))
        self.mm.bus.listen(EVENT_MOTION_INTERNAL, self.handle_motion_message)
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

    @staticmethod
    def decode_event_msg(msg):
        # self.__logger.debug("Creating Event from socket message: %s" % msg)
        event_id = msg["event"]
        camera_id = msg["camera"]
        start_time = msg["timestamp"]
        return Event(event_id, camera_id, start_time)

    @staticmethod
    def decode_frame_msg(msg):
        # self.__logger.debug("Creating Frame from socket message: %s" % msg)
        camera_id = msg["camera"]
        timestamp = msg["timestamp"]
        frame_num = msg["frame"]
        filename = msg["file"]
        return Frame(camera_id, timestamp, frame_num, filename)

    @staticmethod
    def decode_event_frame_msg(msg):
        # self.__logger.debug("Creating EventFrame from socket message: %s" % msg)
        camera_id = msg["camera"]
        event_id = msg["event"]
        timestamp = msg["timestamp"]
        frame_num = msg["frame"]
        filename = msg["file"]
        score = msg["score"]
        return EventFrame(camera_id, event_id, timestamp, frame_num, filename, score)

    def handle_motion_message(self, event):
        msg = event.data
        if msg["type"] in ["picture_save"]:
            file_type = int(msg["filetype"])
            if file_type == self.FTYPE_IMAGE_SNAPSHOT:
                self.__logger.debug("Handling a snapshot")
                frame = SocketHandler.decode_frame_msg(msg)
                self.mm.bus.fire(EVENT_NEW_FRAME, frame)

            if file_type == self.FTYPE_IMAGE:
                self.__logger.debug("Handling motion image")
                event_frame = SocketHandler.decode_event_frame_msg(msg)
                self.mm.bus.fire(EVENT_NEW_MOTION_FRAME, event_frame)

        if msg["type"] == "event_start":
            # We need an Event
            new_event = SocketHandler.decode_event_msg(msg)
            self.__logger.info("Created new event for start: %s" % new_event)
            self.mm.bus.fire(EVENT_MOTION_EVENT_START, new_event)
        if msg["type"] == "event_end":
            new_event = SocketHandler.decode_event_msg(msg)
            self.__logger.info("Created new event for end: %s" % new_event)
            self.mm.bus.fire(EVENT_MOTION_EVENT_END, new_event)
