import aiohttp.web

from .web.rest import rest_method
from .utils import load as load_modules

class RouteTableDef(aiohttp.web.RouteTableDef):
    pass

from .web.routedef import RestServiceDef
from .logs import log_application_routes

# from .web.application import Application
from .main import cli