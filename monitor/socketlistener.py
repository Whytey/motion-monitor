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
    
    __gsignals__ = {
        MOTION_EVENT: (GObject.SIGNAL_RUN_LAST, None, (GObject.TYPE_PYOBJECT,))
    }
        
    def __init__(self):
        GObject.GObject.__init__(self)
        
        self.__logger = logging.getLogger(__name__)
        
        # Initialise server and start listening.
        self.__socket = socket.socket()
        self.__socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.__socket.bind(('127.0.0.1', 8888))
        self.__socket.listen(1)
        self.__logger.info("Listening...")
        GObject.io_add_watch(self.__socket.fileno(), GObject.IO_IN, self.__handle_msg)
        
    def __validate_msg(self, msg):
        assert type(msg) == dict, "Message should be a dictionary: %s" % msg
        assert "type" in msg, "Message does not specify what type it is: %s" % msg
        assert msg["type"] in ["area_detected",
                               "camera_lost",
                               "event_end",
                               "event_start",
                               "motion_detected",
                               "movie_end",
                               "movie_start",
                               "picture_save"], "Unknown message type: %s" % msg["type"]
        
        self.__logger.debug("Got a message type of '%s'" % msg["type"])

        
    def __handle_msg(self, fd, condition):
        # If it is the correct socket, read data from it.
        if fd == self.__socket.fileno():
            try:
                conn, addr = self.__socket.accept()
                line = conn.recv(65536)
                self.__logger.debug("Rxd raw data: %s" % line)
                msg = json.loads(line)
                self.__validate_msg(msg)
            except Exception, e:
                self.__logger.exception(e)
                return True
            
            self.emit(self.MOTION_EVENT, msg)
            return True
