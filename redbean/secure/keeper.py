import logging
logger = logging.getLogger(__name__)

import json
from aioetcd3.client import client as etcd_client
from aioetcd3.help import range_all, range_prefix
from aioetcd3.kv import KV
from aioetcd3 import transaction
from base64 import b16encode as _b16encode

from passlib.hash import sha256_crypt
from passlib.pwd import genword

from redbean.secure.identity import SessionIdentity
from redbean.exception import AlreadyExists, NotFound, Unauthorized
from redbean.exception import Unprocessable

etcd_endpoint = "127.0.0.1:2379"



class UserIdentityKeeper:

    def __init__(self, endpoint, user_id_generator=None):
        self._client = etcd_client(endpoint)

        self._prefix_perm = '/users/perm' #perms
        self._prefix_identity = '/users/identity'

        self._user_id_generator = user_id_generator


    async def create_identity(self, 
        identity: str, 
        passwd: str, 
    ) -> SessionIdentity :
        """ 直接通过电子邮件和密码创建新用户的登录身份 """

        identity_path = f"{self._prefix_identity}/{identity}"

        profile, _ = await self._client.get(identity_path)
        if profile is not None:
            raise AlreadyExists(f"登陆身份'{identity}'已经注册")

        user_id = await self._user_id_generator.new()

        # 加密登录标识
        hashed = sha256_crypt.using(rounds=2000, salt_size=8).hash(passwd)

        profile = {
            "user_id": user_id,
            "identity": identity,
            "hashed": hashed
        }
    
        value = json.dumps(profile).encode("ascii")
        await self._client.put(identity_path, value)


        return SessionIdentity(user_id=user_id, identity=identity)

    async def check_passwd(self, 
        identity: str, 
        passwd: str
    ) -> SessionIdentity :
        """ 通过密码检查身份 """
        assert identity

        value, _ = await self._client.get(f"{self._prefix_identity}/{identity}")
        if value is None:
            logger.debug(f'Not found identity: {identity}')
            raise Unauthorized(f"无此登录身份'{identity}'")

        profile = json.loads(value.decode('utf-8'))

        user_id = profile['user_id']
        identity = profile['identity']
        hashed = profile['hashed']

        if sha256_crypt.verify(passwd, hashed):
            return SessionIdentity(user_id=user_id, identity=identity)
        else:
            raise Unauthorized(f"登录身份'{identity}'认证失败")

    async def verify_permissions(self, user_id, *permissions):
        """ 返回当前用户所匹配的首个有效权限 """

        prefix = f"{self._prefix_perm}/{user_id}/"

        perm_names = [str(p) for p in permissions]
        
        checkings = [KV.get.txn(prefix + p) for p in perm_names]
        success, responses = await self._client.txn(compare=[], success=checkings)
        if not success:
            errmsg = f"无法读取用户({user_id})的权限信息"
            raise Unprocessable(errmsg)

        for i, item  in enumerate(responses):
            if item[0] is not None:
                return permissions[0]
                
        return None

    async def grant(self, user_id, *permissions):
        " 给用户(user_id)授于权限(permission) "

        prefix = f"{self._prefix_perm}/{user_id}/"

        perm_names = [str(p) for p in permissions]        
        checkings = [
            KV.put.txn(prefix + p, b'\0', prev_kv=True) for p in perm_names
        ]
        success, response = await self._client.txn(compare=[], success=checkings)
        if not success:
            errmsg = f"无法授予用户({user_id})的权限: {{{', '.join(perm_names)}}}"
            raise Unprocessable(errmsg)

        if logger.isEnabledFor(logging.DEBUG):
            granted, ignored = set(), set()
            for i, (perm, _)  in enumerate(response):
                if perm is None:
                    granted.add(perm_names[i])
                else:
                    ignored.add(perm_names[i])
            
            logger.debug(f"授予用户({user_id})权限({', '.join(granted)}), "
                            f"忽略已授权({', '.join(ignored)})")

    async def revoke(self, user_id, *permissions):
        " 取消用户(user_id)的权限(permission) "

        prefix = f"{self._prefix_perm}/{user_id}/"

        perm_names = [str(p) for p in permissions]        
        checkings = [
            KV.delete.txn(prefix + p, b'\0', prev_kv=True) for p in perm_names
        ]
        success, response = await self._client.txn(compare=[], success=checkings)
        if not success:
            errmsg = f"无法取消用户({user_id})的权限: {{{', '.join(perm_names)}}}"
            raise Unprocessable(errmsg)
        if logger.isEnabledFor(logging.DEBUG):
            revoked, ignored = set(), set()
            for i, item  in enumerate(response):
                if item:
                    revoked.add(perm_names[i])
                else:
                    ignored.add(perm_names[i])
            
            logger.debug(f"撤销用户({user_id})权限({', '.join(revoked)}), "
                            f"忽略并无此授权({', '.join(ignored)})")


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
            user_id = await self._user_id_generator.new()

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
            raise NotFound(f'{token}')

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

