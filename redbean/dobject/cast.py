from enum import Enum
from dataclasses import is_dataclass
from typing import get_origin, get_args

from cbor2.compat import int2bytes
from . import IncompliantError

from typing import List, Dict, Union
from typing import get_origin, get_args, _GenericAlias

from dataclasses import fields, is_dataclass

from dataclasses import dataclass, fields, MISSING


def cast_generic_object(ctx, data_struct, data_type, cast_object):

    alias_origin = get_origin(data_type)
    if isinstance(alias_origin, type):
        if issubclass(alias_origin, list):  # List[Data]
            item_type = get_args(data_type)[0]
            return [
                cast_object(ctx, item, item_type) for item in data_struct
            ]

        if issubclass(alias_origin, dict):  # Map[Key, Data]
            key_type, val_type = get_args(data_type)[:2]
            return {
                cast_object(ctx, k, key_type): cast_object(ctx, v, val_type)
                for k, v in data_struct.items()
            }

    if alias_origin == Union:  # Union[A, B, None]
        return cast_union_object(ctx, data_struct, data_type, cast_object)

    raise ValueError(f"Unsupport '{data_type}'")


def cast_dataclass_object(ctx, payload, data_type, as_object):
    """将字典结构的数据转换为dataclass类型的对象"""

    if not isinstance(payload, dict):
        raise IncompliantError(f"The payload's type '{type(payload)}' "
                               f"is incomplaint with dataclass {data_type}")

    init_kwargs = {}
    for field in fields(data_type):
        if not field.init:
            # 不需要包含对象初始化里的，跳过
            continue

        field_name = field.name
        field_value = payload.get(field.name, MISSING)
        if field_value is MISSING:
            # 处理缺失值
            if field.default is not MISSING:
                field_value = field.default
            elif field.default_factory is not MISSING:
                field_value = field.default_factory()
            else:
                field_value = None
        else:
            field_value = as_object(ctx, field_value, field.type)

        init_kwargs[field_name] = field_value

    return data_type(**init_kwargs)


_DREALM_HINTS = "__drealm_hints__"


def cast_union_object(ctx, payload, union_data_cls, cast_object):
    data_cls = infer_union_arg(payload, union_data_cls)

    return cast_object(ctx, payload, data_cls)


def infer_union_arg(payload, data_cls):
    """infer the payload's type with union argument types"""

    hints = getattr(data_cls, _DREALM_HINTS, None)
    if hints is None:
        hints = build_union_hints(data_cls)
        setattr(data_cls, "__drealm_hints__", hints)

    simp_types, dobj_field_groups = hints

    if isinstance(payload, dict): # maybe a dataclass object
        for fields, owners in dobj_field_groups:
            if any(f in payload for f in fields):
                return owners[0]

    if isinstance(payload, dict):
        dict_generic_type = simp_types[1]
        if dict_generic_type is not None:
            alias_origin = get_origin(dict_generic_type)
            if issubclass(alias_origin, dict):
                return dict_generic_type

    elif isinstance(payload, (list, tuple)):
        list_generic_type = simp_types[2]
        if list_generic_type is not None:
            alias_origin = get_origin(list_generic_type)
            if issubclass(alias_origin, (list, tuple)):
                return list_generic_type
    else:
        for data_type in simp_types[0]:
            if isinstance(payload, data_type):
                return data_type

    raise IncompliantError(f"The payload's type '{type(payload)}' "
                        f"is incompliant with {data_cls}")

def build_union_hints(data_cls):
    """
    build inferrence hints

    推理规则： payload具有某类的专有属性则优先判断为该类
    """

    options = get_args(data_cls)

    simp_types = []
    dobj_fields = {}
    dobj_types = []
    list_type = None
    dict_type = None
    for i, cls in enumerate(options):
        if is_dataclass(cls):
            dobj_types.append(cls)
            for field in fields(cls):
                owner_idxs = dobj_fields.get(field.name)
                if owner_idxs is None:
                    dobj_fields[field.name] = [i]
                else:
                    owner_idxs.append(i)
        elif isinstance(cls, _GenericAlias):
            alias_origin = get_origin(cls)
            if isinstance(alias_origin, type):
                if issubclass(alias_origin, list):  # List[..]
                    if list_type is None:
                        list_type = cls
                    else: 
                        raise IncompliantError("Only allow one Dict type in Union")
                    
                if issubclass(alias_origin, dict):  # Dict[..]
                    if dict_type is None:
                        dict_type = cls
                    else: 
                        raise IncompliantError("Only allow one Dict type in Union")
        else:
            simp_types.append(cls)

    simp_types = tuple(simp_types)

    if dobj_types:
        owner_fields = {}
        for field_name, owner_idxs in dobj_fields.items():
            owner_idxs = tuple(owner_idxs)
            names = owner_fields.get(owner_idxs)
            if names is None:
                owner_fields[owner_idxs] = [field_name]
            else:
                names.append(field_name)

        # [(fields, owners)] 按照所属类的个数越少、出现顺序越往前排序
        groups = sorted(
            [[tuple(f), i] for i, f in owner_fields.items()],
            key=lambda x: (len(x[1]), x[1])
        )

        groups = tuple(
            (fields, tuple(options[i] for i in owners))
            for fields, owners in groups
        )
    else:
        groups = ()

    return (simp_types, dict_type, list_type), groups
