'''
Created on 11/08/2013

@author: djwhyte
'''
from PIL import Image as PILImage
from StringIO import StringIO
from gi.repository import GObject
import base64
import datetime
import json
import logging
import monitor.sqlexchanger
from monitor.cameramonitor import Event
import socket

#class Frame():
#    def __init__(self, cameraId, timestamp, frameNum, filename):
#        self.__logger = logging.getLogger("%s.Frame" % __name__)
#        self._cameraId = cameraId
#        self._timestamp = timestamp
#        self._frameNum = frameNum
#        self._filename = filename
#
#    def toJSON(self):
#        self.__logger.debug("Getting JSON")
#        jsonstr = {"cameraid": self._cameraId,
#                   "timestamp": self._timestamp.strftime("%Y-%m-%d %H:%M:%S"),
#                   "frame": self._frameNum,
#                   "filename": self._filename}
#        return jsonstr
#
#class EventFrame(Frame):
#    
#    def __init__(self, cameraId, eventId, timestamp, frameNum, filename, score):
#        self.__logger = logging.getLogger("%s.EventFrame" % __name__)
#        Frame.__init__(self, cameraId, timestamp, frameNum, filename)
#        self._eventId = eventId
#        self._score = score
#        
#    def toJSON(self):
#        self.__logger.debug("Getting JSON")
#        jsonstr = {"eventid": self._eventId,
#                   "cameraid": self._cameraId,
#                   "timestamp": self._timestamp.strftime("%Y-%m-%d %H:%M:%S"),
#                   "score": self._score,
#                   "frame": self._frame,
#                   "filename": self._filename}
#        return jsonstr
#
#
#class Event():
#    
#    def __init__(self, eventId, cameraId, startTime):
#        self.__logger = logging.getLogger("%s.Event" % __name__)
#        self._eventId = eventId
#        self._cameraId = cameraId
#        self._topScore = 0
#        self._startTime = startTime
#        self._topScoreFrame = None
#        self._frames = []
#        
##    def _include_frame(self, camera, filename, frame, score, file_type, time_stamp, text_event):
##        # See if this is the highest scoring frame
##        if score > self._topScore:
##            self._topScore = score
##            self._topScoreFrame = (camera, filename, frame, score, file_type, time_stamp, text_event)
##        
##        # Is this the earliest frame
##        if time_stamp < self._startTime:
##            self._startTime = time_stamp
##            
##        # Keep track of all the frames in this event
##        self._frames.append((camera, filename, frame, score, file_type, time_stamp, text_event))
#    
#    def toJSON(self):
#        self.__logger.debug("Getting JSON")
#        jsonstr = {"eventid": self._eventId,
#                   "cameraid": self._cameraId,
#                   "starttime": self._startTime.strftime("%Y-%m-%d %H:%M:%S"),
#                   "topScoreFrame": self._topScoreFrame,
#                   "frames": self._frames}
#        return jsonstr
#
#    @staticmethod        
#    def get(params):
#        sqlwriter = monitor.sqlexchanger.SQLWriter(monitor.sqlexchanger.DB().getConnection())
#        pass
#    
#    @staticmethod        
#    def list(params):
#        sqlwriter = monitor.sqlexchanger.SQLWriter(monitor.sqlexchanger.DB().getConnection())
#        
#        fromTimestamp = None
#        if "fromTimestamp" in params:
#            fromTimestamp = params["fromTimestamp"]
#        toTimestamp = None
#        if "toTimestamp" in params:
#            toTimestamp = params["toTimestamp"]
#        cameraIds = None
#        if "cameraIds" in params:
#            cameraIds = params["cameraIds"]
#        
#        dbEvents = sqlwriter.get_motion_events(fromTimestamp, toTimestamp, cameraIds)
#        events = []
#
#        for (event_id, camera_id, start_time) in dbEvents:
#            events.append(Event(event_id, camera_id, start_time))
#        
#        # Return the events as a list
#        return events
    

