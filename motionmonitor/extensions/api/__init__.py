import base64
import json
import logging
from datetime import datetime

from aiohttp import web
from aiohttp.web_exceptions import HTTPBadRequest, HTTPNotImplemented

from motionmonitor.const import KEY_MM
from motionmonitor.extensions.api.siren import Entity, EmbeddedRepresentationSubEntity
from motionmonitor.models import Frame
from motionmonitor.utils import convert_image

_LOGGER = logging.getLogger(__name__)


def get_extension(mm):
    return [API(mm), APItoHTML(mm)]


class APItoHTML:
    def __init__(self, mm):
        self.mm = mm

    async def start_extension(self):
        self.mm.api.app.router.add_static('/static', 'motionmonitor/extensions/api/html', show_index=True)


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

        self.mm.api = self

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

    url = None
    name = None
    description = None
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

    @classmethod
    def to_entity_repr(cls, request, classes=[], path_params={}, query_params={}):
        return {
            "class": classes,
            "properties": {
            },
            "entities": [],
            "links": [
                {
                    "rel": ["self"],
                    "href": str(request.app.router[cls.name].url_for(**path_params).with_query(query_params))
                }
            ],
        }

    @classmethod
    def to_link_repr(cls, request, classes=[], rel=[], path_params={}, query_params={}):
        return {
            "class": classes,
            "rel": rel,
            "href": str(request.app.router[cls.name].url_for(**path_params).with_query(query_params))
        }


class APIRootView(BaseAPIView):
    url = "/"
    name = "api:root"
    description = "Describes the available API endpoints"

    async def get(self, request):
        response = Entity(["route"])
        response.set_property("application", "Motion Monitor")
        response.set_property("version", 0.1)
        response.append_link("self", self.url)
        for route in request.app.router.routes():
            entity = EmbeddedRepresentationSubEntity(["link"])
            entity.set_property("name", route.name)
            entity.set_property("method", route.method)
            entity.set_property("url", route.resource.canonical)
            entity.set_property("description", "<str>")
            if route.method.upper() == "GET" and "{" not in route.resource.canonical:
                entity.append_link("self", route.resource.canonical)
            response.add_sub_entity(entity)
        return web.Response(text=json.dumps(response.to_json()), content_type='application/json')


class APICamerasView(BaseAPIView):
    url = "/cameras"
    name = "api:cameras"
    description = "Lists the known cameras"

    async def get(self, request):
        mm = request.app[KEY_MM]
        response = self.to_entity_repr(request, ["cameras"])
        for camera_id in mm.cameras:
            camera = mm.cameras[camera_id]
            camera_resp = APICameraEntityView.to_link_repr(request, [], ["item"], {"camera_id": camera_id})
            camera_resp["rel"].append("item")
            response["entities"].append(camera_resp)
        return web.Response(text=json.dumps(response), content_type='application/json')


