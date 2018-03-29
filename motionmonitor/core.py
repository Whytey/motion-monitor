import logging
import time
from collections import OrderedDict

import motionmonitor.cameramonitor
import motionmonitor.config
import motionmonitor.extensions.zabbixwriter
import motionmonitor.filemanager
import motionmonitor.jsoninterface
import motionmonitor.socketlistener
import motionmonitor.sqlexchanger
from motionmonitor.const import (
    MATCH_ALL, EVENT_JOB, MAX_JOBQ_SIZE
)


class MotionMonitor(object):

    def __init__(self):
        self.__logger = logging.getLogger("%s.%s" % (self.__class__.__module__, self.__class__.__name__))

        self.config = motionmonitor.config
        self.bus = EventBus(self)

        self._jobs = OrderedDict()

        self.bus.listen(EVENT_JOB, self.job_handler)

        self.__socket_listener = motionmonitor.socketlistener.SocketListener(self)
        self.__camera_monitor = motionmonitor.cameramonitor.CameraMonitor(self)
        self.__zabbixwriter = motionmonitor.extensions.zabbixwriter.ZabbixWriter(self)
        self.__live_sqlwriter = motionmonitor.sqlexchanger.SQLWriter(self)

        # This is the sweeper and auditor.
        self.__sweeper = motionmonitor.filemanager.Sweeper(self)
        self.__auditor = motionmonitor.filemanager.Auditor(self)

        self.__json_interface = motionmonitor.jsoninterface.JSONInterface(self, self.__camera_monitor)

        self.__logger.info("Initialised...")

    def job_handler(self, event):
        self.__logger.debug("Handling a job event: {}".format(event))
        job = event.data
        self._jobs[job.id] = job
        while (len(self._jobs) > MAX_JOBQ_SIZE):
            self.__logger.debug("Too many jobs in the queue, popping the oldest")
            self._jobs.popitem(False)

class Job:
    def __init__(self, name):
        self.__logger = logging.getLogger("%s.%s" % (self.__class__.__module__, self.__class__.__name__))

        self.id = "{}-{}".format(name, time.time())
        self.name = name
        self.__progress = 0
        self.progress_description = ""
        self.__update_time = None

    def update_status(self, progress, description):
        self.progress = progress
        self.progress_description = description
        self.__update_time = time.time()

    def start(self):
        self.update_status(0, "Started")

    @property
    def progress(self):
        return self.__progress

    def __repr__(self):
        """Return the representation."""
        return "<Job {}: {}, {}%>".format(self.id, self.__progress, self.__update_time)

class Event(object):
    """Representation of an event within the bus."""

    def __init__(self, event_type, data=None, time_fired=None):
        """Initialize a new event."""
        self.event_type = event_type
        self.data = data or {}
        self.time_fired = time_fired or time.time()

    def as_dict(self):
        """Create a dict representation of this Event.
        Async friendly.
        """
        return {
            'event_type': self.event_type,
            'data': dict(self.data),
            'time_fired': self.time_fired,
        }

    def __repr__(self):
        """Return the representation."""
        if self.data:
            return "<Event {}: {}>".format(
                self.event_type,
                self.data)

        return "<Event {}>".format(self.event_type)

    def __eq__(self, other):
        """Return the comparison."""
        return (self.__class__ == other.__class__ and
                self.event_type == other.event_type and
                self.data == other.data and
                self.time_fired == other.time_fired)


class EventBus(object):
    """Allow the firing of and listening for events."""

    def __init__(self, mm):
        """Initialize a new event bus."""
        self.__logger = logging.getLogger("%s.%s" % (self.__class__.__module__, self.__class__.__name__))

        self._listeners = {}
        self._mm = mm

    @property
    def listeners(self):
        """Return dictionary with events and the number of listeners."""
        return {key: len(self._listeners[key])
                for key in self._listeners}

    def fire(self, event_type, event_data=None):
        """Fire an event."""
        listeners = self._listeners.get(event_type, [])
        match_all_listeners = self._listeners.get(MATCH_ALL)

	if match_all_listeners:
            listeners = match_all_listeners + listeners

        event = Event(event_type, event_data)

        self.__logger.info("Handling {} with {}".format(event, listeners))

        if not listeners:
            return

        for func in listeners:
            func(event)

    def listen(self, event_type, listener):
        """Listen for all events or events of a specific type.
        To listen to all events specify the constant ``MATCH_ALL``
        as event_type.
        """
        if event_type in self._listeners:
            self._listeners[event_type].append(listener)
        else:
            self._listeners[event_type] = [listener]

        def remove_listener():
            """Remove the listener."""
            try:
                self._listeners[event_type].remove(listener)

                # delete event_type list if empty
                if not self._listeners[event_type]:
                    self._listeners.pop(event_type)
            except (KeyError, ValueError):
                # KeyError is key event_type listener did not exist
                # ValueError if listener did not exist within event_type
                self.__logger.warning("Unable to remove unknown listener %s", listener)

        return remove_listener
