import logging
logger = logging.getLogger(__name__)

import json

import asyncio

from aioetcd3.client import client as etcd_client
from aioetcd3.help import range_all, range_prefix
from aioetcd3.kv import KV
from aioetcd3 import transaction
from base64 import b16encode as _b16encode

from passlib.hash import sha256_crypt
from passlib.pwd import genword

from ..config import etcd_endpoint, secure_key

from redbean.asyncid import AsyncID64

from aiohttp.web_exceptions import HTTPNotFound

gen_user_sn = AsyncID64('/asyncid/user_sn', etcd_endpoint)



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

class UserIdentityKeeper:

    def __init__(self, endpoint):
        self._client = etcd_client(endpoint)

    async def create_email_identity(self, 
            client_id, identity, passwd, *, 
            user_id=None # 如果设置用户ID，则创建该用户的新登录身份
        ) -> SessionIdentity :
        """ 创建使用电子邮件地址和密码登录的用户身份 """
        
        assert passwd

        value, _ = await self._client.get(f"/users/identity/{identity}")
        if value:
            raise ValueError(f' {identity} has already been registered')

        if user_id is None: # 新用户
            user_id = await gen_user_sn.new()

        # 加密登录标识
        hashed = sha256_crypt.using(rounds=2000, salt_size=8).hash(passwd)

        profile = {
            "user_id": user_id,
            "identity": identity,
            "hashed": hashed
        }

        token = genword(length=32, charset="ascii_50")
        key = f"/users/verifying/{token}"

        await self._client.put(key, json.dumps(profile))

        return SessionIdentity(user_id=user_id, identity=identity)


    async def verify_email(self, token) -> SessionIdentity:
        key = f"/users/verifying/{token}"
        value, _ = await self._client.get(key)
        if value is None:
            raise HTTPNotFound(text=f'{token}')

        profile = json.loads(value.decode('utf-8'))
        user_id = profile['user_id']
        identity = profile['identity']
        assert identity
        assert user_id

        lease = await self._client.grant_lease(ttl=86400) # 1 days
        await self._client.put(key, profile, lease=lease)            

        key = f"/users/identity/{identity}"
        await self._client.put(key, profile)

        del profile['hashed']

        return SessionIdentity(user_id=user_id, identity=identity)


    async def check_identity(self, 
        identity: str, passwd: str, client_id: str = None
    ) -> SessionIdentity :

        value, _ = await self._client.get(f"/users/identity/{identity}")
        if value is None:
            logger.debug(f'Not found identity: {identity}')
            return None

        profile = json.loads(value.decode('utf-8'))

        user_id = profile['user_id']
        identity = profile['identity']
        hashed = profile['hashed']

        if sha256_crypt.verify(passwd, hashed):
            return SessionIdentity(user_id=user_id, identity=identity)
        else:
            return None

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
