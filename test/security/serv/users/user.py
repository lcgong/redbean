import logging
logger = logging.getLogger(__name__)

from test.security.app import rest

from redbean.secure.identity import SessionIdentity

rest.set_path('../user')

@rest.get.post('{user_id}/hi')
@rest.get('{user_id}/hi2')
@rest.guarded('a', 'b')
@rest.guarded('c')
async def hi(user_id: int, identity: SessionIdentity) -> dict:
    logger.info('hi') 
    logger.debug(f'3333:  {identity}')

    return {"id": 222*1000 + user_id}

# @REST.GET('{user_id}/session')
async def get_user_session(user_id: int, identity) -> dict:
    return {"id": 100000}
