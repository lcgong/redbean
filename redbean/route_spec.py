
import inspect
import re
import sys
from yarl import URL
from urllib.parse import urljoin


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

    def __init__(self, proto, path, methods):
        self.proto = proto
        self.path = path
        self.methods = methods

        self.handler_func = None

        self.path_fields = None
        self.query_fields = None
        self.post_fields = None

        self.code_filename = None
        self.code_lineno = None

        self.abspath = None
        self._prefix = None

    @property
    def prefix(self):
        return self._prefix

    def set_prefix(self, path_prefix):
        self.abspath = urljoin(path_prefix, self.path)
        parse_path(self, self.abspath)


    def __repr__(self):
        return (f"<RouteSpec '{self.path}' "
                f"[{','.join(self.methods)}] '{self.handler_func.__name__}' "
                f"in '{self.handler_func.__module__}'>")

def _register_route_spect(route_spec, frame):
    assert frame

    route_spec.code_filename = frame.f_code.co_filename
    route_spec.code_lineno = frame.f_lineno

    caller_module = inspect.getmodule(frame)
    routespec_group = get_routespec_group(caller_module.__name__)
    routespec_group.add(route_spec)

class RouteSpecDecorator():
    def __init__(self, proto):
        self.proto = proto
        self.methods = []

    def __call__(self, path, query_fields=None, post_fields=None):

        def decorator(handler_func):

            route_spec = RouteSpec(self.proto, path, self.methods)

            route_spec.handler_func = handler_func
            route_spec.query_fields = _parse_fields(query_fields)
            route_spec.post_fields = _parse_fields(post_fields)

            _register_route_spect(route_spec, frame=sys._getframe(1))

            return handler_func

        return decorator

    def __getattr__(self, method):
        return self.add_method(method)

    def add_method(self, method):
        method = method.upper()
        if method not in ['GET', 'POST', 'PUT', 'DELETE']:
            raise ValueError(f"Not support {method}")

        self.methods.append(method)
        return self


class RouteSpecDecoratorFactory():

    def __init__(self, proto):
        self.proto = proto
        self.methods = []

    def __getattr__(self, method):
        decorator = RouteSpecDecorator(self.proto)
        return decorator.add_method(method)


_SPACE_COMMA_SEPERATOR_RE = re.compile(r'\s*[,]?\s*')
def _parse_fields(expr):
    if not expr:
        return []

    if expr and isinstance(expr, str):
        return list(m for m in _SPACE_COMMA_SEPERATOR_RE.split(expr))

    if isinstance(expr, Sequence):
        for m in expr:
            if not isinstance(m, str):
                raise ValueError(f"unkown type '{m.__class__.__name__}'")
        return expr

    raise ValueError(f"unknown type {expr} ")


_ROUTE_RE = re.compile(r'(\{[_a-zA-Z][^{}]*(?:\{[^{}]*\}[^{}]*)*\})')
_SOLID_PARAM_RE = re.compile(r'\{(?P<var>[_a-zA-Z][_a-zA-Z0-9]*)\}')
_TYPED_PARAM_RE = re.compile(r'\{(?P<var>[_a-zA-Z][_a-zA-Z0-9]*):(?P<type>\s*(?:int|float|str|path))\s*\}')
_REGEX_PARAM_RE = re.compile(r'\{(?P<var>[_a-zA-Z][_a-zA-Z0-9]*):(?P<re>.+)\}')

def parse_path(route_spec, pathexpr):

    pattern, signature = '', ''

    # print(999, pathexpr)

    fields = []
    startpos = 0
    for param_part in _ROUTE_RE.finditer(pathexpr):
        part = param_part.group(0)
        # print(733, part)

        param_name, param_regex = _parse_pathexpr_part(part)
        if param_name in fields:
            raise ValueError(f"duplicated '{{{param_name}}}' in '{pathexpr}'");

        fields.append(param_name)

        norm_part  = _escape_norm_part(pathexpr, startpos, param_part.start())
        
        # print(111, norm_part, re.escape(norm_part))


        pattern   += norm_part + f'(?P<{param_name}>{param_regex})'
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
    # print(555, pattern)

    route_spec.path_signature = signature
    route_spec.path_fields    = fields
    route_spec.path_pattern   = pattern
    route_spec.path_formatter = signature.format(*("{"+p+"}" for p in fields))


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
