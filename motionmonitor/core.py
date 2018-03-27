import logging
import time
from motionmonitor.const import (
    MATCH_ALL
)
import motionmonitor.config
import motionmonitor.socketlistener
import motionmonitor.sqlexchanger
import motionmonitor.filemanager
import motionmonitor.zabbixwriter
import motionmonitor.cameramonitor
import motionmonitor.jsoninterface


class MotionMonitor(object):

    def __init__(self):
        self.__logger = logging.getLogger("%s.%s" % (self.__class__.__module__, self.__class__.__name__))

        self.config = motionmonitor.config
        self.bus = EventBus(self)

        self._jobs = {}

        self.__socket_listener = motionmonitor.socketlistener.SocketListener(self)
        self.__camera_monitor = motionmonitor.cameramonitor.CameraMonitor(self)
        self.__zabbixwriter = motionmonitor.zabbixwriter.ZabbixWriter(self)
        motionmonitor.sqlexchanger.DB(self)
        self.__live_sqlwriter = motionmonitor.sqlexchanger.SQLWriter()

        # SocketListener MOTION_EVENTs should be handled by the CameraMonitor.
        self.__socket_listener.connect(self.__socket_listener.MOTION_EVENT,
                                       self.__camera_monitor.handle_motion_event)

        # SocketListener MOTION_EVENTs should be handled by the SQLWriter.
        self.__socket_listener.connect(self.__socket_listener.MOTION_EVENT,
                                       self.__live_sqlwriter.handle_motion_event)

        # CameraMonitor ACTIVITY_EVENTs are handled by the ZabbixWriter.
        self.__camera_monitor.connect(self.__camera_monitor.ACTIVITY_EVENT,
                                      self.__zabbixwriter.handle_camera_activity)

        # This is the sweeper and auditor.
        self.__sweeper = motionmonitor.filemanager.Sweeper(self)
        self.__auditor = motionmonitor.filemanager.Auditor(self)
        # SocketListener MANAGEMENT_EVENTs should be handled by the Sweeper.
        self.__socket_listener.connect(self.__socket_listener.MANAGEMENT_EVENT,
                                       self.__sweeper.sweep)

        # SocketListener MANAGEMENT_EVENTs should be handled by the Auditor.
        self.__socket_listener.connect(self.__socket_listener.MANAGEMENT_EVENT,
                                       self.__auditor.insert_orphaned_snapshots)

        self.__json_interface = motionmonitor.jsoninterface.JSONInterface(self, self.__camera_monitor)


class Job:
    def __init__(self, name, start_time):
        self.__logger = logging.getLogger("%s.%s" % (self.__class__.__module__, self.__class__.__name__))

        self.name = name
        self.__start_time = start_time
        self.__progress = 0
        self.__update_time = start_time
        self.__status_text = None

    def update_status(self, progress, description):
        self.progress = progress
        self.__update_time = time.time()

    @property
    def progress(self):
        return self.__progress

    @progress.setter
    def progress(self, value):
        if value > 100:
            self.__logger.debug("Provided value '{}' being forced to 100".format(value))
            self.__progress = 100
        elif value < 0:
            self.__logger.debug("Provided value '{}' being forced to 0".format(value))
            self.__progress = 0
        else:
            self.__progress = float(value)

    @property
    def eta(self):
        return time.time()


class Event(object):
    """Representation of an event within the bus."""

    __slots__ = ['event_type', 'data', 'origin', 'time_fired']

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
        listeners = match_all_listeners + listeners

        event = Event(event_type, event_data)

        self.__logger.info("Handling %s", event)

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
