'''
Created on 11/08/2013

@author: djwhyte
'''
from PIL import Image
from StringIO import StringIO
from gi.repository import GObject
import base64
import json
import logging
import socket
import datetime
import time


class JSONInterface():
    
    __SERVER_ADDR = '127.0.0.1'
    __SERVER_PORT = 8889
    __CONFIG_target_dir = '/data/motion/'
    __CONFIG_snapshot_filename = 'snapshots/camera%t/%Y/%m/%d/%H/%M/%S-snapshot.jpg'


    
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

        assert msg["type"] in ["camera_summary",
                               "get_picture"]
        if msg["type"] == "get_picture":
            assert ("path" in msg) or ("camera" in msg and "timestamp" in msg), "Can't get_picture without a 'path': %s" % msg
            
    def __decode_image_path(self, msg):
        timestamp = msg["timestamp"]
        camera = msg["camera"]
        
        # Parse the string timestamp
        ts = datetime.datetime.strptime(timestamp, '%Y%m%d%H%M%S')
        
        path = self.__CONFIG_target_dir + self.__CONFIG_snapshot_filename

        # Inject the camera number
        path = path.replace("%t", camera)
        
        # Overlay the timestamp into the filepath
        path = ts.strftime(path)
        
        self.__logger.debug("Decoded the image path of %s to %s" % (msg, path))
        return path
            
    def __get_image(self, msg):
        if "path" in msg:
            path = msg["path"]
        else: 
            path = self.__decode_image_path(msg)
            
        # Need to ensure we only serve up motion files.
        assert path.startswith("/data/motion/"), "Not a motion file: %s" % path
        # TODO: Need to only server up jpeg files.

        with open(path, "rb") as image_file:
            if "thumbnail" in msg and msg["thumbnail"].upper() == "TRUE":
                self.__logger.debug("Creating a thumbnail")
                size = 160, 120
                thumbnail = StringIO()
                im = Image.open(image_file)
                im.thumbnail(size, Image.ANTIALIAS)
                im.save(thumbnail, "JPEG")
                file_bytes = thumbnail.getvalue()
            else:
                file_bytes = image_file.read()

        encoded_string = base64.b64encode(file_bytes)
        self.__logger.debug("Returning encoded image bytes")
        return encoded_string
        
    def __handle_json_request(self, fd, condition):
        response = {}

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
            
                if msg["type"] == "camera_summary":
                    cams_resp = []
                    for key, camera in self.__camera_monitor.get_cameras().items():
                        cams_resp.append(camera.toJSON())
                    response["camera"] = cams_resp
                
                if msg["type"] == "get_picture":
                    response["bytes"] = self.__get_image(msg)

        except Exception as e:
            self.__logger.exception(e)
            response["error"] = str(e)
        finally:
            if not conn is None:
                self.__logger.debug("Sending response: %s" % response)
                conn.send(json.dumps(response))
                conn.close()
            
        return True
