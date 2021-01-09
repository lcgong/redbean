import aiohttp.web

from .web.rest import rest_method
from .utils import load as load_modules

class RouteTableDef(aiohttp.web.RouteTableDef):
    pass

from .web.application import Application
from .main import cli