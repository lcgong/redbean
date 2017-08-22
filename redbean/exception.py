

from aiohttp.web_exceptions import HTTPForbidden, HTTPUnauthorized
from aiohttp.web_exceptions import HTTPUnprocessableEntity


class HandlerSpecError(Exception):
    pass

class NotSupportedException(Exception):
    pass


class UnprocessableState(HTTPUnprocessableEntity): # 422
    """
    the service handler understands the request but was unable to fulfill the
    request when some condition or state was not satified
    """

class Invalidation(UnprocessableState):
    def __init__(self, message):
        self.message = message
        super(Invalidation, self).__init__()
