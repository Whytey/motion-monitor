'''
Created on 11/08/2013

@author: djwhyte
'''
from collections import deque
from datetime import datetime
from gi.repository import GObject
import logging
import monitor.sqlexchanger

class Frame():
    def __init__(self, cameraId, timestamp, frameNum, filename):
        self.__logger = logging.getLogger("%s.Frame" % __name__)
        self._cameraId = cameraId
        self._timestamp = timestamp
        self._frameNum = frameNum
        self._filename = filename

    def toJSON(self):
        self.__logger.debug("Getting JSON")
        jsonstr = {"cameraId": self._cameraId,
                   "timestamp": self._timestamp.strftime("%Y%m%d%H%M%S"),
                   "frame": self._frameNum,
                   "filename": self._filename}
        return jsonstr

    @staticmethod
    def fromSocketMsg(msg):
        # self.__logger.debug("Creating Frame from socket message: %s" % msg)
        cameraId = msg["camera"]
        timestamp = datetime.strptime(msg["timestamp"], "%Y%m%d%H%M%S")
        frameNum = msg["frame"]
        filename = msg["file"]
        return Frame(cameraId, timestamp, frameNum, filename)
    
    @staticmethod        
    def get(params):
        sqlwriter = monitor.sqlexchanger.SQLWriter()

        assert "cameraId" in params, "No cameraId is specified: %s" % params
        assert "startTime" in params, "No startTime is specified: %s" % params
        assert "units" in params, "No units is specified: %s" % params
        assert "count" in params, "No count is specified: %s" % params
        
        cameraId = params["cameraId"]        
        startTime = params["startTime"]        
        units = params["units"]        
        count = params["count"]
        
        minuteCount = 0
        hourCount = 0
        dayCount = 0
        weekCount = 0
        monthCount = 0
        
        if units.lower() == "minute":
            minuteCount = count
        elif units.lower() == "hour":
            hourCount = count
        elif units.lower() == "day":
            dayCount = count
        elif units.lower() == "week":
            weekCount = count
        elif units.lower() == "month":
            monthCount = count
        
        dbFrames = sqlwriter.get_timelapse_snapshot_frames(cameraId, 
                                                           startTime, 
                                                           minuteCount, 
                                                           hourCount, 
                                                           dayCount, 
                                                           weekCount, 
                                                           monthCount)
        frames = []

        for (cameraId, timestamp, frame, filename) in dbFrames:
            frames.append(Frame(cameraId, timestamp, frame, filename))
        
        # Return the frames as a list
        return frames
        

class EventFrame(Frame):
    
    def __init__(self, cameraId, eventId, timestamp, frameNum, filename, score):
        self.__logger = logging.getLogger("%s.EventFrame" % __name__)
        Frame.__init__(self, cameraId, timestamp, frameNum, filename)
        self._eventId = eventId
        self._score = score
        
    def toJSON(self):
        self.__logger.debug("Getting JSON")
        jsonstr = {"eventId": self._eventId,
                   "cameraId": self._cameraId,
                   "timestamp": self._timestamp.strftime("%Y%m%d%H%M%S"),
                   "score": self._score,
                   "frame": self._frameNum,
                   "filename": self._filename}
        return jsonstr

    @staticmethod
    def fromSocketMsg(msg):
        # self.__logger.debug("Creating EventFrame from socket message: %s" % msg)
        cameraId = msg["camera"]
        eventId = msg["event"]
        timestamp = datetime.strptime(msg["timestamp"], "%Y%m%d%H%M%S")
        frameNum = msg["frame"]
        filename = msg["file"]
        score = msg["score"]
        return EventFrame(cameraId, eventId, timestamp, frameNum, filename, score)


class Event():
    
    def __init__(self, eventId, cameraId, startTime):
        self.__logger = logging.getLogger("%s.Event" % __name__)
        self._eventId = eventId
        self._cameraId = cameraId
        self._startTime = startTime
        self._topScoreFrame = None
        self._frames = []

    def __str__(self):
        return "%s for camera %s" % (self._eventId, self._cameraId)
        
    def _include_frame(self, eventFrame):
        # See if this is the highest scoring frame
        if not self._topScoreFrame or (self._topScoreFrame and 
                                       eventFrame._score > self._topScoreFrame._score):
            self._topScoreFrame = eventFrame
        # Keep track of all the frames in this event
        self._frames.append(eventFrame)
            
    def toJSON(self, extended=False):
        self.__logger.debug("Getting JSON")
        
        topScoreFrame_json = None
        if self._topScoreFrame:
            topScoreFrame_json = self._topScoreFrame.toJSON()

        jsonstr = {"eventId": self._eventId,
                   "cameraId": self._cameraId,
                   "startTime": self._startTime.strftime("%Y%m%d%H%M%S"),
                   "topScoreFrame": topScoreFrame_json}
        
        if extended:
            frames_json = []
            for frame in self._frames:
                frames_json.append(frame.toJSON())

            jsonstr["frames"] = frames_json
        return jsonstr
    
    @staticmethod
    def fromSocketMsg(msg):
        # self.__logger.debug("Creating Event from socket message: %s" % msg)
        eventId = msg["event"]
        cameraId = msg["camera"]
        startTime = datetime.strptime(msg["timestamp"], "%Y%m%d%H%M%S")
        return Event(eventId, cameraId, startTime)
    
    @staticmethod        
    def get(params):
        sqlwriter = monitor.sqlexchanger.SQLWriter()

        assert "eventId" in params, "No eventId is specified: %s" % params
        assert "cameraId" in params, "No cameraId is specified: %s" % params
        
        eventId = params["eventId"]        
        cameraId = params["cameraId"]        
        
        dbFrames = sqlwriter.get_motion_event_frames(eventId, cameraId)
        
        events = []
        
        if len(dbFrames) > 0:
            eventId = dbFrames[0][0]
            cameraId = dbFrames[0][1]
            startTime = dbFrames[0][2]
            event = Event(eventId, cameraId, startTime)

            for (eventId, cameraId, timestamp, frameNum, score, filename) in dbFrames:
                eventFrame = EventFrame(cameraId, eventId, timestamp, frameNum, filename, score)
                event._include_frame(eventFrame)
                
            events.append(event)
        
        # Return the events as a list
        return events
    
    @staticmethod        
    def list(params):
        # Returns the list of motion events from the DB only.
        sqlwriter = monitor.sqlexchanger.SQLWriter()
        
        fromTimestamp = None
        if "fromTimestamp" in params:
            fromTimestamp = params["fromTimestamp"]
        toTimestamp = None
        if "toTimestamp" in params:
            toTimestamp = params["toTimestamp"]
        cameraIds = None
        if "cameraIds" in params:
            cameraIds = params["cameraIds"]
        
        dbEvents = sqlwriter.get_motion_events(fromTimestamp, toTimestamp, cameraIds)
        events = []

        for (event_id, camera_id, start_time) in dbEvents:
            events.append(Event(event_id, camera_id, start_time))
        
        # Return the events as a list
        return events
    
