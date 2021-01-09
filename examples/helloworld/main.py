import redbean
from redbean import rest_method

routes = redbean.RouteTableDef()
import logging

logger = logging.getLogger("hello")

@routes.get("/")
@rest_method
async def helloword():
    logger.debug("hi! - debug")
    logger.info("hi! - info")
    logger.warning("hi! - warn")
    logger.error("hi! - error")
    logger.fatal("hi! - final")

    return {"message": "hello world"}


async def create_app():

    app = redbean.Application()
    app.add_routes(routes)
    app.log_routes()

    return app


if __name__ == '__main__':
    redbean.cli(create_app)
