import base64
import json
import logging
from datetime import datetime

from aiohttp import web
from aiohttp.web_exceptions import HTTPBadRequest, HTTPNotImplemented

from motionmonitor.const import KEY_MM
from motionmonitor.models import Frame
from motionmonitor.utils import convert_image

_LOGGER = logging.getLogger(__name__)


def get_extension(mm):
    return [API(mm), APItoHTML(mm)]


class APItoHTML:
    def __init__(self, mm):
        self.mm = mm

    async def start_extension(self):
        self.mm.api.router.add_static('/static', 'html', show_index=True)


class API:
    def __init__(self, mm):
        self.__logger = logging.getLogger(__name__)

        self.mm = mm
        self.__port = mm.config["API"]["PORT"]

        self.server = None

    async def start_extension(self):
        app = self.app = web.Application()

        # Put the mm object in the app - makes available to views when handling requests.
        app[KEY_MM] = self.mm

        # Add the views
        self.register_view(APIRootView)
        self.register_view(APICamerasView)
        self.register_view(APICameraEntityView)
        self.register_view(APICameraSnapshotsView)
        self.register_view(APICameraSnapshotFrameView)
        self.register_view(APICameraSnapshotTimelapseView)
        self.register_view(APICameraEventsView)
        self.register_view(APICameraEventsTimelapseView)
        self.register_view(APICameraEventEntityView)
        self.register_view(APICameraEventFrameView)
        self.register_view(APICameraEventTimelapseView)
        self.register_view(APIJobsView)

        # Prevent the router from getting frozen so that extensions are able to add new routes, even after
        # the server has started.  Inspired by Home-Assistant code (https://github.com/home-assistant).
        # pylint: disable=protected-access
        app._router.freeze = lambda: None

        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, 'localhost', self.__port)
        await site.start()

        self.mm.api = app

        self.__logger.info("Listening on port {}...".format(self.__port))

    def register_view(self, view):
        """Register a view with the WSGI server.
        The view argument must be a class that inherits from HomeAssistantView.
        It is optional to instantiate it before registering; this method will
        handle it either way.
        """
        if isinstance(view, type):
            # Instantiate the view, if needed
            view = view()

        class_name = view.__class__.__name__
        if not hasattr(view, "url"):
            raise AttributeError(f'{class_name} missing required attribute "url"')

        if not hasattr(view, "name"):
            raise AttributeError(f'{class_name} missing required attribute "name"')

        if not hasattr(view, "description"):
            raise AttributeError(f'{class_name} missing required attribute "description"')

        view.register(self.app, self.app.router)
        _LOGGER.debug("View '{}' has been registered.".format(view.name))


class BaseAPIView:
    """Base view for all views."""

    # url = None
    # name = None
    # description = None
    extra_urls = []

    def register(self, app, router):
        """Register the view with a router."""
        _LOGGER.debug("Attempting to register our view")

        for method in ("get", "post", "delete", "put", "patch", "head", "options"):
            handler = getattr(self, method, None)

            if not handler:
                _LOGGER.debug("Couldn't locate a '{}' handler for the view.".format(method))
                continue

            router.add_route(method, self.url, handler, name=self.name)


class APIRootView(BaseAPIView):
    url = "/"
    name = "api:root"
    description = "Describes the available API endpoints"

    async def get(self, request):
        response = {"application": "Motion Monitor", "version": 0.1, "routes": []}
        for route in request.app.router.routes():
            route_desc = {"name": route.name, "method": route.method, "url": route.resource.canonical,
                          "description": "<str>"}
            response["routes"].append(route_desc)
        return web.Response(text=json.dumps(response), content_type='application/json')


class APICamerasView(BaseAPIView):
    url = "/cameras"
    name = "api:cameras"
    description = "Lists the known cameras"

    async def get(self, request):
        mm = request.app[KEY_MM]
        response = {"cameras": []}
        for camera_id in mm.cameras:
            camera_desc = {"cameraId": camera_id,
                           "url": str(request.app.router[APICameraEntityView.name].url_for(camera_id=camera_id))}
            response["cameras"].append(camera_desc)
        return web.Response(text=json.dumps(response), content_type='application/json')


class APICameraEntityView(BaseAPIView):
    url = "/cameras/{camera_id}"
    name = "api:camera-entity"
    description = "Provides a detailed view of a specific camera_id"

    async def get(self, request):
        camera_id = request.match_info['camera_id']

        mm = request.app[KEY_MM]
        try:
            response = mm.cameras[camera_id].to_json()
            return web.Response(text=json.dumps(response), content_type='application/json')
        except KeyError as e:
            _LOGGER.error("Invalid cameraId: {}".format(camera_id))
            raise HTTPBadRequest()


