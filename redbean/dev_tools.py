from .config import _dict_update_deeply
from .config import load as load_config
import contextlib
import sys
import traceback
import asyncio
from pathlib import Path

from aiohttp_devtools.logs import log_config as load_adev_log_config
from aiohttp_devtools.exceptions import AiohttpDevException
from aiohttp_devtools.runserver.config import Config
from aiohttp_devtools.runserver.serve import check_port_open
from aiohttp_devtools.runserver.watch import AppTask
from aiohttp.web_runner import AppRunner, TCPSite

import logging
main_logger = logging.getLogger('adev.main')


def setup_log(verbose=False):
    adev_config = load_adev_log_config(verbose)
    util_config = load_config('logging')
    _dict_update_deeply(adev_config, util_config)

    if verbose:
        import json; 
        msg = json.dumps(adev_config, indent=4)
        print(f"LOG: loading logging configuration\n{msg}\n")

    logging.config.dictConfig(adev_config)


def run_app(app_factory_pyfile, app_factory_name, watch_path,
            port, host=None, verbose=False):

    # force a full reload in sub processes so they load an updated version of code,
    # this must be called only once
    from multiprocessing import set_start_method
    set_start_method('spawn')

    config = MyConfig(main_port=port, host=host, verbose=verbose)

    # import inspect
    # app_factory_module = inspect.getmodule(app_factory)

    config.py_file = Path(app_factory_pyfile).resolve()
    config.app_factory_name = app_factory_name
    config.watch_path = watch_path

    loop = asyncio.get_event_loop()
    loop.run_until_complete(check_port_open(config.main_port, loop))

    main_manager = NoLivereloadAppTask(config, loop)
    loop.run_until_complete(main_manager.start({'websockets': []}))

    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    except AiohttpDevException as e:
        main_logger.error('Error: %s', e)
        sys.exit(2)
    finally:
        main_logger.info('shutting down server...')
        start = loop.time()
        with contextlib.suppress(asyncio.TimeoutError, KeyboardInterrupt):
            loop.run_until_complete(main_manager.close())
        main_logger.info('shutdown took %0.2fs', loop.time() - start)


class MyConfig(Config):
    def import_app_factory(self):

        setup_log(self.verbose)  # 每次进程启动，需要覆盖logging的配置
        return super().import_app_factory()


class NoLivereloadAppTask(AppTask):
    async def _src_reload_when_live(self, checks):
        pass


if __name__ == '__main__':

    from main import create_app
    run_app(create_app, port=8100)
