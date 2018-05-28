import logging

import hashlib
from base64 import b64decode, b64encode
from aiohttp.web import Response


import aiohttp

class AccessCotrol:

    async def authorized_userid(self, identity):
        """Retrieve authorized user id.
        Return the user_id of the user identified by the identity
        or 'None' if no user exists related to the identity.
        """
        if identity == 'jack':
            return identity


    async def remember(self, request, response, identity):
        pass

    async def forget(self, request, response):
        pass

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


