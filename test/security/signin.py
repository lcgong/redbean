import logging
from redbean import route_base, REST, HTTP
from domainics.domobj import dset, datt, dobject, DObject, DSet

from datetime import datetime, timedelta, timezone

from authlib.specs.rfc7519 import jwt

# from domainics import P, transaction, sqltext

from sqlblock import SQL
from sqlblock.asyncpg import transaction

route_base('./')

@REST.POST('signin')
async def signin(json_arg: dict) -> DObject:
    print('req: ', json_arg)

    client_id = json_arg.get('client_id')
    login_id = json_arg.get('login_id')
    passwd = json_arg.get('login_id')



    jwt_payload = {}
    jwt_payload['sub'] = login_id

    client_id = json_arg.get('client_id')
    if client_id:
        jwt_payload['aud'] = client_id

     # seconds from the epoch, 1970-1-1 UTC
    expires = datetime.now().astimezone() + timedelta(days=10)
    jwt_payload['exp'] = int(expires.timestamp())

    secure_key = 'secure_key'
    token = jwt.encode({'alg': 'HS256'}, jwt_payload, secure_key).decode('ascii')

    print(jwt.decode(token, secure_key))

    return {"expires": expires.isoformat(), "token": token}
