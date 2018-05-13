
from .route_spec import route_base
from .exception import Invalidation

from .route_spec import RouteSpecDecoratorFactory

from .route import RouteModules

REST = RouteSpecDecoratorFactory('REST')
HTTP = RouteSpecDecoratorFactory('HTTP')
