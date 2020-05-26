import json
import logging

from aiohttp import web
from aiohttp.web_exceptions import HTTPBadRequest

from motionmonitor.const import KEY_MM

_LOGGER = logging.getLogger(__name__)


def get_extension(mm):
    return API(mm)


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

        if not hasattr(view, "url"):
            class_name = view.__class__.__name__
            raise AttributeError(f'{class_name} missing required attribute "url"')

        if not hasattr(view, "name"):
            class_name = view.__class__.__name__
            raise AttributeError(f'{class_name} missing required attribute "name"')

        view.register(self.app, self.app.router)
        _LOGGER.debug("View '{}' has been registered.".format(view.name))


class BaseAPIView:
    """Base view for all views."""

    url = None
    name = None
    extra_urls = []

    def register(self, app, router):
        """Register the view with a router."""
        _LOGGER.debug("Attempting to register our view")
        assert self.url is not None, "No url set for view"

        for method in ("get", "post", "delete", "put", "patch", "head", "options"):
            handler = getattr(self, method, None)

            if not handler:
                _LOGGER.debug("Couldn't locate a '{}' handler for the view.".format(method))
                continue

            router.add_route(method, self.url, handler, name=self.name)


class APIRootView(BaseAPIView):
    url = "/"
    name = "api:root"

    async def get(self, request):
        response = {"application": "Motion Monitor", "version": 0.1, "routes": []}
        for route in request.app.router.routes():
            route_desc = {"name": route.name, "method": route.method}
            # route_desc = {"name": route.name, "method": route.method, "url": str(route.url_for())}
            response["routes"].append(route_desc)
        return web.Response(text=json.dumps(response), content_type='application/json')


class APICamerasView(BaseAPIView):
    url = "/cameras"
    name = "api:cameras"

    async def get(self, request):
        mm = request.app[KEY_MM]
        response = {"cameras": []}
        for camera_id in mm.cameras:
            camera_desc = {"cameraId": camera_id,
                           "url": str(request.app.router[APICameraEntityView.name].url_for(camera_id=camera_id))}
            response["cameras"].append(camera_desc)
        response["count"] = len(response["cameras"])
        return web.Response(text=json.dumps(response), content_type='application/json')


class APICameraEntityView(BaseAPIView):
    url = "/cameras/{camera_id}"
    name = "api:camera-entity"

    async def get(self, request):
        camera_id = request.match_info['camera_id']

        mm = request.app[KEY_MM]
        try:
            response = mm.cameras[camera_id].to_json()
            return web.Response(text=json.dumps(response), content_type='application/json')
        except KeyError as e:
            raise HTTPBadRequest()
