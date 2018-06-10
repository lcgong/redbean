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
        
        if isinstance(data['error'], str):
            reason = data['error']
        else:
            reason = None
        
        if 'type' not in data:
            exc_type = type(self)
            data['type'] = f"{exc_type.__module__}.{exc_type.__qualname__}"
        
        text = json.dumps(data)
        content_type = 'application/json'
        
        super().__init__(text=text, reason=reason, content_type=content_type)


class RESTfulRequestError(RESTfulHTTPError):
    status_code = 400

class RESTfulArgumentError(RESTfulRequestError):
    
    def __init__(self, errors):
        data = {
            "error": errors
        }
        
        super().__init__(data=data)

class Unauthorized(RESTfulRequestError):
    status_code = 401

    def __init__(self, text=None):
        super().__init__(text=text)

class Forbidden(RESTfulRequestError):
    status_code = 403
    
    def __init__(self, text=None):
        super().__init__(text=text)

class NotFound(RESTfulRequestError):
    status_code = 404

    def __init__(self, text=None):
        super().__init__(text=text)

class AlreadyExists(RESTfulRequestError):
    status_code = 409 # Conflict

    def __init__(self, text=None):
        super().__init__(text=text)

class Unprocessable(RESTfulRequestError):
    status_code = 422 # UnprocessableState
    # the service handler understands the request but was unable to fulfill the
    # request when some condition or state was not satified

    def __init__(self, text):
        super().__init__(text=text)


class RESTfulServerError(RESTfulHTTPError):
    status_code = 500


class RESTfulDeclarationError(RESTfulServerError):
    pass

