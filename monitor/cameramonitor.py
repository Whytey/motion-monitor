'''
Created on 11/08/2013

@author: djwhyte
'''
from gi.repository import GObject

import logging

class MotionEvent():
    
    def __init__(self, msg):
        self.__logger = logging.getLogger("%s.MotionEvent" % __name__)
        
        self.__logger.debug("Initialising with msg: %s" % msg)

        self.__starttime = msg["timestamp"]
        self.__event_id = 0
        self.__bestimage = None
        self.__bestimage_score = 0
        self.__bestimage_time = None
        
    def handle_image(self, msg):
        self.__logger.debug("Handling an image")
        try:
            score = int(msg["score"])
            if score > self.__bestimage_score:
                self.__logger.debug("Score of %d is better than %d" % (score, self.__bestimage_score))
                self.__bestimage_score = score
                self.__bestimage = msg["file"] 
                self.__bestimage_time = msg["timestamp"]
        except ValueError:
            self.__logger.warning("Unable to cast the score: %s" % msg["score"])
            pass
        
    def toJSON(self):
        self.__logger.debug("Getting JSON")
        return {"starttime": self.__starttime,
                "event_id": self.__event_id,
                "best_image": self.__bestimage,
                "best_image_score": self.__bestimage_score,
                "best_image_time": self.__bestimage_time}

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
    
    def __init__(self, camera_id):
        self.__logger = logging.getLogger("%s.Camera" % __name__)

        self.__camera_id = camera_id
        self.__state = self.STATE_IDLE 
        
        self.__last_snapshot_path = None
        self.__last_snapshot_timestamp = None
        self.__last_motion = None
        
    def get_id(self):
        return self.__camera_id
    
    def get_state(self):
        return self.__state
    
    def get_last_snapshot(self):
        return self.__last_snapshot_path
    
    def get_last_motion(self):
        return self.__last_motion
        
    def handle_activity(self, msg):
        if msg["type"] == "event_start":
            self.__state = self.STATE_ACTIVITY
            # We need a MotionEvent
            self.__last_motion = MotionEvent(msg)
            self.__logger.debug("Last motion: %s" % self.__last_motion)
        if msg["type"] == "event_end":
            self.__state = self.STATE_IDLE
            
    def handle_picture(self, msg):
        try:
            filetype = int(msg["filetype"])
            if filetype == self.FTYPE_IMAGE_SNAPSHOT:
                self.__logger.debug("Handling a snapshot")
                self.__last_snapshot_path = msg["file"]
                self.__last_snapshot_timestamp = msg["timestamp"]
            
            if filetype == self.FTYPE_IMAGE:
                self.__logger.debug("Handling motion image")
                self.__last_motion.handle_image(msg)
        except ValueError:
            self.__logger.warning("Received an unexpected filetype: %s" % msg["filetype"])
            
    def toJSON(self):
        self.__logger.debug("Getting JSON")
        if self.__last_motion is None:
            last_motion_json = None
        else:
            last_motion_json = self.__last_motion.toJSON()
            
        recent_motion_json = []
        recent_motion_json.append(last_motion_json)
        return {"id": self.__camera_id, 
                "state": self.__state, 
                "last_snapshot_path": self.__last_snapshot_path,
                "last_snapshot_timestamp": self.__last_snapshot_timestamp,
                "recent_motion": recent_motion_json}
    
class CameraMonitor(GObject.GObject):
    
    ACTIVITY_EVENT = "event_state"
    MOTION_DETECTED_EVENT = "motion_detected"
    
    __gsignals__ = {
        ACTIVITY_EVENT: (GObject.SIGNAL_RUN_LAST, None, 
                                (GObject.TYPE_PYOBJECT,)),
        MOTION_DETECTED_EVENT: (GObject.SIGNAL_RUN_LAST, None, 
                                (GObject.TYPE_PYOBJECT,))
    }

    def __init__(self):
        GObject.GObject.__init__(self)
        
        self.__logger = logging.getLogger("%s.CameraMonitor" % __name__)
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
        
        
        
