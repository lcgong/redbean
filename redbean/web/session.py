import time
import aiohttp

from cryptography.fernet import InvalidToken
from cryptography import fernet
from sqlblock.json import json_dumps
from aiohttp.abc import AbstractStreamWriter
from typing import Optional

from ..exception import UnauthorizedError

import logging
logger = logging.getLogger(__name__)


SESSION_COOKIE = "tgu-session"
CONTEXT_COOKIE = "tgu-context"

SESSION_FERNET = "session_fernet"
SESSION_FATORY = 'session_factory'


def setup_session(app, secret_key, session_factory):

    app[SESSION_FERNET] = fernet.Fernet(secret_key)
    app[SESSION_FATORY] = session_factory


async def get_http_session(request):

    principal = get_secure_cookie(request, SESSION_COOKIE)
    if principal is None:
        raise UnauthorizedError(f"Unauthorized user session")

    factory = request.app.get(SESSION_FATORY)
    if factory is None:
        raise RuntimeError(
            "Install user session factory "
            "in your aiohttp.web.Application")

    user_session = await factory(principal)
    if user_session is None:
        raise UnauthorizedError(f"Unauthorized user session")

    return user_session


async def get_validation_in_cookie(request):

    return get_secure_cookie(request, CONTEXT_COOKIE)


class LoginResponse(aiohttp.web.Response):
    def __init__(self, principal: Optional[str], validation=False,
                 text: str = None,
                 body: bytes = None,
                 status: int = 200,
                 reason: Optional[str] = None,
                 content_type: str = None):

        self._principal = principal
        self._validation = validation

        super().__init__(text=text, body=body,
                         status=status,
                         reason=reason,
                         content_type=content_type)

    async def prepare(
            self,
            request: 'BaseRequest'
    ) -> Optional[AbstractStreamWriter]:

        set_secure_cookie(request, self,
                          SESSION_COOKIE, self._principal,
                          httponly=True)

        if self._validation:
            set_secure_cookie(request, self,
                              CONTEXT_COOKIE, self._principal,
                              max_age=3600*24*28,
                              httponly=True)

        await super().prepare(request)


class LogoutResponse(aiohttp.web.Response):
    def __init__(self, validation=False):

        self._validation = validation
        super().__init__()

    async def prepare(
            self,
            request: 'BaseRequest'
    ) -> Optional[AbstractStreamWriter]:

        set_secure_cookie(request, self, SESSION_COOKIE, None)

        if self._validation:
            set_secure_cookie(request, self, CONTEXT_COOKIE, None)

        await super().prepare(request)


def get_secure_cookie(request, name):
    value = request.cookies.get(name)
    if value is None:
        return None

    fernet = request.app[SESSION_FERNET]
    if fernet is None:
        raise RuntimeError("fernet is required in application")

    try:
        value = fernet.decrypt(value.encode('utf-8')).decode('utf-8')
        return value
    except InvalidToken:
        logger.warning("Cannot decrypt cookie value")
        return None


def set_secure_cookie(request, response, name, value, *,
                      domain=None,
                      max_age=None,
                      path='/',
                      httponly=True):

    if value is None:
        response.del_cookie(name, domain=domain, path=path)
        return

    fernet = request.app[SESSION_FERNET]
    value = fernet.encrypt(value.encode('utf-8')).decode('utf-8')

    if max_age is not None:
        expires = time.gmtime(time.time() + max_age)
        expires = time.strftime("%a, %d-%b-%Y %T GMT", expires)
    else:
        expires = None

    response.set_cookie(name, value,
                        domain=domain, path=path,
                        max_age=max_age,
                        expires=expires,
                        httponly=httponly)
