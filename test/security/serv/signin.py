import logging
logger = logging.getLogger(__name__)

from datetime import datetime, timedelta, timezone


from ..config import rest, etcd_endpoint
from .identity import SessionIdentity, UserIdentityKeeper

identity_keeper = UserIdentityKeeper(etcd_endpoint)

# rest.
rest.set_path('.')

@rest.post('signin')
@rest.session_enter
async def signin(json_arg: dict) -> SessionIdentity:

    client_id = json_arg.get('client_id')
    login_id = json_arg.get('login_id')
    passwd = json_arg.get('login_id')

    return await identity_keeper.check_identity(client_id, login_id, passwd)


@rest.get('verify_email/{token}')
@rest.session_enter
async def verify_email(token: str) -> SessionIdentity:
    """ 使用邮件确认链接确认其使用本人邮件地址作为登录标识 """
    assert token

    identity = await identity_keeper.verify_email(token)
    return identity


@rest.post('signup')
async def signup(json_arg: dict) -> SessionIdentity:
    client_id = json_arg.get('client_id')
    identity = json_arg.get('login_id')
    passwd = json_arg.get('login_id')

    assert client_id
    assert identity
    assert passwd

    await identity_keeper.create_email_identity(client_id, identity, passwd)

@rest.post('signout')
@rest.session_exit
async def signout() -> None:
    # print('req: ', json_arg)
    pass