class Camera():
    
    FTYPE_IMAGE = 1
    FTYPE_IMAGE_SNAPSHOT = 2
    FTYPE_IMAGE_MOTION = 4
    FTYPE_MPEG = 8
    FTYPE_MPEG_MOTION = 16
    FTYPE_MPEG_TIMELAPSE = 32
    
    STATE_IDLE = 0
    STATE_ACTIVITY = 2
    STATE_LOST = 4
    
    def __init__(self, cameraId):
        self.__logger = logging.getLogger("%s.%s" % (self.__class__.__module__, self.__class__.__name__))

        self.__cameraId = cameraId
        self.__state = self.STATE_IDLE 
        self.__last_snapshot = None
        self.__recent_motion = deque([], 10)
        
    @property
    def id(self):
        return self.__cameraId
        
    @property
    def state(self):
        return self.__state

    def handle_activity(self, msg):
        if msg["type"] == "event_start":
            self.__state = self.STATE_ACTIVITY
            # We need an Event
            newEvent = Event.fromSocketMsg(msg)
            self.__logger.info("Created new event: %s" % newEvent)
            self.__recent_motion.appendleft(newEvent)
            self.__logger.debug("Last motion: %s" % self.__recent_motion)
        if msg["type"] == "event_end":
            self.__state = self.STATE_IDLE
            
    def handle_picture(self, msg):
        try:
            filetype = int(msg["filetype"])
            if filetype == self.FTYPE_IMAGE_SNAPSHOT:
                self.__logger.debug("Handling a snapshot")
                self.__last_snapshot = Frame.fromSocketMsg(msg)
            
            if filetype == self.FTYPE_IMAGE:
                self.__logger.debug("Handling motion image")
                eventFrame = EventFrame.fromSocketMsg(msg)
                try:
                    self.__recent_motion[0]._include_frame(eventFrame)
                except IndexError as e:
                    self.__logger.warning("Must have missed the start of an event, forcing creation")
                    newEvent = Event(eventFrame._eventId, eventFrame._cameraId, eventFrame._timestamp)
                    self.__logger.info("Created new event: %s" % newEvent)
                    self.__recent_motion.appendleft(newEvent)
                    self.__recent_motion[0]._include_frame(eventFrame)
        except ValueError:
            self.__logger.warning("Received an unexpected filetype: %s" % msg["filetype"])
            
    def toJSON(self):
        self.__logger.debug("Getting JSON")

        recent_motion_json = []
        for event in self.__recent_motion:
            recent_motion_json.append(event.toJSON())
            
        last_snapshot_json = None
        if self.__last_snapshot:
            last_snapshot_json = self.__last_snapshot.toJSON()
            
        return {"cameraId": self.__cameraId,
                "state": self.__state,
                "lastSnapshot": last_snapshot_json,
                "recentMotion": recent_motion_json}
    
class CameraMonitor(GObject.GObject):
    
    ACTIVITY_EVENT = "event_state"
    MOTION_DETECTED_EVENT = "motion_detected"
    
    __gsignals__ = {
        ACTIVITY_EVENT: (GObject.SIGNAL_RUN_LAST, None,
                                (GObject.TYPE_PYOBJECT,)),
        MOTION_DETECTED_EVENT: (GObject.SIGNAL_RUN_LAST, None,
                                (GObject.TYPE_PYOBJECT,))
    }

    def __init__(self, config):
        GObject.GObject.__init__(self)
        
        self.__logger = logging.getLogger("%s.%s" % (self.__class__.__module__, self.__class__.__name__))
        self.__cameras = {}
        
        self.__logger.info("Initialised")

        
    def get_cameras(self):
        return self.__cameras
        
       
    def handle_motion_event(self, object, msg):
        try:
            self.__logger.debug("Handling a message: %s" % msg)
            
            # Get the camera responsible for this event.
            camera_id = msg["camera"]
            if not self.__cameras.has_key(camera_id):
                # This is the first time we have encountered this camera
                self.__logger.info("Creating an object for camera %s" % camera_id)
                camera = Camera(camera_id)
                self.__cameras[camera_id] = camera
                
            camera = self.__cameras[camera_id]
            
            if msg["type"] in ["event_end", "event_start"]:
                camera.handle_activity(msg)
                self.emit(self.ACTIVITY_EVENT, camera)
                
            if msg["type"] in ["picture_save"]:
                camera.handle_picture(msg)
        
        except Exception as e:
            self.__logger.exception(e)
            raise
        return True
        
        
        
