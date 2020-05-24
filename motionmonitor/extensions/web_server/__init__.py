'''
Created on 11/08/2013

@author: djwhyte
'''
import base64
import datetime
import json
import logging
from io import BytesIO
from motionmonitor.stream.handlers import SnapshotFrameHandler, MotionFrameHandler, MotionVideoHandler, TimelapseVideoHandler, LiveFrameHandler, LiveVideoHandler

from PIL import Image as PILImage
from aiohttp import web

import motionmonitor.sqlexchanger
from models import Frame, Event


def get_extension(mm):
    return JSONInterface(mm)


class Image:
    """This is an Image object, as represented in JSON"""

    # _CONFIG_target_dir = '/data/motion/'
    _CONFIG_snapshot_filename = 'snapshots/camera%t/%Y/%m/%d/%H/%M/%S-snapshot.jpg'
    _CONFIG_motion_filename = 'motion/camera%t/%Y%m%d/%v/%Y%m%d-%H%M%S-%q.jpg'

    TYPE_MOTION = 1
    TYPE_SNAPSHOT = 2

    def __init__(self, mm, cameraid=None, timestamp=None, thumbnail=False, include_image=False):
        self.__logger = logging.getLogger("%s.Image" % __name__)
        self.mm = mm
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
            jsonstr["image"] = self._get_image_data().decode('ascii')
        return jsonstr

    def _get_image_data(self):
        # Need to ensure we only serve up motion files.
        assert self._path.startswith(self.mm.config["GENERAL"]["TARGET_DIR"]), "Not a motion file: %s" % self._path

        # TODO: Need to only serve up jpeg files.

        with open(self._path, "rb") as image_file:
            if self._thumbnail:
                self.__logger.debug("Creating a thumbnail")
                size = [160, 120]
                thumbnail = BytesIO()
                im = PILImage.open(image_file)
                im.thumbnail(size)
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
        path = path.replace("%t", str(cameraid))

        # Overlay the timestamp into the filepath
        path = ts.strftime(path)
        return path

    @staticmethod
    def get(mm, params):
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
            return [MotionImage(mm, cameraid, timestamp, event, thumbnail, include_image)]
        else:
            # Can only be a snapshot!
            return [SnapshotImage(mm, cameraid, timestamp, thumbnail, include_image)]


class MotionImage(Image):
    def __init__(self, mm, cameraid=None, timestamp=None, event=None, thumbnail=False, include_image=False):
        self.__logger = logging.getLogger("%s.MotionImage" % __name__)
        Image.__init__(self, mm, cameraid, timestamp, thumbnail, include_image)
        self._event = event
        self._path = mm.config["GENERAL"]["TARGET_DIR"] + Image._CONFIG_motion_filename
        self._path = self._path.replace("%v", str(self._event))
        self._path = self._path.replace("%q", "00")
        self._path = Image._decode_image_path(self._path, self._cameraid, self._timestamp)
        self.__logger.debug("The path: " + self._path)
        self.__logger.debug("Getting JSON")

    def _imageType(self):
        return "motion"


class SnapshotImage(Image):
    def __init__(self, mm, cameraid=None, timestamp=None, thumbnail=False, include_image=False):
        self.__logger = logging.getLogger("%s.SnapshotImage" % __name__)
        Image.__init__(self, mm, cameraid, timestamp, thumbnail, include_image)

        self._path = mm.config["GENERAL"]["TARGET_DIR"] + Image._CONFIG_snapshot_filename
        self._path = Image._decode_image_path(self._path, self._cameraid, self._timestamp)
        self.__logger.debug("The path: " + self._path)

    def _imageType(self):
        return "snapshot"


class JSONInterface:
    def __init__(self, mm):
        self.__logger = logging.getLogger(__name__)

        self.mm = mm
        self.__port = mm.config["WEB_SERVER"]["PORT"]

        self.server = None

    async def start_extension(self):
        app = web.Application()
        app.router.add_get('/json', self.json_get_data_received)
        app.router.add_post('/json', self.json_post_data_received)
        app.router.add_get('/media', self.media_get_data_received)
        app.router.add_post('/media', self.media_post_data_received)
        app.router.add_static("/", path=str('./html/'))

        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, 'localhost', self.__port)
        await site.start()

        self.__logger.info("Listening on port {}...".format(self.__port))


    def __validate_json_msg(self, msg):
        # assert type(msg) == dict, "Message should be a dictionary: %s" % msg
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

    async def media_get_data_received(self, request):
        self.__logger.debug("Need to handle MEDIA GET request.")
        self.__logger.debug(request.query)
        msg = request.query
        return await self.media_data_received(request, msg)

    async def media_post_data_received(self, request):
        self.__logger.debug("Need to handle MEDIA POST request.")
        self.__logger.debug(request.json())
        msg = await request.json()
        return await self.media_data_received(request, msg)

    async def media_data_received(self, request, msg):
        response = {}
        self.__logger.debug("Handling the MEDIA request.")
        try:
            # assert type(request) == dict, "Request should be a dictionary: %s" % request
            assert "method" in msg, "Request does not specify what method it is: %s" % msg

            request_type = msg["method"]

        except AssertionError as e:
            response["error"] = "Invalid request: %s" % e
            return

        try:
            if request_type.lower() == "snapshotframe":
                handler = SnapshotFrameHandler(msg)
            elif request_type.lower() == "motionframe":
                handler = MotionFrameHandler(msg)
            # elif request_type.lower() == "motionvideo":
            #     handler = MotionVideoHandler(msg)
            # elif request_type.lower() == "timelapsevideo":
            #     handler = TimelapseVideoHandler(msg)
            elif request_type.lower() == "liveframe":
                handler = LiveFrameHandler(msg)
            elif request_type.lower() == "livevideo":
                handler = LiveVideoHandler(msg)
            else:
                raise KeyError("Unknown method requested: %s" % request_type)

            image_bytes = await handler.createBytes()

            self.__logger.debug("Got bytes: " + str(base64.b64encode(image_bytes)))
            response = web.Response(body=image_bytes)
            self.__logger.debug("Size: " + str(response.content_length))
            response.content_type = 'image/jpeg'
            return response

        except Exception as e:
            # Socket errors
            import traceback
            traceback.print_exc()
            response["error"] = "Error processing request: %s" % e
        finally:
            return response

    async def json_get_data_received(self, request):
        self.__logger.debug("Need to handle JSON GET request.")
        self.__logger.debug(request.query)
        msg = request.query
        return await self.json_data_received(msg)

    async def json_post_data_received(self, request):
        self.__logger.debug("Need to handle JSON POST request.")
        self.__logger.debug(await request.json())
        msg = await request.json()
        return await self.json_data_received(msg)

    async def json_data_received(self, msg):
        response = {}

        try:
            self.__logger.debug("Handling the JSON request.")
            self.__validate_json_msg(msg)

            if msg["method"] == "camera.get":
                results_json = []
                for result in self.mm.cameras.values():
                    results_json.append(result.toJSON())
                response["result"] = results_json
                response["count"] = len(results_json)

            if msg["method"] == "image.get":
                results = Image.get(self.mm, msg["params"])
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

        self.__logger.debug(response)
        return web.Response(text=json.dumps(response), content_type='application/json')
