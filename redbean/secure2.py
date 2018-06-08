class SessionIdentityPolicy:

    async def identify(self, request) :
        """ 从session里得到 登录身份 """
        pass
        # return identity

    async def remember(self, request, response, identity, **kwargs):
        pass

    async def forget(self, request, response):
        pass


class Authorization:
    async def authorize(self, identity):
        """ 对身份进行认证，得到授权的身份 """
        pass
        # return identity

    async def permits(self, identity, permissions):
        """ 对身份的权限检查"""
        return True



async def login(self, request):
    response = web.HTTPFound('/')
    form = await request.post()
    login = form.get('login')
    password = form.get('password')
    db_engine = request.app.db_engine
    if await check_credentials(db_engine, login, password):
        await remember(request, response, login)
        return response

    return web.HTTPUnauthorized(
        body=b'Invalid username/password combination')


async def logout(self, request):
    response = web.Response(body=b'You have been logged out')
    await forget(request, response)
    return response
