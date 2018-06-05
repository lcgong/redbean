
import inspect
import re
import sys
from yarl import URL
from inspect import getmodule
from importlib import  import_module
from pkgutil import walk_packages
import aiohttp

from .handler import request_handler_factory

from .path_params import parse_path, parse_fields


class DynamicResource(aiohttp.web_urldispatcher.Resource):

    def __init__(self, pattern, formatter, *, name=None):
        super().__init__(name=name)
        assert pattern.pattern.startswith('/')
        # assert pattern.pattern.startswith('\\/')
        assert formatter.startswith('/')
        self._pattern = pattern
        self._formatter = formatter


    def add_prefix(self, prefix):
        assert prefix.startswith('/')
        assert not prefix.endswith('/')
        assert len(prefix) > 1
        self._pattern = re.compile(re.escape(prefix)+self._pattern.pattern)
        self._formatter = prefix + self._formatter

    def _match(self, path):
        match = self._pattern.fullmatch(path)
        if match is None:
            return None
        else:
            return {key: URL.build(path=value, encoded=True).path
                    for key, value in match.groupdict().items()}

    def raw_match(self, path):
        return self._formatter == path

    def get_info(self):
        return {'formatter': self._formatter, 'pattern': self._pattern}

    def url_for(self, **parts):
        url = self._formatter.format_map({k: URL.build(path=v).raw_path
                                          for k, v in parts.items()})
        return URL.build(path=url)


    def __repr__(self):
        name = "'" + self.name + "' " if self.name is not None else ""
        return ("<DynamicResource {name} {formatter}>"
                .format(name=name, formatter=self._formatter))


class RouteSpec():

    def __init__(self, spec_no, path, methods, handler_func):
        self._spec_no = spec_no

        self.path = path
        self.methods = methods
        self.handler_func = handler_func

        self.path_fields = None
        self.query_fields = None
        self.post_fields = None

        self._permissions = None
        self._session_exit = None
        self._session_enter = None
        self._secure = None

        self._precondition = None
        self._postcondition = None

    def __repr__(self):
        return (f"<RouteSpec '{self.path}' "
                f"[{','.join(self.methods)}] '{self.handler_func.__name__}' "
                f"in '{self.handler_func.__module__}'>")


from .secure.secure import AccessCotrol

class RESTfulModules():

    def __init__(self, prefix):

        self._spec_max_no = 0

        self._secure = AccessCotrol()

        self._handlers = {}

        self._module_prefix = prefix if prefix else {}
        self._module_paths = self._module_prefix

        self._guarded_handlers = {}
        self._session_enter_handlers = []
        self._session_exit_handlers = []


    def session_enter(self, handler):
        self._session_enter_handlers.append(handler)
        return handler

    def session_exit(self, handler):
        self._session_exit_handlers.append(handler)
        return handler
        
    def guarded(self, *permissions):
        def decorator(handler):

            if handler not in self._guarded_handlers:
                self._guarded_handlers[handler] = list(permissions)
            else:
                self._guarded_handlers[handler] += permissions

            return handler

        return decorator

        
    def __getattr__(self, method):
        return RouteMethodDecorator(self)._add_method(method)

    def set_path(self, path):
        assert len(path) >= 1
        module = inspect.getmodule(sys._getframe(1))
        self._module_paths[module.__name__] = path

    def setup(self, app):
        for module_name in sorted(set(self._module_prefix.keys())):
            for module in _iter_submodules(module_name):
                app.logger.debug('dynamic loaded module: ' + module.__name__)

        for handler, permissions in self._guarded_handlers.items():
            specs = self._handlers.get(handler)
            if not specs:
                raise SyntaxError('its not rest handler: ' + handler.__qualname__)

            for spec in specs:
                assert spec._permissions is None
                spec._permissions = permissions
                spec._secure = self._secure

        for handler in self._session_enter_handlers:
            specs = self._handlers.get(handler)
            if not specs:
                raise SyntaxError('its not rest handler: ' + handler.__qualname__)

            for spec in specs:
                spec._session_enter = True
                spec._secure = self._secure

        for handler in self._session_exit_handlers:
            specs = self._handlers.get(handler)
            if not specs:
                raise SyntaxError('its not rest handler: ' + handler.__qualname__)
            for spec in specs:
                spec._session_exit = True
                spec._secure = self._secure

        specs = []
        for spec in self._handlers.values():
            specs += spec
        specs = sorted(specs, key=lambda s : s._spec_no) # 按出现顺序排序

        for spec in specs:
            spec._precondition = _precondition_factory(spec)
            spec._postcondition = _postcondition_factory(spec)

            resource  = DynamicResource(spec.path_pattern, spec.path_formatter)
            app.router.register_resource(resource)

            for method in spec.methods:
                handler = request_handler_factory(spec, method)
                route = resource.add_route(method, handler)
                setattr(route, '_route_spec', spec)

        infos = []
        for resource in app.router._resources:
            for route in resource:
                method = route.method
                formatter = route._resource._formatter
                func = route._route_spec.handler_func.__qualname__
                module = route._route_spec.handler_func.__module__
                infos.append(f"{formatter} [{method}] => {func} in {module}")

        app.logger.info('Route Definition:\n' + '\n'.join(infos) + '\n')
                       
    def _inc_spec_no(self):
        self._spec_max_no += 1
        return self._spec_max_no

def _precondition_factory(spec):
    if spec._permissions is None and not spec._session_exit:
        return None

    async def filter(request):
        if spec._permissions is not None:
            await spec._secure.permits(request, spec._permissions)

        if spec._session_exit:
            print('session exit')

    return filter

import json

def _postcondition_factory(spec, session_enter=False):

    if spec._session_enter:
        async def filter(request, return_value, response):
            print('session enter: ' + json.dumps(return_value))

        return filter

    return None


class RouteMethodDecorator():
    """ 
    
    """
    
    def __init__(self, routes):
        self.methods = []
        self._routes = routes

    def __call__(self, path, query_fields=None, post_fields=None):

        def decorator(handler):
            prefix = self._get_module_prefix(getmodule(handler).__name__)
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



def _iter_submodules(root_module, recursive=True):
    """  """
    if isinstance(root_module, str):
        root_module = import_module(root_module)
    
    if not hasattr(root_module, '__path__'):
        yield root_module
        return

    if isinstance(root_module.__path__, list): # no namespace package
        yield root_module

    if not recursive:
        return

    prefix = root_module.__name__ + '.'

    for loader, module_name, ispkg in walk_packages(root_module.__path__, prefix):
        module = loader.find_module(module_name).load_module(module_name)
        if ispkg and not isinstance(module.__path__, list):
            continue

        yield module

