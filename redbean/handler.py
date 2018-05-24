import logging
import inspect
import json
import sys
import warnings

from aiohttp.web import Response
from traceback import format_tb

from aiohttp.web_exceptions import HTTPException
from aiohttp.web_exceptions import HTTPInternalServerError

from .exception import NotSupportedException
from .handler_response import make_response_writer, make_error_handler
from .handler_argument import build_argval_getters

from .secure import checkCRSFToken

def request_handler_factory(route_spec, method):
    # path_signature = route_spec.path_signature
    # path_fields = route_spec.path_fields
    proto = route_spec.proto
    handler_func = route_spec.handler_func

    func_sig = inspect.signature(handler_func)

    param_names = list(func_sig.parameters.keys())
    arg_getters  = build_argval_getters(route_spec)
    resp_writer  = make_response_writer(proto, method, handler_func)

    handle_error = make_error_handler(proto, method, handler_func)

    n_args = len(arg_getters)

    async def _arg_values(request):
        arguments, errors = {}, None
        for i in range(n_args):
            try:
                arguments[param_names[i]] = await arg_getters[i](request)
            except Exception :
                if errors is None: errors = []
                errors.append((i, *sys.exc_info()))

        return arguments, errors

    def _handle_arg_error(errors):
        logger = logging.getLogger(handler_func.__module__)

        param_names= list(func_sig.parameters)
        errmsg = f"caught an exception in calling "
        errmsg += f"'{handler_func.__name__}' in '{handler_func.__module__}' \n"

        logger.error(errmsg
            + '\n'.join([f"<{i}> {str(exc_val)}\n" + ''.join(format_tb(exc_tb))
                                for i, exc_typ, exc_val, exc_tb in errors]))


        errmsg +='\n'.join([f"<{i}> {param_names[i]}: {str(exc_val)}"
                                for i, exc_typ, exc_val, traceback in errors])

        return Response(text=errmsg, status=400, reason='Bad Request')


    if inspect.iscoroutinefunction(handler_func):
        async def _request_handler(request):

            print(request.headers)

            if not verifyCRSFToken(request):
                errmsg = 'The CSRF token is required'
                return Response(text=errmsg, status=401, reason='Bad Request')

            request._redbean_route_spec = route_spec

            arguments, errors = await _arg_values(request)
            if errors: 
                return _handle_arg_error(errors)

            try:
                return_value = await handler_func(**arguments)
            except Exception as exc:
                return handle_error(request, exc)

            return resp_writer(request, return_value)

        return _request_handler

    elif inspect.isfunction(handler_func):
        raise TypeError('only support async function')
        # async def _request_handler(request):
        #     arguments, errors = await _arg_values(request)
        #     try:
        #         return_value = handler_func(**arguments)
        #     except Exception as exc:
        #         return handle_error(request, exc)

        #     return resp_writer(request, return_value)

        # return _request_handler
    else:
        raise TypeError('only support async function')
        

    handler_expr = handler_func.__name__ + str(inspect.signature(handler_func))
    raise NotSupportedException(
        f"The handler function must be a function or coroutine: "
        f"{handler_expr} in {handler_func.__module__}")
