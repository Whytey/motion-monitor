import logging
from collections import deque

from motionmonitor.utils import FixedSizeOrderedDict


class Frame:
    def __init__(self, camera_id, timestamp, frame_num, filename):
        self.__logger = logging.getLogger("%s.Frame" % __name__)
        self._camera_id = camera_id
        self._timestamp = timestamp
        self._frame_num = frame_num
        self._filename = filename

    @property
    def camera_id(self):
        return self._camera_id

    @property
    def id(self):
        return self.create_id(self._timestamp, self._frame_num)

    @property
    def timestamp(self):
        return self._timestamp

    @property
    def frame_num(self):
        return self._frame_num

    @property
    def filename(self):
        return self._filename

    @staticmethod
    def create_id(timestamp, frame_num):
        return "{}_{}".format(timestamp.strftime("%Y%m%d%H%M%S"), frame_num)

    def to_json(self):
        self.__logger.debug("Getting JSON")
        json_str = {"cameraId": self._camera_id,
                    "timestamp": self._timestamp.strftime("%Y%m%d%H%M%S"),
                    "frame": self._frame_num,
                    "filename": self._filename}
        return json_str


class EventFrame(Frame):

    def __init__(self, camera_id, event_id, timestamp, frame_num, filename, score):
        self.__logger = logging.getLogger("%s.EventFrame" % __name__)
        Frame.__init__(self, camera_id, timestamp, frame_num, filename)
        self._event_id = event_id
        self._score = score

    @property
    def event_id(self):
        return self._event_id

    @property
    def score(self):
        return self._score

    def to_json(self):
        self.__logger.debug("Getting JSON")
        json_str = {"eventId": self._event_id,
                    "cameraId": self._camera_id,
                    "timestamp": self._timestamp.strftime("%Y%m%d%H%M%S"),
                    "score": self._score,
                    "frame": self._frame_num,
                    "filename": self._filename}
        return json_str


class Event:

    def __init__(self, event_id, camera_id, start_time):
        self.__logger = logging.getLogger("%s.Event" % __name__)
        self._event_id = event_id
        self._camera_id = camera_id
        self._start_time = start_time
        self._top_score_frame = None
        self._frames = []

    def __str__(self):
        return "%s for camera %s" % (self._event_id, self._camera_id)

    @property
    def id(self):
        return self._event_id

    @property
    def camera_id(self):
        return self._camera_id

    @property
    def start_time(self):
        return self._start_time

    @property
    def top_score_frame(self):
        return self._top_score_frame

    def append_frame(self, event_frame):
        self.__logger.debug("Got a new event frame: {}".format(event_frame))
        # See if this is the highest scoring frame
        if not self._top_score_frame or (self._top_score_frame and
                                         event_frame.score > self._top_score_frame.score):
            self.__logger.debug("It's a new top score")
            self._top_score_frame = event_frame
        # Keep track of all the frames in this event
        self._frames.append(event_frame)

    def to_json(self, extended=False):
        self.__logger.debug("Getting JSON")

        top_score_frame_json = None
        if self._top_score_frame:
            top_score_frame_json = self._top_score_frame.to_json()

        json_str = {"eventId": self._event_id,
                    "cameraId": self._camera_id,
                    "startTime": self._start_time.strftime("%Y%m%d%H%M%S"),
                    "topScoreFrame": top_score_frame_json}

        if extended:
            frames_json = []
            for frame in self._frames:
                frames_json.append(frame.to_json())

            json_str["frames"] = frames_json
        return json_str


class Camera:
    STATE_IDLE = 0
    STATE_ACTIVITY = 2
    STATE_LOST = 4

    def __init__(self, camera_id):
        self.__logger = logging.getLogger("%s.%s" % (self.__class__.__module__, self.__class__.__name__))

        self.__camera_id = camera_id
        self.__state = self.STATE_IDLE
        self.__recent_snapshots = FixedSizeOrderedDict(max=1800)
        self.__recent_motion = FixedSizeOrderedDict(max=100)

    @property
    def id(self):
        return self.__camera_id

    @property
    def state(self):
        return self.__state

    @property
    def recent_snapshots(self):
        return self.__recent_snapshots

    @property
    def last_snapshot(self):
        if len(self.__recent_snapshots) > 0:
            self.__logger.debug("We have recent snapshots, getting the latest one")
            return list(self.__recent_snapshots.values())[-1]
        return None

    @property
    def recent_motion(self):
        return self.__recent_motion

    def append_snapshot_frame(self, frame):
        self.__recent_snapshots[Frame.create_id(frame.timestamp, frame.frame_num)] = frame

    def to_json(self):
        self.__logger.debug("Getting JSON for camera: {}".format(self))

        recent_motion_json = []
        for event in self.__recent_motion:
            recent_motion_json.append(event.to_json())

        last_snapshot_json = None
        if self.last_snapshot:
            last_snapshot_json = self.last_snapshot.to_json()

        return {"cameraId": self.__camera_id,
                "state": self.__state,
                "lastSnapshot": last_snapshot_json,
                "recentMotion": recent_motion_json}
