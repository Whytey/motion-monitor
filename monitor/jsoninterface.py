'''
Created on 11/08/2013

@author: djwhyte
'''
from gi.repository import GObject
import json
import logging
import socket


class JSONInterface():
    
    __SERVER_ADDR = '127.0.0.1'
    __SERVER_PORT = 8889

    
    def __init__(self, camera_monitor):
        self.__logger = logging.getLogger(__name__)
        
        self.__camera_monitor = camera_monitor
        
        # Initialise server and start listening.
        self.__socket = socket.socket()
        self.__socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.__logger.debug("binding to %s:%d" % (self.__SERVER_ADDR, self.__SERVER_PORT))
        self.__socket.bind((self.__SERVER_ADDR, self.__SERVER_PORT))
        self.__socket.listen(1)
        self.__logger.info("Listening...")
        
        # When there is data available, call the callback.
        GObject.io_add_watch(self.__socket.fileno(), GObject.IO_IN, 
                             self.__handle_json_request)
        
    def __validate_msg(self, msg):
        assert type(msg) == dict, "Message should be a dictionary: %s" % msg
        assert "type" in msg, "Message does not specify what type it is: %s" % msg
        
        self.__logger.debug("Got a message type of '%s'" % msg["type"])

        assert msg["type"] in ["camera_summary"]


    def __handle_json_request(self, fd, condition):
        try:
            self.__logger.debug("Need to handle JSON request.")
            # If it is the correct socket, read data from it.
            if fd == self.__socket.fileno():
                conn, addr = self.__socket.accept()
                # conn - socket to client
                # addr - clients address
                line = conn.recv(1024) #receive data from client
                
                self.__logger.debug("Rxd raw data: %s" % line)
                
                msg = json.loads(line)
                self.__validate_msg(msg)
                
                response = {}
                
                if msg["type"] == "camera_summary":
                    cams_resp = []
                    for key, camera in self.__camera_monitor.get_cameras().items():
                        cams_resp.append(camera.toJSON())
                    response["camera"] = cams_resp
                    
                conn.send(json.dumps(response))
                conn.close()

        except Exception as e:
            self.__logger.exception(e)
            raise
        return True
