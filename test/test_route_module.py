
from redbean.route import Application


import logging

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger()




async def test_f(test_client):
    app = Application()
    app.add_module('test.case1', prefix='/')
    app.print_routes()

    client = await test_client(app)
    resp = await client.get('/user/124/info')
    text = await resp.text()
    assert resp.status == 200

    log.debug(text)
