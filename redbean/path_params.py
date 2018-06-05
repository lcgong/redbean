import re
from yarl import URL
from collections.abc import Sequence

_SPACE_COMMA_SEPERATOR_RE = re.compile(r'\s*[,]?\s*')
def parse_fields(expr):
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

def parse_path(pathexpr):

    # pathexpr = route_spec.path

    pattern, signature = '', ''

    fields = []
    startpos = 0
    for param_part in _ROUTE_RE.finditer(pathexpr):
        part = param_part.group(0)

        param_name, param_regex = _parse_pathexpr_part(part)
        if param_name in fields:
            raise ValueError(f"duplicated '{{{param_name}}}' in '{pathexpr}'");

        fields.append(param_name)

        norm_part  = _escape_norm_part(pathexpr, startpos, param_part.start())
        
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

    return pattern, signature, fields



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
                f"Unknown type '{param_type}' in ['{part}']"
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
