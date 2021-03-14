import pytest

from enum import Enum

from redbean.dobject.cbor import DObjectCBOREncoder
from redbean.dobject.utils import is_complaint
from redbean.dobject import IncompliantError

from datetime import datetime, date, time as dt_time, timezone, timedelta
from decimal import Decimal
from typing import List, Dict, Union, Optional
from dataclasses import dataclass, fields


# https://github.com/hildjj/node-cbor
# https://marcosschroh.github.io/dataclasses-avroschema/primitive_types/

print()


class FileState(Enum):
    ACTIVE: str = "Active"
    DISABLED: str = "Disabled"


# @dataclass
# class C:
#     s: FileState


# # print(fields(C))

# c = C(s=FileState.ACTIVE)
# print(c.s.value)

# print(C(s=FileState("Disabled")))


def assert_encode(value, data_type=None, expected=None, encoder=None):
    if encoder is None:
        encoder = DObjectCBOREncoder()

    if data_type is None:
        data_type = type(value)

    decoded_value = encoder.decode(encoder.encode(value), data_type)
    print("D: ", value, " :==: ", decoded_value)

    if expected is None:
        assert decoded_value == value
    else:
        assert decoded_value == expected

    return is_complaint(decoded_value, data_type)


# def test_none_value():

#     def assert_encode_none(data_type):
#         encoder = DObjectCBOREncoder()
#         decoded = encoder.decode(encoder.encode(None), data_type)
#         assert decoded is None

#     assert_encode_none(str)
#     assert_encode_none(bytes)
#     assert_encode_none(int)
#     assert_encode_none(float)
#     assert_encode_none(bool)
#     assert_encode_none(datetime)
#     assert_encode_none(date)
#     assert_encode_none(Decimal)
#     assert_encode_none(List[int])
#     assert_encode_none(Dict[str, int])

#     @dataclass
#     class A:
#         v: str

#     assert_encode_none(A)


def test_datetime():
    # datetime必须指定时区，如果数据源没有指定，默认设置为以本地时区

    assert_encode(datetime.now().astimezone(), datetime)
    assert_encode("2000-10-01", datetime,
                  expected=datetime(2000, 10, 1).astimezone())

    expected = datetime(2021, 3, 10, 14, 32, 49, 96434,
                        tzinfo=timezone(timedelta(seconds=28800)))  # 设置为本地时区

    assert_encode("2021-03-10T14:32:49", datetime,
                  expected=datetime(2021, 3, 10, 14, 32, 49).astimezone())

    assert_encode("2021-03-10T14:32:49.096434", datetime,
                  expected=expected.astimezone())

    assert_encode("2021-03-10T14:32:49.096434+08:00", datetime,
                  expected=expected.astimezone())

    assert_encode("2021-03-10T06:32:49.096434+00:00", datetime,
                  expected=expected.astimezone())

    assert_encode("2021-03-10T12:32:49.096434+06:00", datetime,
                  expected=expected.astimezone())

    value = datetime(2021, 3, 10, 14, 32, 49, 96434)
    value_str = value.astimezone().isoformat()

    assert_encode(value, str, expected=value_str)
    assert_encode(value.astimezone(
        timezone(timedelta(seconds=14400))), str, expected=value_str)


def test_date_value():

    assert_encode(date(1999, 2, 28), date)
    assert_encode(date(2000, 1, 1), date)
    assert_encode("2000-10-01", date, expected=date(2000, 10, 1))

    value = date(2000, 1, 1)
    value_str = datetime.combine(value, dt_time(0),
                                 tzinfo=timezone.utc).astimezone().isoformat()
    assert_encode(value, str, expected=value_str)

    with pytest.raises(IncompliantError):
        assert_encode(123.45, date)


def test_simple_value():

    assert_encode(1234567)
    assert_encode(1.0 / 3)
    assert_encode(True)
    assert_encode(False)

    assert_encode(Decimal('123.45678901233445567893323'))
    assert_encode("HelloWorld")
    assert_encode(b"HelloWorld")


def test_list():
    assert_encode([1, 2, 3], List[int])

def test_dict():

    encoder = DObjectCBOREncoder()
    assert_encode({"a": 10}, Dict[str, int])
    assert_encode({20: 30}, Dict[int, int])

    @dataclass
    class A:
        n: str

    assert_encode({"a": A("b")}, Dict[str, A])


def test_dataclass():
    encoder = DObjectCBOREncoder()

    @dataclass
    class D:
        v_str: str
        v_float: float = 0.0

    assert_encode(D("Tom&Jerry"), D)
    assert_encode(D("Tom&Jerry", 12.4), D)

    @dataclass
    class E:
        e_list: List[D]
        e_dict: Dict[str, D]

    assert_encode(E([D("A"), D("B")], {"c": D("c")}), E)

def test_enum():

    class State1(Enum):
        ACTIVE: str = "Active"
        DISABLED: str = "Disabled"

    assert_encode(State1.ACTIVE, State1)


    class State2(Enum):
        ACTIVE: int = 1
        DISABLED: int = 2

    assert_encode(State2.ACTIVE, State2)


    class State3(Enum):
        ACTIVE = 1
        DISABLED = 2

    assert_encode(State3.DISABLED, State3)


    @dataclass
    class A:
        n: str
        s: State1 = State1.DISABLED

    assert_encode(A("tom", State1.ACTIVE), A)
    assert_encode(A("tom"), A)


