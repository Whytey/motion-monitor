import logging
from collections import deque


class Frame:
    def __init__(self, cameraId, timestamp, frameNum, filename):
        self.__logger = logging.getLogger("%s.Frame" % __name__)
        self._cameraId = cameraId
        self._timestamp = timestamp
        self._frameNum = frameNum
        self._filename = filename

    @property
    def camera_id(self):
        return self._cameraId

    @property
    def timestamp(self):
        return self._timestamp

    @property
    def frameNum(self):
        return self._frameNum

    @property
    def filename(self):
        return self._filename

    def toJSON(self):
        self.__logger.debug("Getting JSON")
        jsonstr = {"cameraId": self._cameraId,
                   "timestamp": self._timestamp.strftime("%Y%m%d%H%M%S"),
                   "frame": self._frameNum,
                   "filename": self._filename}
        return jsonstr

    @staticmethod
    def get(sqlreader, params):

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

        dbFrames = sqlreader.get_timelapse_snapshot_frames(cameraId,
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

    @property
    def event_id(self):
        return self._eventId

    @property
    def score(self):
        return self._score

    def toJSON(self):
        self.__logger.debug("Getting JSON")
        jsonstr = {"eventId": self._eventId,
                   "cameraId": self._cameraId,
                   "timestamp": self._timestamp.strftime("%Y%m%d%H%M%S"),
                   "score": self._score,
                   "frame": self._frameNum,
                   "filename": self._filename}
        return jsonstr


class Event:

    def __init__(self, eventId, cameraId, startTime):
        self.__logger = logging.getLogger("%s.Event" % __name__)
        self._eventId = eventId
        self._cameraId = cameraId
        self._startTime = startTime
        self._topScoreFrame = None
        self._frames = []

    def __str__(self):
        return "%s for camera %s" % (self._eventId, self._cameraId)

    @property
    def id(self):
        return self._eventId

    @property
    def camera_id(self):
        return self._cameraId

    def append_frame(self, eventFrame):
        self.__logger.debug("Got a new event frame: {}".format(eventFrame))
        # See if this is the highest scoring frame
        if not self._topScoreFrame or (self._topScoreFrame and
                                       eventFrame._score > self._topScoreFrame._score):
            self.__logger.debug("It's a new top score")
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
    def get(sqlreader, params):
        assert "eventId" in params, "No eventId is specified: %s" % params
        assert "cameraId" in params, "No cameraId is specified: %s" % params

        eventId = params["eventId"]
        cameraId = params["cameraId"]

        dbFrames = sqlreader.get_motion_event_frames(eventId, cameraId)

        events = []

        if len(dbFrames) > 0:
            eventId = dbFrames[0][0]
            cameraId = dbFrames[0][1]
            startTime = dbFrames[0][2]
            event = Event(eventId, cameraId, startTime)

            for (eventId, cameraId, timestamp, frameNum, score, filename) in dbFrames:
                eventFrame = EventFrame(cameraId, eventId, timestamp, frameNum, filename, score)
                event.append_frame(eventFrame)

            events.append(event)

        # Return the events as a list
        return events

    @staticmethod
    def list(sqlreader, params):
        fromTimestamp = None
        if "fromTimestamp" in params:
            fromTimestamp = params["fromTimestamp"]
        toTimestamp = None
        if "toTimestamp" in params:
            toTimestamp = params["toTimestamp"]
        cameraIds = None
        if "cameraIds" in params:
            cameraIds = params["cameraIds"]

        dbEvents = sqlreader.get_motion_events(fromTimestamp, toTimestamp, cameraIds)
        events = []

        for (event_id, camera_id, start_time) in dbEvents:
            events.append(Event(event_id, camera_id, start_time))

        # Return the events as a list
        return events


class Camera:
    STATE_IDLE = 0
    STATE_ACTIVITY = 2
    STATE_LOST = 4

    def __init__(self, camera_id):
        self.__logger = logging.getLogger("%s.%s" % (self.__class__.__module__, self.__class__.__name__))

        self.__cameraId = camera_id
        self.__state = self.STATE_IDLE
        self.__recent_snapshots = deque([], 1000)
        self.__recent_motion = deque([], 10)

    @property
    def id(self):
        return self.__cameraId

    @property
    def state(self):
        return self.__state

    @property
    def last_snapshot(self):
        if len(self.__recent_snapshots) > 0:
            return self.__recent_snapshots[-1]
        return None

    @property
    def recent_motion(self):
        return self.__recent_motion

    def append_snapshot_frame(self, frame):
        self.__recent_snapshots.appendleft(frame)

    def toJSON(self):
        self.__logger.debug("Getting JSON for camera: {}".format(self))

        recent_motion_json = []
        for event in self.__recent_motion:
            recent_motion_json.append(event.toJSON())

        last_snapshot_json = None
        if self.last_snapshot:
            last_snapshot_json = self.last_snapshot.toJSON()

        return {"cameraId": self.__cameraId,
                "state": self.__state,
                "lastSnapshot": last_snapshot_json,
                "recentMotion": recent_motion_json}
