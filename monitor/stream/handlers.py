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

    sock.connect(('localhost', 8889))
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
    def getBytes(self, requestParams):
        pass
            

class SnapshotFrameHandler(BaseHandler):
    
    def __init__(self, request):
        self.__logger = logging.getLogger("%s.SnapshotFrameHandler" % __name__)
        BaseHandler.__init__(self, "image/jpeg", request)

    
    def getBytes(self, requestParams):
        # Get this requests params
        try:
            cameraId = requestParams["cameraId"]
            timestamp = requestParams["timestamp"]
            frame = requestParams["frame"]
        except KeyError, e:
            # One of the above required values are not provided in the request
            raise e
        
        request = {"method": "image.get",
                   "params": {"timestamp": timestamp, 
                              "type": "2", 
                              "cameraid": cameraId,
                              "frame": frame, 
                              "include_image": "True"}
                   }
        
        response = _request_data(request)
        response_json = json.loads(response)
        imageBytes = response_json["result"][0]["image"]
        decodedBytes = base64.b64decode(imageBytes)

        return decodedBytes
        
class LiveFrameHandler(BaseHandler):
    
    def __init__(self, request):
        self.__logger = logging.getLogger("%s.LiveFrameHandler" % __name__)
        BaseHandler.__init__(self, "image/jpeg", request)

    
    def getBytes(self, requestParams):
        # Get the latest camera summary
        request = {"method": "camera.get",
                   "params": {}
                   }
        
        response = _request_data(request)
        response_json = json.loads(response)
        
        for camera in response_json["result"]:
            if camera["cameraId"] == "1":
                timestamp = camera["lastSnapshot"]["timestamp"]
        
        imageBytes = response_json["result"][0]["image"]
        decodedBytes = base64.b64decode(imageBytes)

        return decodedBytes
        

