import inspect

import arrow
from datetime import datetime, date
from decimal import Decimal

from domainics.pillar import _pillar_history, pillar_class
from domainics.util   import comma_split, filter_traceback
from domainics.domobj import dset, dobject, DObject, DSet

from domainics.domobj.pagination import DPage
from domainics.domobj.pagination import parse_query_range, parse_header_range


def build_argval_getters(proto, method, handler_func, path_param_names):

    getters = []
    for arg_name, arg_spec in inspect.signature(handler_func).parameters.items():
        is_path_param = arg_name in path_param_names
        getter = _build_argval_getter(arg_name, arg_spec, is_path_param)
        getters.append(getter)

    return getters

def _build_argval_getter(arg_name, arg_spec, is_path_param):
    ann_type = arg_spec.annotation
    argval_getter = None
    if ann_type != inspect._empty:
        for getter_factory in _handler_argval_getters:
            argval_getter = getter_factory(arg_name, ann_type, is_path_param)
            if argval_getter is not None:
                break

    if argval_getter is None:
        argval_getter = _defaul_argval_getter(arg_name, ann_type, is_path_param)

    if arg_spec.default is not inspect._empty:
        async def _getter(request):
            arg_val = await argval_getter(request)
            if arg_val is None:
                arg_val = arg_spec.default

            return arg_val
    else:
        async def _getter(request):
            try:
                print(arg_name, argval_getter)
                arg_val = await argval_getter(request)
            except TypeError as exc :
                raise TypeError(f"{exc} while reading '{arg_name}' with "
                                f"'{argval_getter.__qualname__}'")
            return arg_val

    return _getter




#----------------------------------------------------------------------------



def default_argval_getter_factory(arg_name, is_path_param):

    if is_path_param:
        async def _path_param_getter(request):
            return request.match_info.get(arg_name)
        return _path_param_getter

    async def _argvalue_func(request):
        if request.method in request.POST_METHODS:
            arg_val = request.post().get(arg_name)
            if arg_val is not None:
                return arg_val

        arg_val = request.query.get(arg_name)
        if arg_val is not None:
            return arg_val

        return None

    return _argvalue_func

def _defaul_argval_getter(arg_name, ann_type, is_path_param):

    read_argval = default_argval_getter_factory(arg_name, is_path_param)

    async def _getter_func(request):
        arg_val = await read_argval(request)
        # if arg_val is not None:
        #     arg_val = ann_type(arg_val)

        return arg_val

    return _getter_func


async def read_json_from_request(request):
    text = await request.text()
    return json.loads(text)


def _json_arg_getter(arg_name, ann_type, is_path_param):
    if arg_name not in ['json_arg', 'json_body']:
        return

    return read_json_from_request


def _dset_value_getter(arg_name, ann_type, is_path_param):
    if not issubclass(ann_type, DSet[DObject]):
        return

    item_type = ann_type.__parameters__[0]

    async def getter(request):
        json_obj = await read_json_from_request(request)
        return dset(item_type)(json_obj)

    return getter


def _dobject_value_getter(arg_name, ann_type, is_path_param):
    if not issubclass(ann_type, DObject):
        return

    async def getter(request):
        json_obj = await read_json_from_request(request)
        return ann_type(json_obj)

    return getter

def _dpage_value_getter(arg_name, ann_type, is_path_param):
    if not issubclass(ann_type, DPage):
        return

    async def getter(request, arg_val):
        arg_val = make_pagination(handler)
        # arg_val = ann_type(arg_val)
        return arg_val

    return getter


def _datetime_value_getter(arg_name, ann_type, is_path_param):
    if not issubclass(ann_type, datetime):
        return

    read_argval = default_argval_getter_factory(arg_name, is_path_param)

    async def getter(request):
        arg_val = arrow.get(read_argval(request)).datetime
        return arg_val

    return getter

def _date_value_getter(arg_name, ann_type, is_path_param):
    if not issubclass(ann_type, date):
        return

    read_argval = default_argval_getter_factory(arg_name, is_path_param)

    async def getter(request, arg_val):
        arg_val = arrow.get(arg_val).datetime.date()
        return arg_val

    return getter



_handler_argval_getters = [
    _dset_value_getter,
    _dobject_value_getter,
    _dpage_value_getter,
    _datetime_value_getter,
    _date_value_getter,
    _json_arg_getter
]
