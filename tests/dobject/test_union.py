import pytest

from redbean.dobject.cbor import DObjectCBOREncoder
from redbean.dobject import IncompliantError

from dataclasses import dataclass
from typing import List, Dict, Union, Optional


@dataclass
class A:
    n: int
    s: int
    m: int = None


@dataclass
class B:
    n: int
    m: int
    t: int


def test_union_dobj():

    encoder = DObjectCBOREncoder()

    a = A(1, 2, 3)
    b = encoder.decode(encoder.encode(a), Union[A, B, None])
    assert a == b
    assert isinstance(b, type(a))

    a = B(4, 5, 6)
    b = encoder.decode(encoder.encode(a), Union[A, B, None])
    assert a == b
    assert isinstance(b, type(a))
    # print(d)

    a = 123
    b = encoder.decode(encoder.encode(a), Union[A, int])
    assert a == b
    assert isinstance(b, type(a))

    with pytest.raises(IncompliantError):
        # 在Union内定义了str，但没有定义int，在Union这种定义内，不会执行默认的类型转换
        a = 123
        b = encoder.decode(encoder.encode(a), Union[A, str])

    with pytest.raises(IncompliantError):
        a = 123
        b = encoder.decode(encoder.encode(a), Union[A, None])

    a = None
    b = encoder.decode(encoder.encode(a), Union[A, None])

    a = None
    b = encoder.decode(encoder.encode(a), Optional[A])


    with pytest.raises(IncompliantError):
        a = None
        b = encoder.decode(encoder.encode(a), Union[A, int])


def test_union_dict():

    encoder = DObjectCBOREncoder()

    a = {"x": 100}
    b = encoder.decode(encoder.encode(a), Union[A, Dict[str, int]])
    assert a == b
    assert isinstance(b, type(a))

    # Union[A, Dict[str, int], Dict[str, str]])
    # => Union[A, Dict[str, Union[int, str]]]
    with pytest.raises(IncompliantError):
        a = {"x": 100}
        # Union内不能定义两个Dict或者List，但可以人工转换为一个Dict元素使用Union的方式
        b = encoder.decode(encoder.encode(a),
                           Union[A, Dict[str, int], Dict[str, str]])

    a = {"x": 100}
    b = encoder.decode(encoder.encode(a),
                       Union[A, Dict[str, Union[int, str]]])
    assert a == b

    a = {"x": "sn100"}
    b = encoder.decode(encoder.encode(a),
                       Union[A, Dict[str, Union[int, str]]])
    assert a == b

    a = {"x": A(1, 2, 3)}
    b = encoder.decode(encoder.encode(a),
                       Union[Dict[str, Union[A, B]], None])

    a = {"x": B(4, 5, 6)}
    b = encoder.decode(encoder.encode(a),
                       Union[Dict[str, Union[A, B]], None])

    with pytest.raises(IncompliantError):
        a = {"x": None}
        b = encoder.decode(encoder.encode(a),
                           Union[Dict[str, Union[A, B]], None])

def test_union_list():
    encoder = DObjectCBOREncoder()

    a = [1, 2, 3]
    b = encoder.decode(encoder.encode(a), Union[A, List[int]])
    assert a == b

    a = [1, 2, "10"]
    b = encoder.decode(encoder.encode(a), Union[A, List[Union[int, str]]])
    assert a == b

    a = [A(1, 2, 3), B(4, 5, 6), None]
    b = encoder.decode(encoder.encode(a), Union[A, List[Union[A, B, None]]])
    assert a == b

    with pytest.raises(IncompliantError):
        a = [A(1, 2, 3), B(4, 5, 6), None]
        b = encoder.decode(encoder.encode(a), Union[A, List[Union[A, B]]])

    a = [1, 2, "10"]
    b = encoder.decode(encoder.encode(a), Union[A, List[int]])
    assert b == [1, 2, 10]

    with pytest.raises(IncompliantError):
        a = [1, 2, 3]
        b = encoder.decode(encoder.encode(a), Union[A, List[int], List[str]])
        assert a == b
