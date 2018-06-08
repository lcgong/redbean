from aioetcd3.client import client as etcd_client
from aioetcd3.help import range_all, range_prefix
from aioetcd3.kv import KV
from aioetcd3 import transaction
from base64 import b16encode as _b16encode


from .identity import SessionIdentity

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