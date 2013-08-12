'''
Created on 11/08/2013

@author: djwhyte
'''
from gi.repository import GObject

import logging

class Camera():
    
    STATE_IDLE = 0
    STATE_ACTIVITY = 2
    STATE_LOST = 4
    
    def __init__(self, camera_id):
        self.__logger = logging.getLogger(__name__)

        self.__camera_id = camera_id
        
        self.__state = self.STATE_IDLE 
        
    def get_id(self):
        return self.__camera_id
    
    def get_state(self):
        return self.__state
        
    def handle_activity(self, msg):
        if msg["type"] == "event_start":
            self.__state = self.STATE_ACTIVITY
        if msg["type"] == "event_end":
            self.__state = self.STATE_IDLE
    
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
        
        self.__logger = logging.getLogger(__name__)
        self.__cameras = {}
        
        self.__logger.info("Initialised")

        
    def get_cameras(self):
        return self.__cameras
        
       
    def handle_motion_event(self, object, msg):
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
        
        return True
        
        
        
