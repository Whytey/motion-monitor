'''
Created on 24/07/2013

@author: djwhyte
'''

from gi.repository import GObject
import json
import logging
import socket

class SocketListener(GObject.GObject):
    
    MOTION_EVENT = "motion_event"
    MANAGEMENT_EVENT = "management_event"
    
    __gsignals__ = {
        MOTION_EVENT: (GObject.SIGNAL_RUN_LAST, None, (GObject.TYPE_PYOBJECT,)),
        MANAGEMENT_EVENT: (GObject.SIGNAL_RUN_LAST, None, (GObject.TYPE_PYOBJECT,))
    }
    
    __SERVER_ADDR = '127.0.0.1'
    __SERVER_PORT = 8888
        
    def __init__(self):
        GObject.GObject.__init__(self)
        
        self.__logger = logging.getLogger(__name__)
        
        # Initialise server and start listening.
        self.__socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.__socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.__logger.debug("binding to %s:%d" % (self.__SERVER_ADDR, self.__SERVER_PORT))
        self.__socket.bind((self.__SERVER_ADDR, self.__SERVER_PORT))
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
            return self.MOTION_EVENT
        
        if msg["type"] == "sweep":
            return self.MANAGEMENT_EVENT
        
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
                if msg_type == self.MANAGEMENT_EVENT:
                    self.emit(self.MANAGEMENT_EVENT, msg)
                if msg_type == self.MOTION_EVENT:
                    self.emit(self.MOTION_EVENT, msg)
                        
        except Exception as e:
            self.__logger.exception(e)
            raise
        return True
