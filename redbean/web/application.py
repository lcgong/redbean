import logging
import aiohttp.web
from aiohttp.web_urldispatcher import PlainResource, DynamicResource
from aiohttp.web_urldispatcher import StaticResource


server_log = logging.getLogger('aiohttp.server')

from .session import SESSION_FERNET, SESSION_FATORY, secret_factory

class Application(aiohttp.web.Application):

    def __init__(self, secret_key=None, **kwargs):
        super().__init__(**kwargs)
        if secret_key is not None:
            assert isinstance(secret_key, str)
            

    # from configuration import dbconn
    # from sqlblock.setup import aiohttp_setup_sqlblock
    # aiohttp_setup_sqlblock(app, dbconn)


    def setup_session(self, factory=None, secret=None):
        
        if secret is not None:
            assert isinstance(secret, str)

            from cryptography import fernet
            self[SESSION_FERNET] = fernet.Fernet(secret)

        if factory is not None:
            self[SESSION_FATORY] = factory


    def log_routes(self):

        lines = []
        for res in self.router.resources():

            if isinstance(res, (PlainResource, DynamicResource)):
                res_info = res.get_info()
                if 'formatter' in res_info:
                    lines.append(f"==> {res_info['formatter']}")
                else:
                    lines.append(f"==> {res_info['path']}")

                for route in res:
                    handler = route.handler
                    s = f'{route.method} at {handler.__module__}.{handler.__name__}'
                    lines.append(' '* 8 + ' + ' + s)

            elif isinstance(res, StaticResource):
                res_info = res.get_info()
                print(res, res_info)
                for route in res:
                    print(route)

        server_log.info("Routes:\n" + '\n'.join(lines))

