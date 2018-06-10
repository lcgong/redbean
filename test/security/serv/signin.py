import logging
logger = logging.getLogger(__name__)

from redbean.secure.identity import SessionIdentity
from redbean.secure.keeper import UserIdentityKeeper
from redbean.asyncid import AsyncID64

from ..config import etcd_endpoint
from test.security.app import rest

user_id_generator = AsyncID64('/asyncid/user_sn', etcd_endpoint)
keeper = UserIdentityKeeper(etcd_endpoint, user_id_generator=user_id_generator)

# rest.
rest.set_path('.')

@rest.post('login')
@rest.prepare_session
async def login(json_body: dict) -> SessionIdentity:

    client_id = json_body.get('client_id')
    identity = json_body.get('identity')
    passwd = json_body.get('passwd')

    identity = await keeper.check_passwd(identity, passwd)
    identity.client_id = client_id

    return identity


@rest.post('logout')
@rest.close_session
async def logout(identity: SessionIdentity) -> None:
    logger.debug(f'signout {identity}')


@rest.post('identity/new')
@rest.prepare_session
async def create_identity(json_body: dict) -> SessionIdentity:

    login_id = json_body.get('identity')
    passwd = json_body.get('passwd')

    identity = await keeper.create_identity(login_id, passwd)

    return identity

@rest.permission_verifier
async def verify_permissions(identity: SessionIdentity, permissions):
    return await keeper.verify_permissions(identity.user_id, *permissions)

@rest.on_cleanup
async def cleanup():
    user_id_generator.stop()
    await user_id_generator.stopped()


# @rest.get('verify_email/{token}')
# @rest.prepare_session
# async def verify_email(token: str) -> SessionIdentity:
#     """ 使用邮件确认链接确认其使用本人邮件地址作为登录标识 """
#     assert token

#     identity = await keeper.verify_email(token)
#     return identity

# @rest.post('signup')
# async def signup(json_arg: dict) -> SessionIdentity:
#     client_id = json_arg.get('client_id')
#     identity = json_arg.get('login_id')
#     passwd = json_arg.get('login_id')

#     assert client_id
#     assert identity
#     assert passwd

#     await keeper.create_email_identity(client_id, identity, passwd)



