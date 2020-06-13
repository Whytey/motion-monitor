import base64
import json
import logging
from datetime import datetime

from aiohttp import web
from aiohttp.web_exceptions import HTTPBadRequest, HTTPNotImplemented

from motionmonitor.const import KEY_MM
from motionmonitor.extensions.api.siren import Entity, EmbeddedRepresentationSubEntity
from motionmonitor.models import Frame, EventFrame
from motionmonitor.utils import convert_frames, animate_frames

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
        self.register_view(APICameraSnapshotsFramesView)
        self.register_view(APICameraSnapshotFrameView)
        self.register_view(APICameraSnapshotTimelapseView)
        self.register_view(APICameraEventsView)
        self.register_view(APICameraEventsTimelapseView)
        self.register_view(APICameraEventEntityView)
        self.register_view(APICameraEventFramesView)
        self.register_view(APICameraEventFrameView)
        self.register_view(APICameraEventTimelapseView)
        self.register_view(APIJobsView)
        self.register_view(APIJobEntityView)

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

        view.register(self.app.router)
        _LOGGER.debug("View '{}' has been registered.".format(view.name))


class BaseAPIView:
    """Base view for all views."""

    url = None
    name = None
    description = None
    extra_urls = []

    def register(self, router):
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
        _LOGGER.debug(cls.name)
        return {
            "class": classes,
            "rel": rel,
            "href": str(request.app.router[cls.name].url_for(**path_params).with_query(query_params))
        }


class APIImageView(BaseAPIView):
    def _get_scale_param(self, request):
        scale = None
        if "scale" in request.query:
            scale = request.query["scale"]
            _LOGGER.debug("Need to scale: {}".format(scale))
            try:
                scale = float(scale)
            except ValueError:
                _LOGGER.error("Scale is not a float: {}".format(scale))
                raise HTTPBadRequest()
        return scale

    def _get_format_param(self, request):
        img_format = "JSON"
        if "format" in request.query:
            img_format = request.query["format"]
            _LOGGER.debug("Need to format: {}".format(img_format))
            if img_format.upper() not in ["JPEG", "PNG", "GIF", "BMP"]:
                _LOGGER.error("Format is not a recognised option: {}".format(img_format))
                raise HTTPBadRequest()
        return img_format

    def _create_response(self, request, img_format: str, scale: float, frame: Frame, frame_params: dict,
                         self_view: BaseAPIView) -> web.Response:
        _LOGGER.debug(frame_params)
        if img_format == "JSON":
            img_bytes = convert_frames(frame, "JPEG", scale)

            response = self_view.to_entity_repr(request, ["frame"], path_params=frame_params)
            response["properties"] = frame_params.copy()
            response["properties"]["jpegBytes"] = base64.b64encode(img_bytes).decode('ascii'),

            response["links"].append(self_view.to_link_repr(request, rel=["jpeg"], path_params=frame_params,
                                                            query_params={"format": "jpeg"}))
            response["links"].append(self_view.to_link_repr(request, rel=["jpeg-thumbnail"], path_params=frame_params,
                                                            query_params={"format": "jpeg", "scale": "0.2"}))

            return web.Response(text=json.dumps(response), content_type='application/json')
        else:
            img_bytes = convert_frames(frame, img_format, scale)
            return web.Response(body=img_bytes, content_type="image/{}".format(img_format))


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
            response["entities"].append(APICameraEntityView.to_link_repr(request,
                                                                         ["camera"],
                                                                         ["item"],
                                                                         {"camera_id": camera_id}))
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
        except KeyError:
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
            APICameraSnapshotsFramesView.to_link_repr(request, ["frames"],
                                                      rel=["http://motion-monitor/rel/recent-snapshots"],
                                                      path_params={"camera_id": camera_id}))

        # The recent motion sub-entity
        response["entities"].append(
            APICameraEventsView.to_link_repr(request, ["events"],
                                             rel=["http://motion-monitor/rel/recent-motion"],
                                             path_params={"camera_id": camera_id}))
        return web.Response(text=json.dumps(response), content_type='application/json')


class APICameraSnapshotsFramesView(BaseAPIView):
    url = "/cameras/{camera_id}/snapshots"
    name = "api:camera-snapshot-frames"
    description = "Lists the snapshot frames related to this camera_id"

    async def get(self, request):
        camera_id = request.match_info['camera_id']

        mm = request.app[KEY_MM]
        try:
            camera = mm.cameras[camera_id]
        except KeyError:
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


