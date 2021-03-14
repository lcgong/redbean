
from redbean.dobject.utils import is_complaint

from dataclasses import dataclass
from typing import List, Dict, Union, _GenericAlias, get_args, get_origin

def test_compliant_1():
    assert is_complaint([1,2,3], List[int])

    assert is_complaint({"a":1}, Dict[str, int])
    assert not is_complaint({"a": "b"}, Dict[str, int])


def test_compliant_1():
    @dataclass
    class A:
        a: str

    assert is_complaint(A("a"), A)