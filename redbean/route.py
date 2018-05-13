import inspect
from urllib.parse import urljoin
from collections import OrderedDict
from pkgutil import walk_packages
from importlib import  import_module
from yarl import URL

# from aiohttp.web_urldispatcher import DynamicResource
from aiohttp.web_urldispatcher import Resource

from .handler import request_handler_factory
from .route_spec import parse_path, routespec_registry

import aiohttp.web

class DynamicResource(Resource):

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


    # def url(self, *, parts, query=None):
    #     super().url(**parts)
    #     return str(self.url_for(**parts).with_query(query))

    def __repr__(self):
        name = "'" + self.name + "' " if self.name is not None else ""
        return ("<DynamicResource {name} {formatter}>"
                .format(name=name, formatter=self._formatter))

# from collections.abc import Sequence

from aiohttp.web_routedef import AbstractRouteDef

from aiohttp import hdrs

class RouteDef(AbstractRouteDef):

    def __inti__(self, spec, method, path, handler, **kwargs):
        self.spec = spec
        self.method = method
        self.path = path
        self.handler = handler
        self.kwargs = kwargs


    def __repr__(self):
        info = []
        for name, value in sorted(self.kwargs.items()):
            info.append(", {}={!r}".format(name, value))
        return ("<RouteDef {method} {path} -> {handler.__name__!r}"
                "{info}>".format(method=self.method, path=self.path,
                                 handler=self.handler, info=''.join(info)))

    def register(self, router):
        if self.method in hdrs.METH_ALL:
            reg = getattr(router, 'add_'+self.method.lower())
            reg(self.path, self.handler, **self.kwargs)
        else:
            router.add_route(self.method, self.path, self.handler,
                            **self.kwargs)


# class Application(aiohttp.web.Application):

#     def __init__(self, *args, **kwargs):
#         super(Application, self).__init__(**kwargs)
#         self._modules = []

#         self.on_startup.append(_on_startup)

#     def add_module(self, root, *, prefix='/'):
#         self._modules.append((root,prefix))

# def _on_startup(app):
#     for root, prefix in app._modules:
#         register_module(app, root, prefix=prefix)

#     print_route_specs(app)

# def print_route_specs(app):
#     infos = []
#     for resource in app.router._resources:
#         for route in resource:
#             method = route.method
#             formatter = route._resource._formatter
#             func_name = route._route_spec.handler_func.__qualname__
#             module_name = route._route_spec.handler_func.__module__
#             infos.append(f"[{method}]{formatter} => {func_name} in {module_name}")

#     app.logger.info('Route Definition:\n' + '\n'.join(infos) + '\n')

class RouteModules(object):
    """Route definition table for modules"""

    def __init__(self,  *modules, prefix='/'):
        self._modules = [(m, prefix) for m in modules]

    def add_module(self, root, *, prefix='/'):
        self._modules.append((root,prefix))

    def setup(self, app):
        for root, prefix in self._modules:
            self._register_module(app, root, prefix)


    # def print_route_specs(app):
        infos = []
        for resource in app.router._resources:
            for route in resource:
                method = route.method
                formatter = route._resource._formatter
                func_name = route._route_spec.handler_func.__qualname__
                module_name = route._route_spec.handler_func.__module__
                infos.append(f"[{method}]{formatter} => {func_name} in {module_name}")

        app.logger.info('Route Definition:\n' + '\n'.join(infos) + '\n')
            
    
    def _register_module(self, app, root, prefix):

        for module_name in list(routespec_registry.keys()):
            if module_name.startswith(root):
                del routespec_registry[module_name]

        if not prefix.startswith('/') :
            raise ValueError(f"The prefix '{prefix}' should start with '/'")

        assert isinstance(root, str) and len(root) > 1 and not root.endswith('.')

        resources = OrderedDict() # group route specs by the path's pattern
        for path_base, route_specs in _normal_path_base(root, prefix):
            for spec in route_specs:
                spec.set_prefix(path_base)
                group_key = (spec.path_pattern, spec.path_formatter)
                if group_key not in resources:
                    resources[group_key] = [spec]
                else:
                    specs = resources[group_key]

                    for s in specs: # check method conflict
                        for m in spec.methods:
                            if m in s.methods:
                                raise ValueError('confict method')

                    specs.append(spec)

        for (path_pattern, path_formatter), specs in resources.items():

            # print(path_formatter, path_formatter, specs)
            resource  = DynamicResource(path_pattern, path_formatter)
            # resource  = DynamicResource(path_pattern)
            # resource  = DynamicResource(path_pattern, path_formatter)
            # print(resource)
            app.router.register_resource(resource)

            # print(7777, path_pattern.pattern)
            # resource = app.router.add_resource(path_pattern.pattern)

            for route_spec in specs:
                for method in route_spec.methods:
                    handler = request_handler_factory(route_spec, method)

                    route = resource.add_route(method, handler)
                    setattr(route, '_route_spec', route_spec)

def _parent_name(module_name):
    idx = module_name.rfind('.')
    return module_name[0:idx] if idx != -1 else ''

def _stem_name(module_name):

    if not module_name: return ''

    idx = module_name.rfind('.')
    return (module_name[(idx+1):] if idx != -1 else module_name) + '/'

def _normal_path_base(root, prefix):
    if not prefix.endswith('/'):
        prefix += '/'

    path_start = len(root) + 1

    module_prefixs = {}
    module_prefixs[''] = prefix
    for module in _iter_submodules(root):

        module_name = module.__name__[path_start:]
        parent_name = _parent_name(module_name)

        route_group = routespec_registry.get(module.__name__)
        if route_group is None:
            path_base = urljoin(module_prefixs[parent_name], _stem_name(module_name))
            module_prefixs[module_name] = path_base
            continue

        if route_group.base_path is None:
            path_base = _stem_name(module_name)
        else:
            path_base = route_group.base_path

        path_base = urljoin(module_prefixs[parent_name], path_base)

        module_prefixs[module_name] = path_base

        if route_group._route_specs:
            yield (path_base, route_group._route_specs)

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
