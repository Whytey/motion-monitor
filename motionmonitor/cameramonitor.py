'''
Created on 11/08/2013

@author: djwhyte
'''
import logging

from models import Camera, Event
from motionmonitor.const import (
    EVENT_MOTION_EVENT_START,
    EVENT_MOTION_EVENT_END,
    EVENT_NEW_FRAME,
    EVENT_NEW_MOTION_FRAME
)


class CameraMonitor():

    def __init__(self, mm):
        self.__logger = logging.getLogger("%s.%s" % (self.__class__.__module__, self.__class__.__name__))

        self.mm = mm
        self.mm.bus.listen(EVENT_MOTION_EVENT_START, self.handle_motion_start)
        self.mm.bus.listen(EVENT_MOTION_EVENT_END, self.handle_motion_end)
        self.mm.bus.listen(EVENT_NEW_FRAME, self.handle_snapshot_frame)
        self.mm.bus.listen(EVENT_NEW_MOTION_FRAME, self.handle_motion_frame)

        self.__logger.info("Initialised")

    def handle_motion_start(self, event):
        pass
        # self.__state = self.STATE_ACTIVITY
        # self.__recent_motion.appendleft(new_event)
        # self.__logger.debug("Last motion: %s" % self.__recent_motion)

    def handle_motion_end(self, event):
        pass
        # self.__state = self.STATE_IDLE

    def handle_snapshot_frame(self, event):
        frame = event.data
        if frame.camera_id not in self.mm.cameras:
            self.__create_camera(frame.camera_id)

        self.mm.cameras[frame.camera_id].append_snapshot_frame(frame)

    def handle_motion_frame(self, event):
        motion_frame = event.data
        if motion_frame.camera_id not in self.mm.cameras:
            self.__create_camera(motion_frame.camera_id)

        if len(self.mm.cameras[motion_frame.camera_id].recent_motion) == 0 or \
                self.mm.cameras[motion_frame.camera_id].recent_motion[0].event_id != motion_frame.event_id:
            self.__logger.warning(
                "Must have missed the start event '{}', forcing creation".format(motion_frame.event_id))
            new_event = Event(motion_frame.event_id, motion_frame.camera_id, motion_frame.timestamp)
            self.__logger.info("Created new event: {}".format(new_event))
            self.mm.cameras[motion_frame.camera_id].recent_motion.appendleft(new_event)

        self.mm.cameras[motion_frame.camera_id].recent_motion[0].append_frame(motion_frame)

    def __create_camera(self, camera_id):
        self.__logger.info("Creating a new camera: {}".format(camera_id))
        self.mm.cameras[camera_id] = Camera(camera_id)
