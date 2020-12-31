from ..exception import BusinessRuleFailedError
from ..exception import NotFoundError, UnauthorizedError, ForbidenError
from .session import get_http_session
import traceback
from sqlblock.utils import json_dumps, json_loads
import logging
import inspect
import functools
from os import stat
from aiohttp import web

redbean_logger = logging.getLogger("redbean")


def cast_value(arg_spec, raw_value):
    if arg_spec.annotation == str and raw_value is not None:
        return raw_value
    elif arg_spec.annotation == int and raw_value is not None:
        return int(raw_value)
    else:
        # if arg_spec.annotation != arg_spec._empty():
        #     arg_values[arg_name] = arg_spec.annotation(arg_val)
        # else:
        return raw_value


def _default_arg_getter(arg_name, arg_spec):

    async def _getter(request):
        if arg_name in request.match_info:
            arg_val = request.match_info.get(arg_name, None)
        elif arg_name in request.query:
            arg_val = request.query.get(arg_name, None)
        else:
            return None

        return cast_value(arg_spec, arg_val)

    return _getter


def _json_request_getter(arg_name, arg_spec):
    async def _getter(request):
        json_text = await request.text()
        if len(json_text) > 0:
            return json_loads(json_text)

    return _getter


def build_argument_getters(arguments):
    setters = []
    for arg_name, arg_spec in arguments.items():
        if arg_name == 'user_session' or arg_name == 'session':
            async def _setter(request):
                return await get_http_session(request)

            setters.append((arg_name, _setter))
            continue

        if arg_name == 'json_request':
            arg_value = _json_request_getter(arg_name, arg_spec)
            setters.append((arg_name, arg_value))
            continue

        if arg_name == 'http_request' or arg_name == 'request':
            async def _setter(request):
                return request

            setters.append((arg_name, _setter))
            continue

        setters.append((arg_name, _default_arg_getter(arg_name, arg_spec)))

    return setters


def rest_method(target_func):
    """

    @rest
    def hi(session, ...):
        pass

    """
    func_sig = inspect.signature(target_func)
    arg_getters = build_argument_getters(func_sig.parameters)

    async def _wrapper_func(request):
        try:
            arg_values = dict([(arg_name, await arg_getter(request))
                               for arg_name, arg_getter in arg_getters])
            res = await target_func(**arg_values)
            if isinstance(res, web.StreamResponse):
                return res

            return web.json_response(res, dumps=json_dumps)

        except Exception as exc:
            return make_json_error_response(exc)

    return functools.update_wrapper(_wrapper_func, target_func)


def make_json_error_response(exc):
    error_message = str(exc)
    if isinstance(exc, NotFoundError):
        status = 404
        error_type = "NotFound"

    elif isinstance(exc, UnauthorizedError):
        status = 401
        error_type = "Unauthorized"

    elif isinstance(exc, ForbidenError):
        status = 403
        error_type = "ForbidenError"

    elif isinstance(exc, BusinessRuleFailedError):
        status = 409
        error_type = ""

    else:
        status = 500
        error_type = "ServerError"
        error_message = f"Server {type(exc).__name__}: {error_message}"

    details = traceback.format_exc()

    log_message = f"{error_type} ({status}): {error_message}\n{details}\n"
    if status >= 400 and status < 500:
        redbean_logger.warning(log_message)
    elif status >= 500:
        redbean_logger.error(log_message)

    return web.json_response({
        "status": status,
        "error": error_type,
        "message": error_message,
        "details": details,
    }, status=status, dumps=json_dumps)
