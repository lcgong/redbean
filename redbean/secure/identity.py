import logging
logger = logging.getLogger(__name__)

import json

import asyncio


from passlib.hash import sha256_crypt
from passlib.pwd import genword

# from ..config import etcd_endpoint, secure_key

from redbean.asyncid import AsyncID64

from aiohttp.web_exceptions import HTTPNotFound

# gen_user_sn = AsyncID64('/asyncid/user_sn', etcd_endpoint)



class SessionIdentity:
    def __init__(self, user_id, identity, client_id=None):
        self._user_id = user_id
        self._identity = identity
        self._client_id = client_id

    @property
    def user_id(self) -> int :
        """ 用户ID """
        return self._user_id
    
    @property
    def identity(self) -> str :
        """ 身份标识令牌 """
        return self._identity

    @property
    def client_id(self) -> str :
        """ 客户端标识 """
        return self._client_id


from authlib.specs.rfc7519 import jwt


from datetime import datetime, timedelta

async def create_jwt(identity: SessionIdentity, secure_key) -> str:
    assert identity and secure_key

    jwt_payload = {}
    jwt_payload['sub'] = identity.identity
    if identity.client_id:
        jwt_payload['aud'] = identity.client_id

     # seconds from the epoch, 1970-1-1 UTC
    expires = datetime.now().astimezone() + timedelta(days=10)
    jwt_payload['exp'] = int(expires.timestamp())

    token = jwt.encode({'alg': 'HS256'}, jwt_payload, secure_key)

    return token.decode('ascii')

async def decode_jwt(token, secure_key) -> SessionIdentity :
    assert token and secure_key

    profile = jwt.decode(token, secure_key)

    identity = SessionIdentity()

    return identity
