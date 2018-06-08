import json
import inspect

from aiohttp.web_exceptions import HTTPBadRequest
from aiohttp.web_exceptions import HTTPForbidden, HTTPUnauthorized
from aiohttp.web_exceptions import HTTPUnprocessableEntity

from aiohttp.web_exceptions import HTTPInternalServerError

from aiohttp.web_exceptions import HTTPError




class HandlerSpecError(Exception):
    pass

class NotSupportedException(Exception):
    pass

class RESTfulHTTPError(HTTPError):

    def __init__(self, *, text=None, data=None):

        if data is None:
            if text is not None:
                data = {"error": text}
            else:
                raise ValueError()
        
        text = json.dumps(data)
        
        super().__init__(text=text, content_type='application/json')


class RESTfulRequestError(RESTfulHTTPError):
    status_code = 400
    # def __init__(self, data):
    #     super().__init__(data=data)


class RESTfulArgumentError(RESTfulRequestError):
    
    def __init__(self, errors):
        # func_sig = inspect.signature(handler_func)

        # param_names= list(func_sig.parameters)

        # errmsg = f"Error in calling "
        # errmsg += f"'{handler_func.__name__}' in '{handler_func.__module__}' \n"
        # errmsg +='\n'.join([f"<{i}> {param_names[i]}: {str(exc_val)}"
        #                         for i, exc_typ, exc_val, traceback in errors])

        # if hasattr(self, 'message'):
        #     errmsg = exc_val.message
        # else:
        #     errmsg = str(exc_val)
                
        data = {
            "type": 'RESTfulArgumentError',
            "error": errors
        }
        
        super().__init__(data=data)


class UnprocessableState(HTTPUnprocessableEntity): # 422
    """
    the service handler understands the request but was unable to fulfill the
    request when some condition or state was not satified
    """

class Invalidation(UnprocessableState):
    def __init__(self, message):
        self.message = message
        super(Invalidation, self).__init__()


class RESTfulServerError(RESTfulHTTPError):
    status_code = 500


class RESTfulDeclarationError(RESTfulServerError):
    pass

