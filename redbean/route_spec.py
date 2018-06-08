import logging
import aiohttp
import re
import inspect
from yarl import URL
from .path_params import parse_path, parse_fields

logger = logging.getLogger(__name__)

from .handler_argument import argument_getter_factory

from .exception import RESTfulDeclarationError

class RouteSpec():

    def __init__(self, spec_no, path, methods, handler_func):
        self._spec_no = spec_no

        self.path = path
        self.methods = methods
        self.handler_func = handler_func

        self.path_fields = None
        self.query_fields = None
        self.post_fields = None

    def __repr__(self):
        return (f"<RouteSpec '{self.path}' "
                f"[{','.join(self.methods)}] '{self.handler_func.__name__}' "
                f"in '{self.handler_func.__module__}'>")


class RouteMethodDecorator():
    """ 
    """
    
    def __init__(self, routes):
        self.methods = []
        self._routes = routes

    def __call__(self, path, query_fields=None, post_fields=None):

        def decorator(handler):
            if not inspect.iscoroutinefunction(handler):
                raise TypeError(f"handler '{handler.__name__}' " 
                                "should be coroutine function")
                    
            assert handler
            prefix = self._get_module_prefix(inspect.getmodule(handler).__name__)
            abspath = _pathjoin(prefix, path)
            abspath = URL._normalize_path(abspath) 

            spec_no = self._routes._inc_spec_no()
            spec = RouteSpec(spec_no, abspath, self.methods, handler)
            spec.query_fields = parse_fields(query_fields)
            spec.post_fields = parse_fields(post_fields)

            path_pattern, path_sign, path_fields  = parse_path(abspath)
            spec.path_pattern   = path_pattern
            spec.path_signature = path_sign
            spec.path_fields    = path_fields            
            spec.path_formatter = path_sign.format(*("{"+p+"}" for p in path_fields))


            spec._argument_getters = argument_getter_factory(spec)
            

            handlers = self._routes._handlers
            if handler not in handlers:
                handlers[handler] = [spec]
            else:
                handlers[handler].append(spec)

            return handler

        return decorator

    def __getattr__(self, method):
        return self._add_method(method)


    def _get_module_prefix(self, module_name):
        module_paths = self._routes._module_paths

        prefix = self._routes._module_paths.get(module_name)
        if prefix is not None and prefix.startswith('/'):
            return prefix

        parts = module_name.rsplit('.', maxsplit=1)
        if len(parts) == 1: # 顶层模块
            raise ValueError(f"The root module requires the prefix")

        parent = self._get_module_prefix(parts[0]) # 父级模块的前缀
        if prefix is None:
            # 模块没有设置路径，因此采用模块名作为本级目录
            prefix = _pathjoin(parent, parts[1])
            
        else:
            prefix = _pathjoin(parent, prefix)

        module_paths[module_name] = prefix

        return prefix

    def _add_method(self, method):
        method = method.upper()
        if method not in ['GET', 'POST', 'PUT', 'DELETE']:
            raise ValueError(f"Not support {method}")

        self.methods.append(method)
        return self


def _pathjoin(parent, part):
    assert not part.startswith('/')

    return parent + '/' + part