class APICameraSnapshotsView(BaseAPIView):
    url = "/cameras/{camera_id}/snapshots"
    name = "api:camera-snapshots"
    description = "Lists the snapshots related to this camera_id"

    async def get(self, request):
        camera_id = request.match_info['camera_id']

        mm = request.app[KEY_MM]
        try:
            camera = mm.cameras[camera_id]
        except KeyError as e:
            _LOGGER.error("Invalid cameraId: {}".format(camera_id))
            raise HTTPBadRequest()

        response = {"snapshots": [],
                    "url": str(request.app.router[APICameraSnapshotTimelapseView.name].url_for(camera_id=camera_id))}
        for snapshot in camera.recent_snapshots.values():
            timestamp = snapshot.timestamp.strftime("%Y%m%d%H%M%S")
            frame_num = snapshot.frame_num
            snapshot_desc = {"timestamp": timestamp, "frame": frame_num,
                             "url": str(
                                 request.app.router[APICameraSnapshotFrameView.name].url_for(camera_id=camera_id,
                                                                                             timestamp=timestamp,
                                                                                             frame=frame_num))}
            response["snapshots"].append(snapshot_desc)
        return web.Response(text=json.dumps(response), content_type='application/json')


class APICameraSnapshotFrameView(BaseAPIView):
    url = "/cameras/{camera_id}/snapshots/{timestamp}/{frame}"
    name = "api:camera-snapshot-frame"
    description = "Returns the snapshot frame for the specified camera_id, timestamp and frame"

    async def get(self, request):
        camera_id = request.match_info['camera_id']
        timestamp = datetime.strptime(request.match_info['timestamp'], "%Y%m%d%H%M%S")
        frame = request.match_info['frame']

        scale = None
        if "scale" in request.query:
            scale = request.query["scale"]
            _LOGGER.debug("Need to scale: {}".format(scale))
            try:
                scale = float(scale)
            except ValueError:
                _LOGGER.error("Scale is not a float: {}".format(scale))
                raise HTTPBadRequest()

        img_format = "JSON"
        if "format" in request.query:
            img_format = request.query["format"]
            _LOGGER.debug("Need to format: {}".format(img_format))
            if img_format not in ["JPEG", "PNG", "GIF", "BMP"]:
                _LOGGER.error("Format is not a recognised option: {}".format(img_format))
                raise HTTPBadRequest()

        mm = request.app[KEY_MM]
        try:
            camera = mm.cameras[camera_id]
            snapshot = camera.recent_snapshots[Frame.create_id(timestamp, frame)]
        except KeyError as e:
            _LOGGER.error("Invalid cameraId: {}".format(camera_id))
            raise HTTPBadRequest()

        if img_format == "JSON":
            img_bytes = convert_image(snapshot, "JPEG", scale)
            response = snapshot.to_json()
            response["jpeg_bytes"] = base64.b64encode(img_bytes).decode('ascii')
            return web.Response(text=json.dumps(response), content_type='application/json')
        else:
            img_bytes = convert_image(snapshot, img_format, scale)
            return web.Response(body=img_bytes, content_type="image/{}".format(img_format))

    async def delete(self, request):
        camera_id = request.match_info['camera_id']
        timestamp = request.match_info['timestamp']
        frame = request.match_info['frame']
        response = {"Message": "Not yet implemented"}
        return web.Response(text=json.dumps(response), content_type='application/json')


class APICameraSnapshotTimelapseView(BaseAPIView):
    url = "/cameras/{camera_id}/snapshots/timelapse"
    name = "api:camera-snapshot-timelapse"
    description = "Returns the snapshots that make up a timelapse for the specified camera_id"

    async def get(self, request):
        raise HTTPNotImplemented()


class APICameraEventsView(BaseAPIView):
    url = "/cameras/{camera_id}/events"
    name = "api:camera-events"
    description = "Returns the events that we have recorded for a specified camera_id"

    async def get(self, request):
        raise HTTPNotImplemented()


class APICameraEventsTimelapseView(BaseAPIView):
    url = "/cameras/{camera_id}/events/timelapse"
    name = "api:camera-events-timelapse"
    description = "Returns the frames that make up a timelapse of the events for the specified camera_id"

    async def get(self, request):
        raise HTTPNotImplemented()


class APICameraEventEntityView(BaseAPIView):
    url = "/cameras/{camera_id}/events/{event_id}"
    name = "api:camera-event-entity"
    description = "Returns the event specified by camera_id and event_id"

    async def get(self, request):
        raise HTTPNotImplemented()

    async def delete(self, request):
        raise HTTPNotImplemented()


class APICameraEventFrameView(BaseAPIView):
    url = "/cameras/{camera_id}/events/{event_id}/{timestamp}/{frame}"
    name = "api:camera-event-frame"
    description = "Returns a frame from an event as specified by camera_id, event_id, timestamp and frame"

    async def get(self, request):
        raise HTTPNotImplemented()

    async def delete(self, request):
        raise HTTPNotImplemented()


class APICameraEventTimelapseView(BaseAPIView):
    url = "/cameras/{camera_id}/events/{event_id}/timelapse"
    name = "api:camera-event-timelapse"
    description = "Returns the frames that make up a timelapse of the event specified by camera_id and event_id"

    async def get(self, request):
        raise HTTPNotImplemented()


class APIJobsView(BaseAPIView):
    url = "/jobs"
    name = "api:jobs"
    description = "Returns the known jobs."

    async def get(self, request):
        mm = request.app[KEY_MM]
        response = {"jobs": []}
        for job in mm.jobs:
            job_desc = {"jobId": job.id,
                        "name": job.name}
            response["jobs"].append(job_desc)
        return web.Response(text=json.dumps(response), content_type='application/json')
