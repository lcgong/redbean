import importlib
from pkgutil import walk_packages

def load(*module_names):
    for module_name in module_names:
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

__all__ = ['load']