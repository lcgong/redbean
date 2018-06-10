import logging
logger = logging.getLogger(__name__)

from test.security.app import rest

from redbean.secure.identity import SessionIdentity

rest.set_path('../user')

@rest.get('{user_id}/hi')
@rest.guarded('a', 'b')
@rest.guarded('c')
async def hi(user_id: int) -> dict:
    return {"id": 222*1000 + user_id}

# @REST.GET('{user_id}/session')
async def get_user_session(user_id: int, identity) -> dict:
    return {"id": 100000}
