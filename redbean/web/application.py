import logging

from aiohttp.web_urldispatcher import PlainResource, DynamicResource
from aiohttp.web_urldispatcher import StaticResource


server_log = logging.getLogger('aiohttp.server')

def log_app_routes(app):

    lines = []
    for res in app.router.resources():

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


import importlib
from pkgutil import walk_packages

def deep_load_moduels(root_names):
    for module_name in root_names:
        for _ in _iter_submodules(module_name):
            pass  
           

def _iter_submodules(module):
    """  """
    if isinstance(module, str):
        # logger.debug('dynamic loading module: ' + module)    
        module = importlib.import_module(module)
    
    if not hasattr(module, '__path__'):
        yield module
        return

    if isinstance(module.__path__, list): # no namespace package
        yield module

    prefix = module.__name__ + '.'

    for loader, module_name, ispkg in walk_packages(module.__path__, prefix):
        module = loader.find_module(module_name).load_module(module_name)
        if ispkg and not isinstance(module.__path__, list):
            continue

        yield module

