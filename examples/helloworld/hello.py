import logging
import redbean
import redbean.web.routedef
import aiohttp.web

routes = redbean.RestServiceDef(prefix="/api")

logger = logging.getLogger("hello")


@routes.get("/hello/{sn}")
async def hello(sn: int):
    """ 问候动作

    :param sn: 序号

    """

    return {"sn": sn}

async def create_app():

    app = aiohttp.web.Application()
    app.add_routes(routes)

    redbean.log_application_routes(app)

    return app


if __name__ == '__main__':
    redbean.cli(create_app)
