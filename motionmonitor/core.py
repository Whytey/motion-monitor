import logging
import os
import time
from collections import OrderedDict
from importlib import util

import motionmonitor.cameramonitor
import motionmonitor.config
# import extensions.mysql_db_server.__init__
from motionmonitor.const import (
    MATCH_ALL, EVENT_JOB, MAX_JOBQ_SIZE
)


class MotionMonitor(object):

    def __init__(self, config, loop):
        self.__logger = logging.getLogger("%s.%s" % (self.__class__.__module__, self.__class__.__name__))

        self.config = config
        self.loop = loop
        self.bus = EventBus(self)
        self.jobs = OrderedDict()

        self.bus.listen(EVENT_JOB, self.job_handler)
        self.cameras = {}

        self.__camera_monitor = motionmonitor.cameramonitor.CameraMonitor(self)

        self.extensions = self.__load_extensions()

        self.__logger.info("Initialised...")

    async def run(self):
        for extension in self.extensions:
            self.__logger.debug("About to start: {}".format(extension))
            await extension.start_extension()
            self.__logger.debug("Started: {}".format(extension))

    def job_handler(self, event):
        self.__logger.debug("Handling a job event: {}".format(event))
        job = event.data
        self.jobs[job.id] = job
        while (len(self.jobs) > MAX_JOBQ_SIZE):
            self.__logger.debug("Too many jobs in the queue, popping the oldest")
            self.jobs.popitem(False)

    def __load_extensions(self):
        main_module = "__init__"
        extension_folder = self.config["GENERAL"]["EXTENSIONS_DIR"]

        extensions=[]
        possible_extensions = os.listdir(extension_folder)
        self.__logger.debug("Have the following extension folders: {}".format(possible_extensions))

        for extension in [item.lower() for item in possible_extensions]:
            # Try and load the extension
            location = os.path.join(extension_folder, extension)
            self.__logger.debug("Extension location should be: {}".format(location))

            if not os.path.isdir(
                location
            ) or main_module + ".py" not in os.listdir(location):
                self.__logger.warning("Extension '{}' isn't a directory or the directory doesn't contain an '{}'.py.".format(location, main_module))
                continue

            module_path = os.path.join(location, main_module + ".py")
            if not os.path.exists(module_path):
                self.__logger.warning("No {} module found for extention '{}'".format(main_module, location))
                continue

            spec = util.spec_from_file_location(main_module, module_path)
            module = util.module_from_spec(spec)
            spec.loader.exec_module(module)
            extension_instance = module.get_extension(self)
            extensions.extend(extension_instance if type(extension_instance) == list else [extension_instance])

        return extensions


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

    @progress.setter
    def progress(self, value):
        self.__progress = value

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

        self.__logger.debug("Handling {} with {}".format(event, listeners))

        if not listeners:
            return

        for func in listeners:
            func(event)

    def listen(self, event_type, listener):
        """Listen for all events or events of a specific type.
        To listen to all events specify the constant ``MATCH_ALL``
        as event_type.
        """
        self.__logger.debug("Adding {} as a listener to events of type '{}'".format(listener, event_type))
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
