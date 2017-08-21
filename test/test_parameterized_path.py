import pytest

from redbean.route import parse_pathexpr

def test_parse_pathexpr():
    path = '/a/{b}/x/{c:int}/z'

    resource = parse_pathexpr(path)
    print(resource)
