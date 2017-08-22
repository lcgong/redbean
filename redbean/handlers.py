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

def request_handler_factory(route_spec, method, path_signature, path_params):
    proto = route_spec.proto
    func_sig = inspect.signature(route_spec.handler_func)
    handler_func = route_spec.handler_func

    arg_getters  = build_argval_getters(proto, method, handler_func, path_params)
    resp_writer  = make_response_writer(proto, method, handler_func)

    handle_error = make_error_handler(proto, method, handler_func)

    n_args = len(arg_getters)

    async def _arg_values(request):
        arguments, errors = [], None
        for i in range(n_args):
            try:
                arguments.append(await arg_getters[i](request))
            except Exception as exc:
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
            arguments, errors = await _arg_values(request)
            if errors: return _handle_arg_error(errors)

            try:
                return_value = await handler_func(*arguments)
            except Exception as exc:
                return handle_error(request, exc)

            return resp_writer(request, return_value)

        return _request_handler

    elif inspect.isfunction(handler_func):
        async def _request_handler(request):
            arguments, errors = await _arg_values(request)
            try:
                return_value = handler_func(*arguments)
            except Exception as exc:
                return handle_error(request, exc)

            return resp_writer(request, return_value)

        return _request_handler

    handler_expr = handler_func.__name__ + str(inspect.signature(handler_func))
    raise NotSupportedException(
        f"The handler function must be a function or coroutine: "
        f"{handler_expr} in {handler_func.__module__}")

    # async def _handler(request):
    #     arguments = [await getter(request) for getter in arg_getters]
    #     result = handler_func(*arguments)


        # def exit_callback(exc_type, exc_val, tb):
        #     self._handler_args = None
        #
        # busilogic_layer = BusinessLogicLayer(service_name, self.principal_id)
        #
        # bound_func = _pillar_history.bound(handler_func,
        #                                    [(_request_handler_pillar, self),
        #                                     (_busilogic_pillar, busilogic_layer)],
        #                                      exit_callback)


        # bound_func = handler_func
        # result = bound_func(*arguments)

        # use type hinting
        # ret_type = func_sig.return_annotation
        # if result is not None and ret_type != inspect._empty:
        #
        #     if issubclass(ret_type, DSet[DObject]):
        #         if isinstance(result, DSetBase):
        #             return result
        #         else:
        #             item_type = ret_type.__parameters__[0]
        #             result = dset(item_type)([result])
        #             return result
        #
        #     elif issubclass(result.__class__, ret_type) :
        #         return result
        #     else:
        #         return ret_type(result)
        #
        # return Response(text='hi' + json.dumps(result))
        # return result

    # return _handler



def service_func_handler(proto, service_func, service_name, path_sig) :

    def rest_handler(self, *args, **kwargs):
        obj = http_handler(self, *args, **kwargs)

        if not isinstance(obj, (list, tuple, DSetBase)):
            obj = [obj] if obj is not None else []

        if isinstance(obj, DSetBase) and hasattr(obj, '_page'):
            content_range = obj._page.format_content_range()
            self.set_header('Content-Range', content_range)
            if obj._page.start != 0 or obj._page.limit is not None:
                self.set_status(206)

        self.set_header('Content-Type', 'application/json; charset=UTF-8')
        self.write(_json.dumps(obj))

    if proto == 'REST':
        return rest_handler
    elif proto == 'HTTP':
        return http_handler
    else:
        raise ValueError('Unknown')