class Image():
    """This is an Image object, as represented in JSON"""

    _CONFIG_target_dir = '/data/motion/'
    _CONFIG_snapshot_filename = 'snapshots/camera%t/%Y/%m/%d/%H/%M/%S-snapshot.jpg'
    _CONFIG_motion_filename = 'motion/camera%t/%Y%m%d/%v/%Y%m%d-%H%M%S-%q.jpg'
    
    TYPE_MOTION = 1
    TYPE_SNAPSHOT = 2
    
    def __init__(self, cameraid = None, timestamp = None, thumbnail = False, include_image = False):
        self.__logger = logging.getLogger("%s.Image" % __name__)
        self._cameraid = cameraid
        self._timestamp = timestamp
        self._thumbnail = thumbnail
        self._include_image = include_image
    
    
    def toJSON(self):
        self.__logger.debug("Getting JSON")
        jsonstr = {"imageType": self._imageType(),
                   "cameraid": self._cameraid,
                   "timestamp": self._timestamp,
                   "path": self._path,
                   "thumbnail": self._thumbnail}
        if self._include_image:
            jsonstr["image"] = self._get_image_data()
        return jsonstr
    
    def _get_image_data(self):
        # Need to ensure we only serve up motion files.
        assert self._path.startswith("/data/motion/"), "Not a motion file: %s" % self._path
        
        # TODO: Need to only serve up jpeg files.

        with open(self._path, "rb") as image_file:
            if self._thumbnail:
                self.__logger.debug("Creating a thumbnail")
                size = 160, 120
                thumbnail = StringIO()
                im = PILImage.open(image_file)
                im.thumbnail(size, PILImage.ANTIALIAS)
                im.save(thumbnail, "JPEG")
                file_bytes = thumbnail.getvalue()
            else:
                file_bytes = image_file.read()

        encoded_string = base64.b64encode(file_bytes)
        self.__logger.debug("Returning encoded image bytes")
        return encoded_string

    @staticmethod
    def _decode_image_path(path, cameraid, timestamp):
        
        # Parse the string timestamp
        ts = datetime.datetime.strptime(timestamp, '%Y%m%d%H%M%S')
        
        # Inject the camera number
        path = path.replace("%t", cameraid)
        
        # Overlay the timestamp into the filepath
        path = ts.strftime(path)
        
        return path
    
    @staticmethod        
    def get(params):
        # Validate the params
        assert "type" in params, "No type is specified: %s" % params
        assert "cameraid" in params, "No cameraid is specified: %s" % params
        assert "timestamp" in params, "No timestamp is specified: %s" % params
        
        assert int(params["type"]) in [Image.TYPE_MOTION, Image.TYPE_SNAPSHOT], "Type is not recognised: %s" % params 
        
        cameraid = params["cameraid"]
        timestamp = params["timestamp"]
        
        # Optional thumbnail flag
        thumbnail = False
        if "thumbnail" in params:
            thumbnail = params["thumbnail"].upper() == "TRUE"
            
        # Optional include_image flag
        include_image = False
        if "include_image" in params:
            include_image = params["include_image"].upper() == "TRUE"
            
        if int(params["type"]) == Image.TYPE_MOTION:
            assert "event" in params, "No event is specified for motion image: %s" % params
            event = params["event"]
            return [MotionImage(cameraid, timestamp, event, thumbnail, include_image)]
        else:
            # Can only be a snapshot!
            return [SnapshotImage(cameraid, timestamp, thumbnail, include_image)]

class MotionImage(Image):
    def __init__(self, cameraid = None, timestamp = None, event = None, thumbnail = False, include_image = False):
        self.__logger = logging.getLogger("%s.MotionImage" % __name__)
        Image.__init__(self, cameraid, timestamp, thumbnail, include_image)
        self._event = event
        self._path = Image._CONFIG_target_dir + Image._CONFIG_motion_filename
        self._path = self._path.replace("%v", self._event)
        self._path = self._path.replace("%q", "00")
        self._path = Image._decode_image_path(self._path, self._cameraid, self._timestamp)
        self.__logger.debug("Getting JSON")

        
    def _imageType(self):
        return "motion"