class APICameraSnapshotFrameView(APIImageView):
    url = "/cameras/{camera_id}/snapshots/{timestamp}/{frame}"
    name = "api:camera-snapshot-frame"
    description = "Returns the snapshot frame for the specified camera_id, timestamp and frame"

    async def get(self, request):
        camera_id = request.match_info['camera_id']
        timestamp = datetime.strptime(request.match_info['timestamp'], "%Y%m%d%H%M%S")
        frame_num = request.match_info['frame']

        scale = self._get_scale_param(request)
        img_format = self._get_format_param(request)

        mm = request.app[KEY_MM]
        try:
            camera = mm.cameras[camera_id]
            frame = camera.recent_snapshots[Frame.create_id(timestamp, frame_num)]
        except KeyError:
            _LOGGER.error("Invalid cameraId: {}".format(camera_id))
            raise HTTPBadRequest()

        frame_params = {
            "camera_id": camera_id,
            "timestamp": timestamp.strftime("%Y%m%d%H%M%S"),
            "frame": frame_num
        }

        return self._create_response(request, img_format, scale, frame, frame_params, self)

    async def delete(self, request):
        camera_id = request.match_info['camera_id']
        timestamp = request.match_info['timestamp']
        frame = request.match_info['frame']
        response = {"Message": "Not yet implemented"}
        return web.Response(text=json.dumps(response), content_type='application/json')


class APICameraSnapshotTimelapseView(APIImageView):
    url = "/cameras/{camera_id}/snapshots/timelapse"
    name = "api:camera-snapshot-timelapse"
    description = "Returns the snapshots that make up a timelapse for the specified camera_id"

    async def get(self, request):
        camera_id = request.match_info['camera_id']
        scale = self._get_scale_param(request)

        mm = request.app[KEY_MM]
        try:
            camera = mm.cameras[camera_id]
        except KeyError:
            _LOGGER.error("Invalid cameraId: {}".format(camera_id))
            raise HTTPBadRequest()

        animation_bytes = animate_frames(camera.recent_snapshots.values(), scale)
        return web.Response(body=animation_bytes, content_type="image/gif")


class APICameraEventsView(BaseAPIView):
    url = "/cameras/{camera_id}/events"
    name = "api:camera-events"
    description = "Returns the events that we have recorded for a specified camera_id"

    async def get(self, request):
        camera_id = request.match_info['camera_id']

        mm = request.app[KEY_MM]
        try:
            camera = mm.cameras[camera_id]
        except KeyError:
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
        except KeyError:
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
        response["entities"].append(APICameraEventFramesView.to_link_repr(request, ["frames"],
                                                                          ["http://motion-monitor/rel/frames"],
                                                                          path_params={"camera_id": camera_id,
                                                                                       "event_id": event_id}))
        return web.Response(text=json.dumps(response), content_type='application/json')

    async def delete(self, request):
        raise HTTPNotImplemented()


class APICameraEventFramesView(APIImageView):
    url = "/cameras/{camera_id}/events/{event_id}/frames"
    name = "api:camera-event-frames"
    description = "Returns a frames from an event as specified by camera_id, event_id"

    async def get(self, request):
        camera_id = request.match_info['camera_id']
        event_id = request.match_info['event_id']

        mm = request.app[KEY_MM]
        try:
            camera = mm.cameras[camera_id]
            event = camera.recent_motion[event_id]
        except KeyError:
            _LOGGER.error("Invalid cameraId: {}".format(camera_id))
            raise HTTPBadRequest()

        response = self.to_entity_repr(request, ["frames"], path_params={"camera_id": camera_id, "event_id": event_id})
        for frame in event.frames.values():
            response["entities"].append(APICameraEventFrameView.to_link_repr(request, ["frame"],
                                                                             ["http://motion-monitor/rel/event_frame"],
                                                                             path_params={"camera_id": frame.camera_id,
                                                                                          "event_id": frame.event_id,
                                                                                          "timestamp": frame.timestamp.strftime("%Y%m%d%H%M%S"),
                                                                                          "frame": frame.frame_num}))

        return web.Response(text=json.dumps(response), content_type='application/json')


class APICameraEventFrameView(APIImageView):
    url = "/cameras/{camera_id}/events/{event_id}/frames/{timestamp}/{frame}"
    name = "api:camera-event-frame"
    description = "Returns a frame from an event as specified by camera_id, event_id, timestamp and frame"

    async def get(self, request):
        camera_id = request.match_info['camera_id']
        event_id = request.match_info['event_id']
        timestamp = datetime.strptime(request.match_info['timestamp'], "%Y%m%d%H%M%S")
        frame_num = request.match_info['frame']

        scale = self._get_scale_param(request)
        img_format = self._get_format_param(request)

        mm = request.app[KEY_MM]
        try:
            camera = mm.cameras[camera_id]
            frame = camera.recent_motion[event_id].frames[EventFrame.create_id(timestamp, frame_num)]
        except KeyError:
            _LOGGER.error("Invalid cameraId: {}".format(camera_id))
            raise HTTPBadRequest()

        frame_params = {
            "camera_id": camera_id,
            "event_id": frame.event_id,
            "timestamp": timestamp.strftime("%Y%m%d%H%M%S"),
            "score": frame.score,
            "frame": frame_num
        }
        return self._create_response(request, img_format, scale, frame, frame_params, self)

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
