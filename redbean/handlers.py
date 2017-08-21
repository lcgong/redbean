
import inspect
import json
from .argvalue_getters import build_argval_getters

from aiohttp.web import Response

import warnings

from .exception import NotSupportedException
from .response_writers import get_response_writer

def request_handler_factory(route_spec, method, path_signature, path_params):
    proto = route_spec.proto
    arg_getters = build_argval_getters(proto, method, route_spec.handler_func, path_params)
    func_sig = inspect.signature(route_spec.handler_func)


    resp_writer = get_response_writer(proto, method, func_sig)


    handler_func = route_spec.handler_func

    if inspect.iscoroutinefunction(handler_func):
        async def _handler_wrapper(request):
            arguments = [await getter(request) for getter in arg_getters]
            return resp_writer(request, await handler_func(*arguments))

        return _handler_wrapper

    elif inspect.isfunction(handler_func):
        async def _handler_wrapper(request):
            arguments = [await getter(request) for getter in arg_getters]
            return resp_writer(request, handler_func(*arguments))

        return _handler_wrapper

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