class SnapshotImage(Image):
    def __init__(self, cameraid = None, timestamp = None, thumbnail = False, include_image = False):
        self.__logger = logging.getLogger("%s.SnapshotImage" % __name__)
        Image.__init__(self, cameraid, timestamp, thumbnail, include_image)

        self._path = Image._CONFIG_target_dir + Image._CONFIG_snapshot_filename
        self._path = Image._decode_image_path(self._path, self._cameraid, self._timestamp)

    def _imageType(self):
        return "snapshot"


class JSONInterface():
    
    __SERVER_ADDR = '127.0.0.1'
    __SERVER_PORT = 8889
    
    _CONFIG_target_dir = '/data/motion/'
    _CONFIG_snapshot_filename = 'snapshots/camera%t/%Y/%m/%d/%H/%M/%S-snapshot.jpg'

    def __init__(self, camera_monitor):
        self.__logger = logging.getLogger(__name__)
        
        self.__camera_monitor = camera_monitor
        
        # Initialise server and start listening.
        self.__socket = socket.socket()
        self.__socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.__logger.debug("binding to %s:%d" % (self.__SERVER_ADDR, self.__SERVER_PORT))
        self.__socket.bind((self.__SERVER_ADDR, self.__SERVER_PORT))
        self.__socket.listen(5)
        self.__logger.info("Listening...")
        
        # When there is data available, call the callback.
        GObject.io_add_watch(self.__socket.fileno(), GObject.IO_IN, 
                             self.__handle_json_request)
        
    def __validate_msg(self, msg):
        assert type(msg) == dict, "Message should be a dictionary: %s" % msg
        assert "method" in msg, "Message does not specify what method it is: %s" % msg
        self.__logger.debug("Got a message method of '%s'" % msg["method"])
        
        # Check we have a valid method
        assert msg["method"] in ["camera.get",
                                 "image.get",
                                 "event.list"]

        # Check that params have been provided, not necessarily valid params.
        assert "params" in msg, "Message does not specify any parameters: %s" % msg
        
            
    def __handle_json_request(self, fd, condition):
        response = {}

        try:
            self.__logger.debug("Need to handle JSON request.")
            # If it is the correct socket, read data from it.
            if fd == self.__socket.fileno():
                self.__logger.debug("In the if.")
                conn, addr = self.__socket.accept()
                self.__logger.debug("Have the conn, about to read.")
                # conn - socket to client
                # addr - clients address
                line = conn.recv(1024) #receive data from client
                
                self.__logger.debug("Rxd raw data: %s" % line)
                
                msg = json.loads(line)

                self.__validate_msg(msg)
            
                if msg["method"] == "camera.get":
                    cams_resp = []
                    for key, camera in self.__camera_monitor.get_cameras().items():
                        cams_resp.append(camera.toJSON())
                    response["camera"] = cams_resp
                
                if msg["method"] == "image.get":
                    results = Image.get(msg["params"])
                    results_json = []
                    for result in results:
                        results_json.append(result.toJSON())
                    response["result"] = results_json 
                
                if msg["method"] == "event.list":
                    results = Event.list(msg["params"])
                    results_json = []
                    for result in results:
                        results_json.append(result.toJSON())
                    response["result"] = results_json 
        except Exception as e:
            self.__logger.exception(e)
            error = {}
            error["code"] = 1
            error["message"] = "JSON Exception"
            error["data"] = str(e)
            response["error"] = error
        finally:
            if not conn is None:
                try:
                    self.__logger.debug("Sending response: %s" % response)
                    conn.send(json.dumps(response))
                    conn.close()
                except Exception as e:
                    self.__logger.exception(e)
            
        return True
