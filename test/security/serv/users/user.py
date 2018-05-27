import logging
# from redbean import route_base, REST, HTTP

from test.security.app import rest

# route_base('../user/')


rest.set_path('../user')

@rest.get.post('{user_id}/hi')
@rest.get('{user_id}/hi2')
async def hi(user_id: int) -> dict:

    return {"id": 222*1000 + user_id}

# @REST.GET('{user_id}/session')
async def get_user_session(user_id: int) -> dict:
    return {"id": 100000}
