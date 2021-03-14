from typing import get_origin, get_args, _GenericAlias
from dataclasses import _is_dataclass_instance, _FIELDS as _DATACLASS_FIELDS
from dataclasses import dataclass, fields, MISSING

import copy
from typing import Tuple, List
from datetime import datetime, date, time as dt_time, timezone, timedelta
from cbor2 import dumps as cbor_dumps, loads as cbor_loads

from typing import Any, Mapping
from decimal import Decimal
from .cast import cast_dataclass_object, cast_generic_object
from . import IncompliantError

class DObjectCBOREncoder:
    def __init__(self):
        # 取得系统当前时区
        self._tz = datetime.now(timezone.utc).astimezone().tzinfo

    def encode(self, dataobj) -> bytes:
        data_struct = self._as_struc(dataobj)
        return cbor_dumps(data_struct,
                          datetime_as_timestamp=True,
                          timezone=timezone.utc,
                          date_as_datetime=True
                          )

    def decode(self, dataobj, data_type):
        data_struct = cbor_loads(dataobj)
        return _as_dobj(self, data_struct, data_type)

    def _as_struc(self, obj):

        if _is_dataclass_instance(obj):
            field_tuples = []
            for field in fields(obj):
                field_key = field.name
                field_val = getattr(obj, field_key)
                field_val = self._as_struc(field_val)
                field_tuples.append((field_key, field_val))

            return dict(field_tuples)

        elif isinstance(obj, Mapping):
            return dict([
                (self._as_struc(k), self._as_struc(v))
                for k, v in obj.items()
            ])
        elif isinstance(obj, date):
            if isinstance(obj, datetime):
                if obj.tzinfo is None:
                    obj = obj.astimezone()
                
                return obj

            return datetime.combine(obj, dt_time(0), tzinfo=timezone.utc)

        elif isinstance(obj, (List, Tuple)):
            return list(self._as_struc(v) for v in obj)

        elif isinstance(obj, Enum):
            return obj.value

        elif isinstance(obj, (int, str, bool, float, bytes, Decimal)):
            return copy.deepcopy(obj)
        elif obj is None:
            return obj

        raise ValueError(f"Unsupport type '{type(obj)}'")


def _as_dobj(ctx, payload, data_type):

    if hasattr(data_type, _DATACLASS_FIELDS):
        # convert into a dataclass object
        return cast_dataclass_object(ctx, payload, data_type, _as_dobj)

    if isinstance(data_type, type):
        return cast_native_object(ctx, payload, data_type)

    if isinstance(data_type, _GenericAlias):
        return cast_generic_object(ctx, payload, data_type, _as_dobj)

    raise ValueError(f"Unsupport '{data_type}'")


from enum import Enum

def cast_native_object(ctx, payload, data_type):

    if issubclass(data_type, date):
        # note: the datetime is a subclass of date
        if issubclass(data_type, datetime):
            if isinstance(payload, datetime):
                return payload.astimezone()
            elif isinstance(payload, str):
                payload = datetime.fromisoformat(payload)
                return payload.astimezone()
        else:
            if isinstance(payload, datetime):
                return payload.astimezone(timezone.utc).date()
            elif isinstance(payload, str):
                return date.fromisoformat(payload)

    if isinstance(payload, data_type):
        return payload

    if issubclass(data_type, Enum):
        return data_type(payload)

    if issubclass(data_type, str):
        if isinstance(payload, datetime):
            return payload.astimezone().isoformat()
        else:
            return str(payload)


    if isinstance(payload, str):
        if issubclass(data_type, (int, float, Decimal)):
            return data_type(payload)
        elif issubclass(data_type, bool):
            payload = payload.lower()
            if payload == "true" or payload == "t":
                return True
            elif payload == "false" or payload == "f":
                return False

                
    raise IncompliantError(f"The payload type '{type(payload)}' "
                           f"is incomplaint with {data_type}")


