
import logging

from pathlib import Path 
from redbean.logs import setup_logging
setup_logging(config=Path(__file__).parent / 'logging.yaml')

logger = logging.getLogger(__name__)

import redbean
# routes = redbean.RouteModules('test.security.serv', prefix='/api')

rest = redbean.RESTfulModules({'test.security.serv': '/api'})


# from aiohttp import web
def security_middleware():

    @aiohttp.web.middleware
    async def factory(request, handler):
        # request[STORAGE_KEY] = storage
        # raise_response = False

        logger.info(request)

        try:
            response = await handler(request)
        except aiohttp.web.HTTPException as exc:
            response = exc
            # raise_response = True

        # if not isinstance(response, web.StreamResponse):
        #     raise RuntimeError(
        #         "Expect response, not {!r}".format(type(response)))
        # if not isinstance(response, web.Response):
        #     # likely got websoket or streaming
        #     return response
        # if response.prepared:
        #     raise RuntimeError(
        #         "Cannot save session data into prepared response")
        # session = request.get(SESSION_KEY)
        # if session is not None:
        #     if session._changed:
        #         await storage.save_session(request, response, session)
        # if raise_response:
        #     raise response

        return response

    return factory


def create_app():

    import aiohttp
    app = aiohttp.web.Application()

    # import domainics.redbean
    # domainics.redbean.setup(app)

    rest.setup(app)

    # app.middlewares.append(security_middleware())
    app['secure_key'] = 'DjwennlKciQiTlxKmYtWqH8N'


    # logger.debug('test')

    return app

# python -m domainics.run -p 8500 test/security/app.py


