
from yarl import URL
import aiohttp

from aiohttp.web_urldispatcher import MatchInfoError

from redbean.route import Application

class MockResquest(aiohttp.web.Request):
    def __init__(self, method, path, query=None, post=None):
        self._method = method
        self._rel_url = URL(path)

# register_module(app, 'test.case1', prefix='/app')

class MockClient:

    def __init__(self, module_name, prefix='/app'):
        pass
        self.app = Application()
        self.app.add_module('test.case1', prefix=prefix)
        self.app.print_routes()

    async def request(self, method, path, query=None, post=None, json=None):
        request = MockResquest(method, path, query, post)

        match_info = await self.app.router.resolve(request)
        if isinstance(match_info, MatchInfoError):
            if match_info.http_exception.status  == 404:
                raise ValueError(f"NotFound: '{path}'")

        request._match_info = match_info

        print(match_info, match_info.handler)

        res = await match_info.handler(request)


        return res
