import pytest

from redbean.path_params import parse_path
from redbean.route import RouteSpec

def test_parse_pathexpr():
    print()
    
    path = '/a/{b}/x/{c:int}/z'

    path_pattern, path_sign, path_fields  = parse_path(path)
    print(path_pattern)
    print(path_sign)
    print(path_fields)

