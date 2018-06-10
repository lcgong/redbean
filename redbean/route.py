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

from aiohttp.web_exceptions import HTTPException
from redbean.exception import RESTfulServerError, RESTfulDeclarationError

class RESTfulModules():

    def __init__(self):

        self._secure_layer = None

        self._spec_max_no = 0

        self._handlers = {}

        self._root_modules = {}
        self._module_paths = None  
        self._app = None
        self._on_cleanup_callbacks = None

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
    
    def permission_verifier(self, verifier_func):
        """ 标记进行权限检查的函数.

            返回当前用户身份第一个匹配成功的有效权限标签
        """

        self._secure_layer.set_permission_verifier(verifier_func)
        return verifier_func
    
    def on_cleanup(self, callback):
        if self._on_cleanup_callbacks is None:
            self._on_cleanup_callbacks = [callback]
        else:
            self._on_cleanup_callbacks.append(callback)
        
    def __getattr__(self, method):
        return RouteMethodDecorator(self)._add_method(method)

    def set_path(self, path):
        assert len(path) >= 1
        module = inspect.getmodule(sys._getframe(1))
        self._module_paths[module.__name__] = path

    def add_module(self, module_name, *, prefix='/'):
        self._root_modules[module_name] = prefix

    def setup(self, app):
        self._app = app

        secure_key = app['secure_key']
        self._handlers = {}

        self._secure_layer = SecureLayer(secure_key)
        app['secure_layer'] = self._secure_layer

        app.on_startup.append(self._app_on_start)
        app.on_cleanup.append(self._app_on_cleanup) 

    async def _app_on_start(self, app):
        self._module_paths = self._root_modules.copy()
        deep_load_moduels(sorted(set(self._root_modules.keys())))

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
        for callback in self._on_cleanup_callbacks:
            await callback()
                       
    def _inc_spec_no(self):
        self._spec_max_no += 1
        return self._spec_max_no


from .handler_response import make_response_writer

def handler_factory(route_spec, method, secure_layer):

    handler = route_spec.handler_func

    if secure_layer:
        permissions = secure_layer._guarded_handlers.get(handler)
    else:
        permissions = None

    if permissions:
        permissions = sorted(permissions, key=lambda p : str(p))
        # 因为设置的所需权限，需配置权限检查器
        if secure_layer._permission_verifier is None:
            errmsg = "The hook 'permission_verifier(identity, perms)' is required"
            raise RESTfulDeclarationError(text=errmsg)

    if secure_layer and handler in secure_layer._prepare_session_handlers:
        # 
        async def _service_handler(request):
            arguments = await route_spec._argument_getters(request)
            identity = await handler(**arguments)

            response = await secure_layer.open_session(request, identity)
            return response

    elif secure_layer and handler in secure_layer._close_session_handlers:
        # 
        async def _service_handler(request):
            identity = await secure_layer.identify(request)
            if permissions:
                await secure_layer.verfiy_permissions(request, identity, permissions)

            arguments = await route_spec._argument_getters(request)
            await handler(**arguments)
            
            response = await secure_layer.close_session(request, identity)
            return response            

    else:
        async def _service_handler(request):
            if permissions:
                identity = await secure_layer.identify(request)
                await secure_layer.verfiy_permissions(request, identity, permissions)
    
            arguments = await route_spec._argument_getters(request)
            return await handler(**arguments)

    resp_writer  = make_response_writer("REST", method, handler)
    async def _request_handler(request):
        try:
            ret_val = await _service_handler(request)
            return resp_writer(request, ret_val)
        except HTTPException as exc:
            request.app.logger.error(f'HTTP Error: {str(exc)}', exc_info=True)
            raise
        except Exception as exc:
            request.app.logger.error(f'Internal Error: {str(exc)}', exc_info=True)
            raise RESTfulServerError(data=dict(error=str(exc))) from exc

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

