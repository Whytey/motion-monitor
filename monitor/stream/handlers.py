'''
Created on 09/04/2014

@author: djwhyte
'''

from abc import ABCMeta, abstractmethod
import base64
import datetime
import json
import logging
import socket
import time

def _request_data(data):
    # Get the data from the socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    sock.connect(('192.168.0.98', 8889))
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

    def __init__(self, request):
        self.__logger = logging.getLogger("%s.BaseHandler" % __name__)
        self._responseHeaders= {}
        self._request = request
        
    def __iter__(self):
        return self
    
    @abstractmethod
    def next(self):
        pass
        
    def getResponseHeaders(self):
        return self._responseHeaders
    
class AbstractFrameHandler(BaseHandler):

    def __init__(self, request):
        self.__logger = logging.getLogger("%s.AbstractFrameHandler" % __name__)
        BaseHandler.__init__(self, request)
        
        self._bytes = self._generateBytes()
        
        self._responseHeaders["Access-Control-Allow-Origin"] = "*"
        self._responseHeaders["Content-Type"] = "image/jpeg"
        self._responseHeaders["Content-Length"] = str(len(self._bytes))
        
        self.__providedData = False
        
    def next(self):
        if self.__providedData:
            raise StopIteration
        else:
            self.__providedData = True
            return self._bytes

    @abstractmethod
    def _generateBytes(self):
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
        try:
            imageBytes = response_json["result"][0]["image"]
            decodedBytes = base64.b64decode(imageBytes)
        except KeyError, e:
            raise KeyError(e + response_json)

        return decodedBytes
            

class SnapshotFrameHandler(AbstractFrameHandler):
    
    def __init__(self, request):
        self.__logger = logging.getLogger("%s.SnapshotFrameHandler" % __name__)
        AbstractFrameHandler.__init__(self, request)
        
    def _generateBytes(self):
        # Get this requests params
        try:
            cameraId = self._request["cameraId"]
            timestamp = self._request["timestamp"]
            frame = self._request["frame"]
        except KeyError, e:
            # One of the above required values are not provided in the request
            raise e
        
        # Return the bytes for the snapshot frame
        return AbstractFrameHandler._getFrameBytes(cameraId, timestamp, frame)

class MotionFrameHandler(AbstractFrameHandler):
    
    def __init__(self, request):
        self.__logger = logging.getLogger("%s.MotionFrameHandler" % __name__)
        AbstractFrameHandler.__init__(self, request)
    
    def _generateBytes(self):
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
        return AbstractFrameHandler._getFrameBytes(cameraId, timestamp, frame, eventId)

class LiveFrameHandler(AbstractFrameHandler):
    
    def __init__(self, request):
        self.__logger = logging.getLogger("%s.LiveFrameHandler" % __name__)
        AbstractFrameHandler.__init__(self, request)

    def _generateBytes(self):
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
        return AbstractFrameHandler._getFrameBytes(cameraId, timestamp, frame)
    
class AbstractVideoHandler(BaseHandler):
    def __init__(self, request):
        self.__logger = logging.getLogger("%s.AbstractVideoHandler" % __name__)
        BaseHandler.__init__(self, request)
    
        self._boundary = '--boundarydonotcross'
        
        self._responseHeaders["Access-Control-Allow-Origin"] = "*"
        self._responseHeaders["Cache-Control"] = "no-store, no-cache, must-revalidate, pre-check=0, post-check=0, max-age=0"
        self._responseHeaders["Connection"] = "close"
        self._responseHeaders["Content-Type"] = "multipart/x-mixed-replace;boundary=%s" % self._boundary
        self._responseHeaders["Expires"] = "Mon, 3 Jan 2000 12:34:56 GMT"
        self._responseHeaders["Pragma"] = "no-cache"
        
    @abstractmethod
    def _generateFrameBytes(self):
        pass
        
    def next(self):
        
        frameBytes = self._generateFrameBytes()
        
        if frameBytes is None:
            raise StopIteration
        
        imageHeaders = {'X-Timestamp': time.time(),
                        'Content-Length': len(frameBytes),
                        'Content-Type': 'image/jpeg'
                        }

        frameResponse = []
        # Provide the boundary
        frameResponse.append(self._boundary)
        frameResponse.append("\r\n")
        
        # Provide the image header
        for k, v in imageHeaders.items():
            frameResponse.append("%s: %s" % (k, v))
            frameResponse.append("\r\n")
        
        # Provide an empty line
        frameResponse.append("\r\n")
        
        # Provide the image data
        frameResponse.append(frameBytes)
        frameResponse.append("\r\n")
        time.sleep(0.08)
        return "".join(frameResponse)
        
class LiveVideoHandler(AbstractVideoHandler):
    def __init__(self, request):
        self.__logger = logging.getLogger("%s.LiveVideoHandler" % __name__)
        AbstractVideoHandler.__init__(self, request)

    def _generateFrameBytes(self):
        return LiveFrameHandler(self._request)._generateBytes()

class MotionVideoHandler(AbstractVideoHandler):
    def __init__(self, request):
        self.__logger = logging.getLogger("%s.MotionVideoHandler" % __name__)
        AbstractVideoHandler.__init__(self, request)

        try:
            self._cameraId = self._request["cameraId"]
            eventId = self._request["eventId"]
        except Exception, e:    
            # One of the above required values are not provided in the request
            raise e

        self._frames = []
        # Get the timelapse snapshots
        request = {"method": "event.get",
                   "params": {"cameraId": self._cameraId,
                              "eventId": eventId}
                   }
        response = _request_data(request)
        response_json = json.loads(response)
        self._frames = response_json["result"][0]["frames"]

    def _generateFrameBytes(self):
        if len(self._frames) > 0:
            frame = self._frames.pop(0)
            request = {"eventId": frame["eventId"],
                       "cameraId" : str(frame["cameraId"]),
                       "timestamp": frame["timestamp"],
                       "frame": str(frame["frame"])}
            return MotionFrameHandler(request)._generateBytes()
        else:
            return None

    
class TimelapseVideoHandler(AbstractVideoHandler):
    
    def __init__(self, request):
        self.__logger = logging.getLogger("%s.TimelapseVideoHandler" % __name__)
        AbstractVideoHandler.__init__(self, request)
        
        try:
            self._cameraId = self._request["cameraId"]
            fromTimestamp = self._request["fromTimestamp"]
            units = self._request["units"]
            count = int(self._request["count"])
        except Exception, e:    
            # One of the above required values are not provided in the request
            raise e

        self._frames = []
        
        # Get the timelapse snapshots
        request = {"method": "snapshot.get",
                   "params": {"cameraId": self._cameraId,
                              "startTime": fromTimestamp, 
                              "units": units, 
                              "count": count}
                   }
        response = _request_data(request)
        response_json = json.loads(response)
        self._frames = response_json["result"]

    def _generateFrameBytes(self):
        if len(self._frames) > 0:
            frame = self._frames.pop(0)
            request = {"cameraId" : str(frame["cameraId"]),
                       "timestamp": frame["timestamp"],
                       "frame": str(frame["frame"])}
            return SnapshotFrameHandler(request)._generateBytes()
        else:
            return None
