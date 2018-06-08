import logging

import hashlib
from base64 import b64decode, b64encode
from aiohttp.web import Response


import aiohttp

class SecureLayer:

    def __init__(self):
        self._guarded_handlers = dict()
        self._prepare_session_handlers = set()
        self._close_session_handlers = set()
        
    async def remember(self, request, response, identity):
        pass

    async def forget(self, request, response):
        pass

    def add_prepare_session(self, handler):
        self._prepare_session_handlers.add(handler)

    def add_close_session(self, handler):
        self._close_session_handlers.add(handler)

    def add_guarded(self, handler, permissions):
        if handler not in self._guarded_handlers:
            self._guarded_handlers[handler] = list(permissions)
        else:
            self._guarded_handlers[handler] += permissions

    def decorate(self, route_spec, handler):
        target = route_spec.handler_func

        guarded = self._guarded_handlers.get(target)
        prepare_handler  = target in self._prepare_session_handlers
        close_handler = target in self._close_session_handlers

        if not (guarded or  prepare_handler or close_handler):
            return handler

        print(123, route_spec.handler_func)

        async def _secured_handler(request):
            pass

        return handler




    # async def authorized_userid(self, request):
    #     identity = await identity_policy.identify(request)
    #     if identity is None:
    #         return None  # non-registered user has None user_id
    #     user_id = await autz_policy.authorized_userid(identity)
    #     return user_id

    # async def permits(request, permission, context=None):
    #     assert isinstance(permission, (str, enum.Enum)), permission
    #     assert permission
    #     identity = await identity_policy.identify(request)
    #     # non-registered user still may has some permissions
    #     access = await autz_policy.permits(identity, permission, context)
    #     return access


class AccessCotrol:

    async def authorized_userid(self, identity):
        """Retrieve authorized user id.
        Return the user_id of the user identified by the identity
        or 'None' if no user exists related to the identity.
        """
        if identity == 'jack':
            return identity


    async def permits(self, request, permissions):
        # userid = await authorized_userid(request)
        user_id = 123
        user_id = None
        if user_id is None:
            raise aiohttp.web.HTTPUnauthorized()

        # allowed = await permits(request, permission, context)
        allowed = False
        if not allowed:
            required = ', '.join(list(str(p) for p in permissions))
            errmsg = f'Forbidden, user_id={user_id}, required: <{required}>'
            request.app.logger.warn(errmsg)
            raise aiohttp.web.HTTPForbidden



from aiohttp.web_exceptions import HTTPForbidden, HTTPUnauthorized
from authlib.specs.rfc7519 import jwt

from datetime import datetime



def checkAuthorized(request):

    token = getAuthorizationTokenFromHeader(request)
    if not token:
        token = request.cookies['authorization']
        if not token:
            raise HTTPUnauthorized('authorization token is required')

    secure_key = request.app.get('secure_key')
    assert secure_key

    payload = jwt.decode(token, key=secure_key)
    if payload.exp <= int(datetime.now().astimezone().timestamp()):
        raise HTTPUnauthorized('The authorization token has expired')

    client_id = payload.get('aud')
    if not client_id:
        raise HTTPUnauthorized('Invalid authorization token')

    if client_id.startsWith('spa|'):
        checkCRSFToken(request)

        
def getAuthorizationTokenFromHeader(request):
    value = request.headers['Authorization']

    if not value:
        return 

    prefix, token = value.split(' ', maxsplit=1)
    if not prefix.strip().upper() == 'Bearer':
        raise HTTPUnauthorized('Invalid Authorization Header')
    
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
        raise HTTPUnauthorized('Invalid X-CSRF-Token in HTTP headers')


    hashfunc = hashlib.sha1()
    hashfunc.update((hdr_salt + '-' + secure_key).encode('ascii'))
    hashed = b64encode(hashfunc.digest()).decode('ascii')
    # make the encoded hash string url safe
    hashed = hashed.replace('+', '-').replace('/', '_').replace('=', '')

    if not hashed == hdr_hashed:
        raise HTTPUnauthorized('CSRF check failed')


