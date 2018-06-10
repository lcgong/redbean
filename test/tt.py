

import logging
logger = logging.getLogger(__name__)

import json
import aiohttp
import asyncio
from yarl import URL

home_url = URL("http://localhost:8500/api")


async def create_identity():
    cookie_jar = aiohttp.CookieJar(unsafe=True)

    async with aiohttp.ClientSession(cookie_jar=cookie_jar) as session:
        data = {
            "identity":"xyz3@qq.com", 
            "passwd":"123"
        }
        
        data = json.dumps(data).encode("ascii")
        url = home_url / 'identity/new'
        async with session.post(url, data=data) as resp:
            print('Cookies: ', list(cookie_jar))
            if resp.status >= 400:
                error = json.loads(await resp.text())
                print(resp.status, error)
            else:
                print(resp.status, await resp.text())


async def check_password():
    cookie_jar = aiohttp.CookieJar(unsafe=True)

    async with aiohttp.ClientSession(cookie_jar=cookie_jar) as session:
        data = {
            "identity":"xyz2@qq.com", 
            "passwd":"123"
        }
        
        data = json.dumps(data).encode("ascii")
        url = home_url / 'login'
        async with session.post(url, data=data) as resp:
            print('Cookies: ', list(cookie_jar))
            if resp.status == 200:
                print('OK')
            elif resp.status >= 400:
                error = json.loads(await resp.text())
                print(resp.status, error)
            else:
                print(resp.status, await resp.text())


        url = home_url / 'user/123/hi'
        async with session.get(url) as resp:
            print('Cookies: ', list(cookie_jar))
            if resp.status >= 400:
                body = await resp.text()
                print(333, body)
                error = json.loads(body)
                print(resp.status, error)
            else:
                print(resp.status, await resp.text())

        url = home_url / 'logout'
        async with session.post(url) as resp:
            print('Cookies: ', list(cookie_jar))
            if resp.status == 200:
                print('OK: ' + await resp.text())            
            elif resp.status >= 400:
                body = await resp.text()
                print(333, body)
                error = json.loads(body)
                print(resp.status, error)
            else:
                print(resp.status, await resp.text())


async def grant():
    from redbean.secure.keeper import UserIdentityKeeper
    user_keeper = UserIdentityKeeper("127.0.0.1:2379")

    await user_keeper.grant(6564769465106432000, 'a', 'D1', 'D2')
    await user_keeper.revoke(6564769465106432000, 'D1', 'D3')

# from redbean.secure.identity import SessionIdentity

# s = SessionIdentity(1,2)
# s.client_id = 123

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s %(levelname)s %(message)s')

    

    loop = asyncio.get_event_loop()
    
    loop.run_until_complete(grant())

    loop.run_until_complete(check_password())
