import logging
from redbean import route_base, rest_service

route_base('../')

print(456233)

@rest_service.GET('user/{user_id:int}/info')
def get_user_info(user_id: int, sortno):
    logging.warning('user335532')
    # raise ValueError(333)
    return {"user_id": user_id}


@rest_service.GET('user/{user_id:int}/suspend')
def get_user_list(user_id):
    return {"user_id": user_id}


@rest_service.PUT('user/{user_id:int}/info')
def set_user_info(user_id):
    return {"user_id": user_id}
