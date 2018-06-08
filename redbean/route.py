import logging
logger = logging.getLogger(__name__)

import inspect
import re
import sys
from yarl import URL

import aiohttp
from inspect import getmodule

# from .handler import request_handler_factory

from .path_params import parse_path, parse_fields
from .route_spec import RouteMethodDecorator
from .secure.secure import SecureLayer

class RESTfulModules():

    def __init__(self):

        self._secure_layer = SecureLayer()

        self._spec_max_no = 0

        self._handlers = {}

        self._root_modules = {}
        self._module_paths = None  

    def prepare_session(self, handler):
        self._secure_layer.add_prepare_session(handler)
        return handler 

    def close_session(self, handler):
        self._secure_layer.add_close_session(handler)
        return handler
        
    def guarded(self, *permissions):
        def decorator(handler):
            self._secure_layer.add_guarded(handler, permissions)
            return handler

        return decorator
        
    def __getattr__(self, method):
        return RouteMethodDecorator(self)._add_method(method)

    def set_path(self, path):
        assert len(path) >= 1
        module = inspect.getmodule(sys._getframe(1))
        self._module_paths[module.__name__] = path

    def add_module(self, module_name, *, prefix='/'):
        self._root_modules[module_name] = prefix

    def setup(self, app):
        self._handlers = {}
        

        app.on_startup.append(self._app_on_start)
        app.on_cleanup.append(self._app_on_cleanup) 


        print(8889, self._root_modules)
        

        # for handler, permissions in self._guarded_handlers.items():
        #     specs = self._handlers.get(handler)
        #     if not specs:
        #         raise SyntaxError('its not rest handler: ' + handler.__qualname__)

        #     for spec in specs:
        #         assert spec._permissions is None
        #         spec._permissions = permissions
        #         spec._secure = self._secure

        # for handler in self._session_enter_handlers:
        #     specs = self._handlers.get(handler)
        #     if not specs:
        #         raise SyntaxError('its not rest handler: ' + handler.__qualname__)

        #     for spec in specs:
        #         spec._session_enter = True
        #         spec._secure = self._secure

        # for handler in self._session_exit_handlers:
        #     specs = self._handlers.get(handler)
        #     if not specs:
        #         raise SyntaxError('its not rest handler: ' + handler.__qualname__)
        #     for spec in specs:
        #         spec._session_exit = True 
        #         spec._secure = self._secure 

    async def _app_on_start(self, app):
        self._module_paths = self._root_modules.copy()
        deep_load_moduels(sorted(set(self._root_modules.keys())))

        print( self._module_paths )

        specs = []
        for spec in self._handlers.values():
            specs += spec
        specs = sorted(specs, key=lambda s : s._spec_no) # 按出现顺序排序

        for spec in specs:

            resource  = DynamicResource(spec.path_pattern, spec.path_formatter)
            app.router.register_resource(resource)

            for method in spec.methods:
                handler = handler_factory(spec, method, self._secure_layer)
                # handler = self._secure_layer.decorate(spec, handler)
                # assert handler
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

    async def _app_on_cleanup(self, app):
        logger.debug('cleanup routes') 
                       
    def _inc_spec_no(self):
        self._spec_max_no += 1
        return self._spec_max_no


from .handler_response import make_response_writer

def handler_factory(route_spec, method, secure_layer):

    handler_func = route_spec.handler_func

    resp_writer  = make_response_writer("REST", method, handler_func)

    async def _service_handler(request):
        arguments = await route_spec._argument_getters(request)
        return await handler_func(**arguments)    

    _secured_handler = secure_layer.decorate(route_spec, _service_handler)

    async def _request_handler(request):
        ret_val = await _secured_handler(request)
        return resp_writer(request, ret_val)

    return _request_handler

        
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
        self._pattern = re.compile(re.escape(prefix) + self._pattern.pattern)
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

import importlib
from pkgutil import walk_packages

def deep_load_moduels(root_names):
    for module_name in root_names:
        for module in _iter_submodules(module_name):
            pass  
           

def _iter_submodules(module):
    """  """
    if isinstance(module, str):
        logger.debug('dynamic loading module: ' + module)    
        module = importlib.import_module(module)
    
    if not hasattr(module, '__path__'):
        yield module
        return

    if isinstance(module.__path__, list): # no namespace package
        yield module

    prefix = module.__name__ + '.'

    for loader, module_name, ispkg in walk_packages(module.__path__, prefix):
        module = loader.find_module(module_name).load_module(module_name)
        if ispkg and not isinstance(module.__path__, list):
            continue

        yield module

