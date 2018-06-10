
import inspect
from aiohttp.web import json_response
from aiohttp.web_exceptions import HTTPException
from aiohttp.web_response import Response
from collections.abc import Mapping, Sequence, Iterable

from .json import json_dumps
from .exception import HandlerSpecError

import logging
logger = logging.getLogger(__name__)


_response_writers = []

def register_response_writer(writer_factory):
    _response_writers.append(writer_factory)


def make_response_writer(proto, method, handler):
    ret_type = inspect.signature(handler).return_annotation
    if ret_type is inspect.Signature.empty:
        raise HandlerSpecError(
            f"The return type should be annotated"
            f" '{handler.__name__}' in '{handler.__module__}' ")

    if ret_type is None: # no return type
        return Response()

    writer = None
    for writer_factory in _response_writers[::-1]:
        writer = writer_factory(proto, method, handler)
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


# def _http_str_response_factory(proto, method, handler):
#     ret_type = inspect.signature(handler).return_annotation
#     if not (issubclass(ret_type, str)):
#         return

#     def _response(request, return_value):
#         return return_value

#     return _response

# _response_writers.append(_http_str_response_factory)

# def _http_response_writer_factory(proto, method, handler):

#     ret_type = inspect.signature(handler).return_annotation
#     if not (issubclass(ret_type, Response)):
#         return

#     return lambda request, result : result

# _response_writers.append(_http_response_writer_factory)
