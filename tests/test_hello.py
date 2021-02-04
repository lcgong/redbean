from aiohttp import web
import sys

from redbean.logs import log_application_routes
from redbean.web.routedef import RestServiceDef
# from redbean.web import rest_method
services = RestServiceDef(prefix="/api")

@services.get("/hello/{sn}")
async def hello(sn: int):
    """ 问候动作

    :param sn: 序号

    """

    return {"sn":sn}


def create_app(loop):
    app = web.Application(loop=loop)
    app.add_routes(services)
    log_application_routes(app)
    return app

async def test_hello(aiohttp_client):
    client = await aiohttp_client(create_app)
    resp = await client.get('/api/hello/123')
    assert resp.status == 200
    text = await resp.text()
    print()
    print(123456, text)
    assert '{"sn": 123}' in text

