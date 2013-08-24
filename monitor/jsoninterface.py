'''
Created on 11/08/2013

@author: djwhyte
'''
from gi.repository import GObject

import logging
import socket

class JSONInterface():
    
    __SERVER_ADDR = '127.0.0.1'
    __SERVER_PORT = 8889

    
    def __init__(self, camera_monitor):
        self.__logger = logging.getLogger(__name__)
        
        self.__camera_monitor = camera_monitor
        
        # Initialise server and start listening.
        self.__socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.__socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.__logger.debug("binding to %s:%d" % (self.__SERVER_ADDR, self.__SERVER_PORT))
        self.__socket.bind((self.__SERVER_ADDR, self.__SERVER_PORT))
        self.__logger.info("Listening...")
        
        # When there is data available, call the callback.
        GObject.io_add_watch(self.__socket.fileno(), GObject.IO_IN, 
                             self.__handle_json_request)

    def __handle_json_request(self, fd, condition):
        self.__logger.debug("Need to handle JSON request.")
        # If it is the correct socket, read data from it.
        if fd == self.__socket.fileno():
            try:
                line = self.__socket.recv(1024)
                self.__logger.debug("Rxd raw data: %s" % line)
                    
            except Exception, e:
                self.__logger.exception(e)

            self.__logger.info("We have %d cameras" % len(self.__camera_monitor.get_cameras()))
            
        return True
