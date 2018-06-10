import logging
logger = logging.getLogger(__name__)

audit_log = logging.getLogger('redbean.audit')

import hashlib
from base64 import b64decode, b64encode

import aiohttp
from aiohttp.web import Response
from authlib.specs.rfc7519 import jwt

from redbean.exception import Unauthorized
from .identity import SessionIdentity
import time

import datetime as dt


class SecureLayer:

    def __init__(self, secure_key, max_age=None):
        self._guarded_handlers = dict()
        self._prepare_session_handlers = set()
        self._close_session_handlers = set()
        self._permission_verifier = None

        self._cookie_name = "Authorization"
        self._secure_key = secure_key

        if max_age is None:
            self._max_age = 30 * 24 * 3600
        
    async def open_session(self, request, identity):
        token = await self.encode_jwt(identity)

        resp = Response()
        resp.set_cookie(self._cookie_name, token, 
                        max_age=self._max_age, httponly=True)

        logger.debug(f"open session: {str(identity)}")

        return resp

    async def close_session(self, request, identity):

        resp = Response(text="")
        resp.del_cookie(self._cookie_name)

        logger.debug(f"close session: {str(identity)}")

        return resp

    async def identify(self, request):
        """ 从request中得到登录身份identity """
        if hasattr(request, '_session_identity'):
            return request._session_identity

        token = request.cookies.get(self._cookie_name)
        if token is None:
            token = getAuthorizationTokenFromHeader(request)
            if token is None:
                raise Unauthorized('无认证身份')

        identity = await self.decode_jwt(token)
        setattr(request, '_session_identity', identity)

        # if identity.client_id.startsWith('spa|'):
        #     checkCRSFToken(request)

        return identity


    def add_prepare_session(self, handler):
        self._prepare_session_handlers.add(handler)

    def add_close_session(self, handler):
        self._close_session_handlers.add(handler)

    def add_guarded(self, handler, permissions):
        if handler not in self._guarded_handlers:
            self._guarded_handlers[handler] = list(permissions)
        else:
            self._guarded_handlers[handler] += permissions
    
    def set_permission_verifier(self, handler):
        self._permission_verifier = handler

    async def verfiy_permissions(self, request, identity, permissions):
        effective = await self._permission_verifier(identity, permissions)

        if effective is not None:
            if audit_log.isEnabledFor(logging.INFO):
                audit_log.info(f"ACCEPT: {identity}, perm({str(effective)}) "
                                f"at '{request.path_qs}' ")
            return
        
        if audit_log.isEnabledFor(logging.INFO):
            audit_log.info(f"REJECT: {identity} at '{request.path_qs}'")

        raise Unauthorized(f"用户({identity.user_id})需要权限: "
                f"{{{', '.join([str(p) for p in permissions])}}}")


    async def encode_jwt(self, identity: SessionIdentity) -> str:
        """ 将identity编码为JWT """
    
        assert identity

        payload = {
            "sub": identity.identity,
            "user_id": identity.user_id,
            "exp": int(time.time() + self._max_age) # seconds from 1970-1-1 UTC
        }
        
        if identity.client_id:
            payload['aud'] = identity.client_id


        token = jwt.encode({'alg': 'HS256'}, payload, self._secure_key)

        return token.decode('ascii')
        
    async def decode_jwt(self, token: str) -> SessionIdentity :
        assert token

        payload = jwt.decode(token, self._secure_key)

        expires = payload.get('exp')
        if expires and expires <= int(time.time()):
            raise Unauthorized('认证Token超期')

        identity = SessionIdentity(self, 
                                    user_id = payload.get('user_id'), 
                                    identity = payload.get('sub'),
                                    client_id = payload.get('aud'))


        return identity

def getAuthorizationTokenFromHeader(request):
    value = request.headers.get('Authorization')
    if not value:
        return
    
    if not value.startsWith('Bearer '):
        raise Unauthorized("Invalid Authorization Header: 'Bearer <token>'")
    
    token = value[7:].strip()
    return token


def checkCRSFToken(request):

    token = request.headers['X-CSRF-Token']
    assert token

    uasid = request.cookies['x-ua-sid']
    if not uasid:
        return False

    secure_key = request.app.get('secure_key')
    assert secure_key

    secure_key += uasid # real key: secure_key + uasid

    try:
        hdr_salt, hdr_hashed = token.split('-', maxsplit=1)
    except ValueError:
        raise Unauthorized('Invalid X-CSRF-Token in HTTP headers')


    hashfunc = hashlib.sha1()
    hashfunc.update((hdr_salt + '-' + secure_key).encode('ascii'))
    hashed = b64encode(hashfunc.digest()).decode('ascii')
    # make the encoded hash string url safe
    hashed = hashed.replace('+', '-').replace('/', '_').replace('=', '')

    if not hashed == hdr_hashed:
        raise Unauthorized('CSRF check failed')

