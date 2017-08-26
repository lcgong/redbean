#! /usr/bin/env python3

import logging
logger = logging.getLogger(__name__)

import asyncio
import aiohttp
import os
import signal
import sys
import inspect

from pathlib import Path
from multiprocessing import set_start_method, Process
from importlib import import_module
from datetime import datetime

from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler
from watchdog.events import match_any_paths, unicode_paths

import redbean
import click

"""

Referrences:
    https://github.com/aio-libs/aiohttp-devtools
"""

from aiohttp.web import run_app as aiohttp_run_app



def run_app(app, description="redbean"):
    import argparse

    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('--host', '-H', default='localhost', help="server host address")
    parser.add_argument('--port', '-p',  type=int, default=8080, help="server port number")
    parser.add_argument('-d',  default=['./'], nargs='*', dest='work_paths', help="work directory")
    parser.add_argument('--production', action='store_true')
    args = parser.parse_args()

    if args.production:
        aiohttp_run_app(app, port=args.port, host=args.host)
    else:
        app._debug = True
        app_factory_name = None
        frame = sys._getframe(1)
        for var_name, var_val in frame.f_globals.items():
            if var_val is app:
                app_factory_name = var_name
                break
        assert app_factory_name

        work_paths = (Path(p) for p in args.work_paths)
        work_paths = [ str(p) for p in work_paths if p.exists()]

        autoreload_app(app_factory_name, port=args.port, host=args.host,
            work_paths=work_paths)


def autoreload_app(app_runinfo, work_paths=None,
    host: str='localhost', port: int=8080,
    loop: asyncio.AbstractEventLoop=None, **config_kwargs):

    # assert isinstance(app_factory_name, str)
    # app = _get_app_factory(app_factory_name)

    # find the global variabl name of the app value

    set_start_method('spawn')
    loop = loop or asyncio.get_event_loop()
    loop.run_until_complete(check_port_open(port, loop))


    #-------------------------------------------------------

    observer = Observer()
    changed_handler = FileChangedEventHandler(app_runinfo, host, port)
    for path in work_paths:
        logger.info(f"watching file changes in '{path}' ...")
        observer.schedule(changed_handler, path, recursive=True)

    observer.start()

    app = _lookup_app(app_runinfo)
    handler = app.make_handler(access_log=None, loop=loop)

    try:
        loop.run_forever()
    except KeyboardInterrupt:  # pragma: no branch
        pass
    finally:
        logger.info('shutting down server...')
        observer.stop()
        observer.join()
        loop.run_until_complete(app.shutdown())
        loop.run_until_complete(app.cleanup())
        try:
            loop.run_until_complete(handler.finish_connections(0.1))
        except asyncio.TimeoutError:
            pass
    loop.close()


async def check_port_open(port, loop, host='0.0.0.0'):
    for delay in (7, 5, 3, 1):
        try:
            server = await loop.create_server(asyncio.Protocol(), host=host, port=port)
        except OSError as e:
            if e.errno != 98:  # pragma: no cover
                raise
            logger.warning(f'port {port} is already in use, waiting {delay}sec...')
            await asyncio.sleep(delay, loop=loop)
        else:
            server.close()
            await server.wait_closed()
            return
    logger.error(f'The port {port} is already is use, and exit...')
    exit(1)



class FileChangedEventHandler(PatternMatchingEventHandler):
    # patterns = ['*.*']
    patterns = ['*.py']

    ignore_directories = True
    ignore_patterns = [
        '*/.git/*',              # git
        '*/include/python*',     # in virtualenv
        '*/lib/python*',         # in virtualenv
        '*/aiohttp_devtools/*',  # itself
        '*~',                    # linux temporary file
        '*.sw?',                 # vim temporary file
    ]
    skipped_event = False

    def __init__(self, app_runinfo, host: str, port: int, *args, **kwargs):
        self._app_runinfo = app_runinfo
        self._host = host
        self._port = port

        self._change_dt = datetime.now()
        self._since_change = None
        self._change_count = 0
        super().__init__(*args, **kwargs)

        self._start_process()

    def dispatch(self, event):
        if event.is_directory:
            return

        paths = []
        if getattr(event, 'dest_path', None) is not None:
            paths.append(unicode_paths.decode(event.dest_path))
        if event.src_path:
            paths.append(unicode_paths.decode(event.src_path))

        if not match_any_paths(paths, included_patterns=self.patterns,
                                        excluded_patterns=self.ignore_patterns):
            return

        self._since_change = (datetime.now() - self._change_dt).total_seconds()
        if self._since_change <= 1:
            self.skipped_event = True
            return

        self._change_dt = datetime.now()
        self._change_count += 1
        self.on_event(event)
        self.skipped_event = False

    def on_event(self, event):
        self._stop_process()
        self._start_process()

    def _start_process(self):
        if self._change_count == 0:
            logger.info(f'Starting http://{self._host}:{self._port} ●')
        else:
            logger.warning(f'Restarting http://{self._host}:{self._port} ●')

        self._process = Process(target=_run_app,
                        args=(self._app_runinfo,),
                        kwargs=dict(
                            host=self._host,
                            port=self._port,
                            access_log_format='%r [%s] %Dus'))

        self._process.start()

    def _stop_process(self):
        if self._process.is_alive():
            # logger.debug('stopping server process...')
            os.kill(self._process.pid, signal.SIGINT)
            self._process.join(5)
            if self._process.exitcode is None:
                logger.warning('process has not terminated, sending SIGKILL')
                os.kill(self._process.pid, signal.SIGKILL)
                self._process.join(1)
                return

            # logger.debug('process stopped')
            return

        logger.warning('server process already dead, exit code: %d', self._process.exitcode)

def _lookup_app(app_runinfo):
    app_module = import_module(app_runinfo.module_name)
    if app_runinfo.attribute_name:
        app = getattr(app_module, app_runinfo.attribute_name)
        assert app is not None
        return app

    if app_runinfo.factory_name:
        app_factory = getattr(app_module, app_runinfo.attribute_name, None)
        assert app_factory is not None
        app = app_factory()
        assert app
        return app

    raise ValueError("confused application info: " + str(app_runinfo))



def _run_app(app_runinfo, host=None, port=None,
             ssl_context=None, backlog=128, access_log_format=None):

    app = _lookup_app(app_runinfo)

    loop = asyncio.get_event_loop()
    try:
        app._set_loop(loop)
        loop.run_until_complete(app.startup())

        make_handler_kwargs = dict()
        if access_log_format is not None:
            make_handler_kwargs['access_log_format'] = access_log_format

        handler = app.make_handler(loop=loop, **make_handler_kwargs)

        server_creation = loop.create_server(handler, host, port,
                                            ssl=ssl_context, backlog=backlog)
        server = loop.run_until_complete(server_creation)

        try:
            loop.add_signal_handler(signal.SIGINT, aiohttp.web.raise_graceful_exit)
            loop.add_signal_handler(signal.SIGTERM, aiohttp.web.raise_graceful_exit)
        except NotImplementedError:
            # add_signal_handler is not implemented on Windows
            pass

        try:
            loop.run_forever()
        except (aiohttp.web.GracefulExit, KeyboardInterrupt):  # pragma: no cover
            pass
        finally:
            server.close()
            loop.run_until_complete(server.wait_closed())
            loop.run_until_complete(app.shutdown())
            loop.run_until_complete(handler.shutdown())
    finally:
        loop.run_until_complete(app.cleanup())

        loop.close()
