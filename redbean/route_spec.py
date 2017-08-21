
import inspect
import re
import sys
from yarl import URL


routespec_registry = {}
def get_routespec_group(module_name):

    routespec_group = routespec_registry.get(module_name)
    if routespec_group is not None:
        return routespec_group

    routespec_group = RouteSpecGroup()
    routespec_registry[module_name] = routespec_group

    return routespec_group


def route_base(base_path):
    module = inspect.getmodule(sys._getframe(1))
    routespec_group = get_routespec_group(module.__name__)
    # if len(routespec_group._route_specs) > 1:
    #     raise ValueError('The route base should be defined before route declarations')

    if not base_path:
        base_path = './'
    elif not base_path.endswith('/'):
        base_path += '/'

    routespec_group.base_path = base_path

class RouteSpecGroup:

    def __init__(self):
        self._base_path = None
        self._route_specs = []

    @property
    def base_path(self):
        return self._base_path

    @base_path.setter
    def base_path(self, path):
        self._base_path = path

    def add(self, spec):
        self._route_specs.append(spec)

class RouteSpec():

    def __init__(self, proto):
        self.handler_func = None

        self.proto = proto        # http protocol
        self.methods = []         # http methods

        self.code_filename = None
        self.code_lineno = None

    def add_method(self, method):
        self.methods.append(method)

    def __call__(self, path):

        self.path = path

        def decorator(handler_func):
            frame = sys._getframe(1)
            if frame:
                self.code_filename = frame.f_code.co_filename
                self.code_lineno = frame.f_lineno

            self.handler_func = handler_func

            module = inspect.getmodule(frame)
            routespec_group = get_routespec_group(module.__name__)

            routespec_group.add(self)

            return handler_func

        return decorator

    def __repr__(self):
        return (f"<RouteSpec '{self.path}' "
                f"[{','.join(self.methods)}] '{self.handler_func.__name__}' "
                f"in '{self.handler_func.__module__}'>")

    @property
    def GET(self) :
        self.methods.append('GET')
        return self

    @property
    def POST(self) :
        self.methods.append('POST')
        return self

    @property
    def PUT(self) :
        self.methods.append('PUT')
        return self

    @property
    def DELETE(self) :
        self.methods.append('DELETE')
        return self


_SPACE_COMMA_SEPERATOR_RE = re.compile(r'\s*[,]?\s*')

class RouteSpecDecorator():

    def __init__(self, proto):
        self.proto = proto

    def __call__(self, path, *, methods=None):
        """
        method: 'GET,POST' or 'GET POST'
        """
        route_spec = RouteSpec(self.proto)
        if methods and isinstance(methods, str):
            for method in SPACE_COMMA_SEP_RE.split(methods):
                route_spec.add_method(method)

        route_spec.path = path

        return route_spec

    @property
    def GET(self) :
        return RouteSpec(self.proto).GET

    @property
    def POST(self) :
        return RouteSpec(self.proto).POST

    @property
    def PUT(self) :
        return RouteSpec(self.proto).PUT

    @property
    def DELETE(self) :
        return RouteSpec(self.proto).DELETE


rest_service = RouteSpecDecorator('REST_SERIVCE')
page_view    = RouteSpecDecorator('PAGE_VIEW')
http_request = RouteSpecDecorator('HTTP_REQUEST')


_ROUTE_RE = re.compile(r'(\{[_a-zA-Z][^{}]*(?:\{[^{}]*\}[^{}]*)*\})')
_SOLID_PARAM_RE = re.compile(r'\{(?P<var>[_a-zA-Z][_a-zA-Z0-9]*)\}')
_TYPED_PARAM_RE = re.compile(r'\{(?P<var>[_a-zA-Z][_a-zA-Z0-9]*):(?P<type>\s*(?:int|float|str|path))\s*\}')
_REGEX_PARAM_RE = re.compile(r'\{(?P<var>[_a-zA-Z][_a-zA-Z0-9]*):(?P<re>.+)\}')

def parse_path(pathexpr):

    pattern, signature = '', ''

    parameters = []
    startpos = 0
    for param_part in _ROUTE_RE.finditer(pathexpr):
        part = param_part.group(0)

        param_name, param_regex = _parse_pathexpr_part(part)
        if param_name in parameters:
            raise ValueError(f"duplicated '{{{param_name}}}' in '{pathexpr}'");

        parameters.append(param_name)

        norm_part  = _escape_norm_part(pathexpr, startpos, param_part.start())
        pattern   += re.escape(norm_part) + f'(?P<{param_name}>{param_regex})'
        signature += norm_part + '{}'
        startpos = param_part.end()

    norm_part  = _escape_norm_part(pathexpr, startpos, None)
    pattern   += norm_part
    signature += norm_part

    try:
        pattern = re.compile(pattern)
    except re.error as exc:
        raise ValueError(
            "Bad pattern '{}': {}".format(pattern, exc)) from None

    return signature, parameters, pattern

def _parse_pathexpr_part(part):
    match = _SOLID_PARAM_RE.fullmatch(part)
    if match:
        return match.group('var'), r'[^{}/]+'

    match = _TYPED_PARAM_RE.fullmatch(part)
    if match:
        param_type = match.group('type')
        if param_type == 'int':
            re_expr = r'[+-]?\d+'
        elif param_type == 'float':
            re_expr = r'[+-]?\d+(?:\.\d+(?:[eE][+-]?\d+)?)?'
        elif param_type == 'str':
            re_expr = r'[^{}/]+'
        elif param_type == 'path':
            re_expr = r'[^{}]+'
        else:
            raise ValueError(
                f"Unknown type '{param_type}' in path '{path}'['{part}']"
            )

        return match.group('var'), re_expr

    match = _REGEX_PARAM_RE.fullmatch(part)
    if match:
        return match.group('var'), match.group('re')

    return None, None

def _escape_norm_part(path, startpos, endpos):
    normal_part = path[startpos:endpos]
    if '{' in normal_part or '}' in normal_part:
        raise ValueError("Invalid path '{}'['{}']".format(path, normal_part))

    return URL(normal_part).raw_path
