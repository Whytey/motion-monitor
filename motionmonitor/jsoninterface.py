'''
Created on 11/08/2013

@author: djwhyte
'''
import asyncio
import base64
import datetime
import json
import logging
from io import StringIO

from PIL import Image as PILImage

import motionmonitor.sqlexchanger
from motionmonitor.cameramonitor import Event, Frame


class Image():
    """This is an Image object, as represented in JSON"""

    _CONFIG_target_dir = '/data/motion/'
    _CONFIG_snapshot_filename = 'snapshots/camera%t/%Y/%m/%d/%H/%M/%S-snapshot.jpg'
    _CONFIG_motion_filename = 'motion/camera%t/%Y%m%d/%v/%Y%m%d-%H%M%S-%q.jpg'

    TYPE_MOTION = 1
    TYPE_SNAPSHOT = 2

    def __init__(self, cameraid=None, timestamp=None, thumbnail=False, include_image=False):
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
        assert self._path.startswith(self._CONFIG_target_dir), "Not a motion file: %s" % self._path

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
    def __init__(self, cameraid=None, timestamp=None, event=None, thumbnail=False, include_image=False):
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
    def __init__(self, cameraid=None, timestamp=None, thumbnail=False, include_image=False):
        self.__logger = logging.getLogger("%s.SnapshotImage" % __name__)
        Image.__init__(self, cameraid, timestamp, thumbnail, include_image)

        self._path = Image._CONFIG_target_dir + Image._CONFIG_snapshot_filename
        self._path = Image._decode_image_path(self._path, self._cameraid, self._timestamp)

    def _imageType(self):
        return "snapshot"


class JSONInterface():
    _CONFIG_target_dir = '/data/motion/'
    _CONFIG_snapshot_filename = 'snapshots/camera%t/%Y/%m/%d/%H/%M/%S-snapshot.jpg'

    def __init__(self, mm, camera_monitor):
        self.__logger = logging.getLogger(__name__)

        self.mm = mm
        self.camera_monitor = camera_monitor

        # Initialise server and start listening.
        self.transport = None

    def listen(self):
        config = self.mm.config
        self.__logger.debug("binding to %s:%d" % (config.JSON_SOCKET_ADDR, config.JSON_SOCKET_PORT))

        loop = self.mm.loop
        protocol = SocketHandler(self.mm, self.camera_monitor)

        # One protocol instance will be created to serve all client requests
        socket_listener = loop.create_datagram_endpoint(
            lambda: protocol, local_addr=(config.JSON_SOCKET_ADDR, config.JSON_SOCKET_PORT))
        self.transport, p1 = loop.run_until_complete(socket_listener)
        self.__logger.info("Listening...")

    def close(self):
        if self.transport:
            self.transport.close()


class SocketHandler(asyncio.DatagramProtocol):

    def __init__(self, mm, camera_monitor):
        self.mm = mm
        self.__camera_monitor = camera_monitor
        self.__logger = logging.getLogger("%s.%s" % (self.__class__.__module__, self.__class__.__name__))

    def connection_made(self, transport):
        self.transport = transport

    def __validate_msg(self, msg):
        assert type(msg) == dict, "Message should be a dictionary: %s" % msg
        assert "method" in msg, "Message does not specify what method it is: %s" % msg
        self.__logger.debug("Got a message method of '%s'" % msg["method"])

        # Check we have a valid method
        assert msg["method"] in ["camera.get",
                                 "image.get",
                                 "event.list",
                                 "event.get",
                                 "snapshot.get"]

        # Check that params have been provided, not necessarily valid params.
        assert "params" in msg, "Message does not specify any parameters: %s" % msg

    def datagram_received(self, data, addr):
        response = {}

        try:
            self.__logger.debug("Need to handle JSON request.")
            # If it is the correct socket, read data from it.
            line = data.decode()

            self.__logger.debug('Received %r from %s' % (line, addr))

            msg = json.loads(line)

            self.__validate_msg(msg)

            if msg["method"] == "camera.get":
                results_json = []
                for result in self.__camera_monitor.get_cameras().values():
                    results_json.append(result.toJSON())
                response["result"] = results_json
                response["count"] = len(results_json)

            if msg["method"] == "image.get":
                results = Image.get(msg["params"])
                results_json = []
                for result in results:
                    results_json.append(result.toJSON())
                response["result"] = results_json
                response["count"] = len(results_json)

            if msg["method"] == "event.get":
                results = Event.get(motionmonitor.sqlexchanger.SQLReader(self.mm), msg["params"])
                results_json = []
                for result in results:
                    results_json.append(result.toJSON(True))
                response["result"] = results_json
                response["count"] = len(results_json)

            if msg["method"] == "event.list":
                results = Event.list(motionmonitor.sqlexchanger.SQLReader(self.mm), msg["params"])
                results_json = []
                for result in results:
                    results_json.append(result.toJSON())
                response["result"] = results_json
                response["count"] = len(results_json)

            if msg["method"] == "snapshot.get":
                results = Frame.get(motionmonitor.sqlexchanger.SQLReader(self.mm), msg["params"])
                results_json = []
                for result in results:
                    results_json.append(result.toJSON())
                response["result"] = results_json
                response["count"] = len(results_json)

        except Exception as e:
            self.__logger.exception(e)
            error = {}
            error["code"] = 1
            error["message"] = "JSON Exception"
            error["data"] = str(e)
            response["error"] = error
        finally:

            self.__logger.debug('Send %r to %s' % (json.dumps(response), addr))
            self.transport.sendto(data, addr)

        return True
