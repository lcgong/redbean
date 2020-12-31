import inspect
import functools

from aiohttp import web

from sqlblock.json import json_dumps, json_loads
import traceback

from .session import get_http_session
from ..exception import NotFoundError, UnauthorizedError
from ..exception import BusinessRuleFailedError

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
            setters.append(
                (arg_name, _json_request_getter(arg_name, arg_spec)))
            continue

        if arg_name == 'request':
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
        except NotFoundError as exc:
            return web.json_response({
                "error": "NotFound",
                "message": str(exc)
            }, status=404, dumps=json_dumps)
        except UnauthorizedError as exc:
            return web.json_response({
                "error": "Unauthorized",
                "message": str(exc)
            }, status=401, dumps=json_dumps)
        except BusinessRuleFailedError as exc:
            return web.json_response({
                "error": "Unauthorized",
                "message": str(exc)
            }, status=409, dumps=json_dumps)            
        except Exception as exc:
            return web.json_response({
                "error": "ServerError",
                "message": f"Server {type(exc).__name__}: {str(exc)}",
                "details": traceback.format_exc(),
            }, status=500, dumps=json_dumps)

        if not isinstance(res, web.StreamResponse):
            return web.json_response(res, dumps=json_dumps)
        else:
            return res

    return functools.update_wrapper(_wrapper_func, target_func)
