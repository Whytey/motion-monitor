'''
Created on 09/04/2014

@author: djwhyte
'''

from abc import ABCMeta, abstractmethod
import base64
import json
import logging
import socket

def _request_data(data):
    # Get the data from the socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    sock.connect(('192.168.0.100', 8889))
    sock.send(json.dumps(data))
    rxd_data = []
    while True:
        data = sock.recv(65635)
        if not data: break
        rxd_data.append(data)
    return ''.join(rxd_data)

def getHandler(requestData):
    pass

class BaseHandler(object):
    __metaclass__ = ABCMeta

    def __init__(self, contentType, request):
        self.__logger = logging.getLogger("%s.BaseHandler" % __name__)
        self._contentType = contentType
        self._request = request
        
    @property
    def contentType(self):
        return self._contentType
    
    @abstractmethod
    def getBytes(self):
        pass
    
    @staticmethod
    def _getFrameBytes(cameraId, timestamp, frame, eventId=None):
        # Request the data in JSON format
        request = {"method": "image.get",
                   "params": {"timestamp": timestamp, 
                              "type": "2", 
                              "cameraid": cameraId,
                              "frame": frame, 
                              "include_image": "True"}
                   }
        if eventId:
            request["params"]["type"] = 1
            request["params"]["event"] = eventId
            
        response = _request_data(request)
        response_json = json.loads(response)
        
        # Extract the image from it and return the bytes
        imageBytes = response_json["result"][0]["image"]
        decodedBytes = base64.b64decode(imageBytes)

        return decodedBytes
            

class SnapshotFrameHandler(BaseHandler):
    
    def __init__(self, request):
        self.__logger = logging.getLogger("%s.SnapshotFrameHandler" % __name__)
        BaseHandler.__init__(self, "image/jpeg", request)
    
    def getBytes(self):
        # Get this requests params
        try:
            cameraId = self._request["cameraId"]
            timestamp = self._request["timestamp"]
            frame = self._request["frame"]
        except KeyError, e:
            # One of the above required values are not provided in the request
            raise e
        
        # Return the bytes for the snapshot frame
        return BaseHandler._getFrameBytes(cameraId, timestamp, frame)
    
class MotionFrameHandler(BaseHandler):
    
    def __init__(self, request):
        self.__logger = logging.getLogger("%s.MotionFrameHandler" % __name__)
        BaseHandler.__init__(self, "image/jpeg", request)
    
    def getBytes(self):
        # Get this requests params
        try:
            eventId = self._request["eventId"]
            cameraId = self._request["cameraId"]
            timestamp = self._request["timestamp"]
            frame = self._request["frame"]
        except KeyError, e:
            # One of the above required values are not provided in the request
            raise e
        
        # Return the bytes for the snapshot frame
        return BaseHandler._getFrameBytes(cameraId, timestamp, frame)
    
        
class LiveFrameHandler(BaseHandler):
    
    def __init__(self, request):
        self.__logger = logging.getLogger("%s.LiveFrameHandler" % __name__)
        BaseHandler.__init__(self, "image/jpeg", request)
    
    def getBytes(self):
        # Get this requests params
        try:
            cameraId = self._request["cameraId"]
        except KeyError, e:
            # One of the above required values are not provided in the request
            raise e

        # Get the latest camera summary
        request = {"method": "camera.get",
                   "params": {}
                   }
        response = _request_data(request)
        response_json = json.loads(response)
        
        # Get this cameras details from the summary
        for camera in response_json["result"]:
            if camera["cameraId"] == cameraId:
                timestamp = camera["lastSnapshot"]["timestamp"]
                frame = camera["lastSnapshot"]["frame"]
        
        # Return the bytes for the live frame
        return BaseHandler._getFrameBytes(cameraId, timestamp, frame)
        