class APICameraEntityView(BaseAPIView):
    url = "/cameras/{camera_id}"
    name = "api:camera-entity"
    description = "Provides a detailed view of a specific camera_id"

    def __init__(self):
        super(BaseAPIView).__init__()

    async def get(self, request):
        camera_id = request.match_info['camera_id']

        mm = request.app[KEY_MM]
        try:
            camera = mm.cameras[camera_id]
        except KeyError as e:
            _LOGGER.error("Invalid cameraId: {}".format(camera_id))
            raise HTTPBadRequest()

        response = self.to_entity_repr(request, ["cameras"], {"camera_id": camera_id})
        response["properties"] = {
            "cameraId": camera.id,
            "state": camera.state
        }
        # The last-snapshot sub-entity
        last_snapshot = camera.last_snapshot
        if last_snapshot:
            response["entities"].append(
                APICameraSnapshotFrameView.to_link_repr(request, ["frame"],
                                                        rel=["http://motion-monitor/rel/last-snapshot"],
                                                        path_params={"camera_id": camera_id,
                                                                     "timestamp": last_snapshot.timestamp.strftime(
                                                                         "%Y%m%d%H%M%S"),
                                                                     "frame": last_snapshot.frame_num}))

        # The recent-snapshots sub-entity
        response["entities"].append(
            APICameraSnapshotsView.to_link_repr(request, ["frames"],
                                                rel=["http://motion-monitor/rel/recent-snapshots"],
                                                path_params={"camera_id": camera_id}))

        # The recent motion sub-entity
        response["entities"].append(
            APICameraEventsView.to_link_repr(request, ["events"],
                                             rel=["http://motion-monitor/rel/recent-motion"],
                                             path_params={"camera_id": camera_id}))
        return web.Response(text=json.dumps(response), content_type='application/json')


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

        response = self.to_entity_repr(request, ["snapshots"], path_params={"camera_id": camera_id})
        response["links"].append(APICameraSnapshotTimelapseView.to_link_repr(request,
                                                                             rel=["timelapse"],
                                                                             path_params={"camera_id": camera_id}))
        for snapshot in camera.recent_snapshots.values():
            timestamp = snapshot.timestamp.strftime("%Y%m%d%H%M%S")
            frame_num = snapshot.frame_num

            response["entities"].append(APICameraSnapshotFrameView.to_link_repr(request,
                                                                                ["snapshot"],
                                                                                ["item"],
                                                                                path_params={"camera_id": camera_id,
                                                                                             "timestamp": timestamp,
                                                                                             "frame": frame_num}))

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
            if img_format.upper() not in ["JPEG", "PNG", "GIF", "BMP"]:
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

            snapshot_params = {
                "camera_id": camera_id,
                "timestamp": timestamp.strftime("%Y%m%d%H%M%S"),
                "frame": frame
            }

            response = self.to_entity_repr(request, ["frame"], path_params=snapshot_params)
            response["properties"] = {
                "cameraId": camera_id,
                "timestamp": timestamp.strftime("%Y%m%d%H%M%S"),
                "frame": frame,
                "filename": snapshot.filename,
                "jpegBytes": base64.b64encode(img_bytes).decode('ascii'),
            }

            response["links"].append(self.to_link_repr(request, rel=["jpeg"], path_params=snapshot_params,
                                                       query_params={"format": "jpeg"}))
            response["links"].append(self.to_link_repr(request, rel=["jpeg-thumbnail"], path_params=snapshot_params,
                                                       query_params={"format": "jpeg", "scale": "0.2"}))

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
        camera_id = request.match_info['camera_id']

        mm = request.app[KEY_MM]
        try:
            camera = mm.cameras[camera_id]
        except KeyError as e:
            _LOGGER.error("Invalid cameraId: {}".format(camera_id))
            raise HTTPBadRequest()

        response = self.to_entity_repr(request, ["events"], path_params={"camera_id": camera_id})
        for event in camera.recent_motion.values():
            response["entities"].append(APICameraEventEntityView.to_link_repr(request, ["event"], ["item"],
                                                                              path_params={"camera_id": event.camera_id,
                                                                                           "event_id": event.id}))

        return web.Response(text=json.dumps(response), content_type='application/json')


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
        camera_id = request.match_info['camera_id']
        event_id = request.match_info['event_id']

        mm = request.app[KEY_MM]
        try:
            camera = mm.cameras[camera_id]
            event = camera.recent_motion[event_id]
        except KeyError as e:
            _LOGGER.error("Invalid cameraId: {}".format(camera_id))
            raise HTTPBadRequest()

        response = self.to_entity_repr(request, ["event"], path_params={"camera_id": camera_id, "event_id": event_id})
        response["properties"] = {
            "eventId": event.id,
            "cameraId": event.camera_id,
            "startTime": event.start_time.strftime("%Y%m%d%H%M%S"),
        }

        if event.top_score_frame:
            tsf = event.top_score_frame
            response["entities"].append(
                APICameraEventFrameView.to_link_repr(request, ["frame"],
                                                     ["http://motion-monitor/rel/top-score-frame"],
                                                     path_params={"camera_id": tsf.camera_id,
                                                                  "event_id": tsf.event_id,
                                                                  "timestamp": tsf.timestamp.strftime("%Y%m%d%H%M%S"),
                                                                  "frame": tsf.frame_num}))
        return web.Response(text=json.dumps(response), content_type='application/json')

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
        response = self.to_entity_repr(request, ["jobs"])
        for job in mm.jobs:
            response["entities"].append(APIJobEntityView.to_link_repr(request, ["job"],
                                                                      rel=["item"],
                                                                      path_params={"job_id": job.id}))
            job_desc = {"jobId": job.id,
                        "name": job.name}
            response["jobs"].append(job_desc)
        return web.Response(text=json.dumps(response), content_type='application/json')


class APIJobEntityView(BaseAPIView):
    url = "/jobs/{job_id}"
    name = "api:job-entity"
    description = "Returns specified job."

    async def get(self, request):
        response = self.to_entity_repr(request, ["job"])
        return web.Response(text=json.dumps(response), content_type='application/json')
