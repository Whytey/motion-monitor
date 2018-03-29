'''
Created on 24/07/2013

@author: djwhyte
'''

import json
import logging
import socket
from gi.repository import GObject

from motionmonitor.const import (
    EVENT_MOTION_INTERNAL,
    EVENT_MANAGEMENT_ACTIVITY
)


class SocketListener():
    
    def __init__(self, mm):
        self.__logger = logging.getLogger("%s.%s" % (self.__class__.__module__, self.__class__.__name__))

        self.mm = mm
        config = mm.config
        
        # Initialise server and start listening.
        self.__socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.__socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.__logger.debug("binding to %s:%d" % (config.MOTION_SOCKET_ADDR, config.MOTION_SOCKET_PORT))
        self.__socket.bind((config.MOTION_SOCKET_ADDR, config.MOTION_SOCKET_PORT))
        self.__logger.info("Listening...")
        
        # When there is data available, call the callback.
        GObject.io_add_watch(self.__socket.fileno(), GObject.IO_IN, 
                             self.__handle_socket_msg)
        
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

        
    def __handle_socket_msg(self, fd, condition):
        try:
            self.__logger.debug("Need to handle socket IO.")
            # If it is the correct socket, read data from it.
            if fd == self.__socket.fileno():
                line = self.__socket.recv(1024)
                self.__logger.debug("Rxd raw data: %s" % line)
                msg = json.loads(line)
                msg_type = self.__validate_msg(msg)
                self.mm.bus.fire(msg_type, msg)
        except Exception as e:
            self.__logger.exception(e)
            raise
        return True
