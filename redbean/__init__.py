

# from .route_spec import page_view, rest_service, http_request
from .route_spec import route_base
from .app import Application
from .exception import Invalidation

from .route_spec import RouteSpecDecorator

REST = RouteSpecDecorator('REST')
HTTP = RouteSpecDecorator('HTTP')
