

from collections.abc import Mapping, Sequence, Iterable
from inspect import Signature

from aiohttp.web import json_response
from aiohttp.web_exceptions import HTTPException
from aiohttp.web_response import Response

from .json import json_dumps

_response_writers = []

def get_response_writer(proto, method, handler_signature):

    writer = None
    for writer_factory in _response_writers[::-1]:
        writer = writer_factory(proto, method, handler_signature)
        if writer is not None:
            break

    if writer is not None:
        return writer

    return _default_response_writer


def _default_response_writer(request, return_value):
    if isinstance(return_value, Response): # include HTTPException
        return return_value

    elif isinstance(return_value, (Mapping, Sequence)):
        return json_response(return_value, dumps=json_dumps)

    else:
        return Response(text=str(return_value))

def _listmap_result_writer_factory(proto, method, handler_signature):
    ret_type = handler_signature.return_annotation

    if ret_type is Signature.empty:
        return

    if not (issubclass(ret_type, Mapping) or issubclass(ret_type, Sequence)):
        return

    return lambda request, result : json_response(result, dumps=json_dumps)

_response_writers.append(_listmap_result_writer_factory)

def _str_result_writer_factory(proto, method, handler_signature):
    ret_type = handler_signature.return_annotation

    if ret_type is Signature.empty:
        return

    if not (issubclass(ret_type, str)):
        return

    return lambda request, result : result

_response_writers.append(_str_result_writer_factory)


def _response_writer_factory(proto, method, handler_signature):
    ret_type = handler_signature.return_annotation

    if ret_type is Signature.empty:
        return

    if not (issubclass(ret_type, Response)):
        return

    return lambda request, result : result

_response_writers.append(_response_writer_factory)


def _dobject_result_writer_factory(proto, method, handler_signature):
    ret_type = handler_signature.return_annotation

    if ret_type is Signature.empty:
        return

    if not (issubclass(ret_type, DSet[DObject]) or issubclass(ret_type, DObject)):
        return

    async def _resp_writer(result):
        return json_response(result, dumps=json_dumps)

    return lambda request, result : json_response(result, dumps=json_dumps)

_response_writers.append(_dobject_result_writer_factory)
