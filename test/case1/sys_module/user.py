import logging
from redbean import route_base, REST, HTTP
from domainics.domobj import dset, datt, dobject, DObject, DSet

logger = logging.getLogger(__name__)

route_base('../user/')

from redbean import Invalidation

class User(dobject):
    user_id = datt(int)

@REST.GET('{user_id}/info')
async def get_user_info(user_id: int, sortno) -> DObject:
    # raise Invalidation(f"用户{user_id}没有满足条件")
    u = User(user_id=user_id)
    return u

@HTTP.GET('{user_id:int}/txt')
async def pageview_user_info(user_id: int, sortno) -> str:
    raise Invalidation(f"用户{user_id}没有满足条件")
    u = User(user_id=user_id)
    return u


# @rest_service.GET('{user_id:int}/suspend')
# def get_user_list(user_id) -> DSet:
#     return {"user_id": user_id}
#
# @rest_service.PUT('{user_id:int}/info')
# def set_user_info(user_id) -> None:
#     pass
