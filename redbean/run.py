#! /usr/bin/env python
import sys
import traceback
import asyncio

from pathlib import Path

import aiohttp
from aiohttp.web_runner import AppRunner, TCPSite

import aiohttp_devtools
from aiohttp_devtools.logs import main_logger, rs_dft_logger as rs_logger
from aiohttp_devtools.runserver.config import Config
from aiohttp_devtools.runserver.serve import check_port_open, HOST


import watchgod

from click import style as _style

class AppTask():

    def __init__(self, config: Config, loop: asyncio.AbstractEventLoop):
        self._config = config
        self._reloads = 0
        self._runner = None

        self._loop = loop
        self._task = None

        self._path = Path.cwd() # self._config.code_directory
        
        self._awatch = watchgod.awatch(self._path)


    async def start(self):
        self._task = self._loop.create_task(self._run())


    async def _run(self):
        rs_logger.info('Watching: ' + str(self._path))

        try:
           await self._start_dev_server()
        except:
            rs_logger.error('Exception in loading app: ', exc_info=True)

        async for changes in self._awatch:
            self._reloads += 1
            if any(f.endswith('.py') for _, f in changes):
                rs_logger.info(_formatChanges(self._reloads, changes) + '\n')

                try:
                    await self._stop_dev_server()
                    await self._start_dev_server()
                except:
                    rs_logger.error('Exception in restaring app: ', exc_info=True)


    async def _start_dev_server(self):
        url = f'http://{self._config.host}:{self._config.main_port}'
        if self._reloads:
            msg = f'Restarting server at {url} '
            msg += _style(f'{self._reloads!s:^5}', bg='white', fg='red', bold=True)
        else:
            msg = f'Starting server at {url} ●'
        rs_logger.info(msg)
        
        app = self._config.load_app()

        await check_port_open(self._config.main_port, self._loop)
        self._runner = AppRunner(app, access_log_format='%r %s %b')
        await self._runner.setup()
        site = TCPSite(self._runner, host=self._config.host, port=self._config.main_port, shutdown_timeout=0.1)

        await site.start()
        

    async def _stop_dev_server(self):
        rs_logger.debug('stopping server process...')
        self._runner and await self._runner.cleanup()

    async def close(self):
        await self._stop_dev_server()

        if self._task:
            async with self._awatch.lock:
                if self._task.done():
                    self._task.result()
                self._task.cancel()


def _formatChanges(reloads, changes):
    cwd = Path.cwd()
    formated_cwd = click.style(str(cwd) + '/', fg='white', dim=True)

    style = click.style

    ln = f'Found {len(changes)!s} changes, reload '
    lns = [ ln ]
    for _, f in changes:
        f = str(Path(f).relative_to(cwd))
        lns.append(' ' * 11 + formated_cwd + style(f, fg='yellow') )

    return '\n'.join(lns)

#-----------------------------------------------------------------------------
import click

_file_dir_existing = click.Path(exists=True, dir_okay=True, file_okay=True)

host_help = ('host with default of localhost. env variable AIO_HOST')
port_help = 'Port to serve app from, default 8000. env variable: AIO_PORT'
@click.command()
@click.argument('app-path', envvar='AIO_APP_PATH', type=_file_dir_existing, required=False)
@click.option('-H', '--host', default='localhost', help=host_help)
@click.option('-p', '--port', 'main_port', envvar='AIO_PORT', type=click.INT, help=port_help)
@click.option('-v', '--verbose', is_flag=True, help='Enable verbose output.')
@click.option('--prod', is_flag=True, default=False, help='Enable production mode')
def main(**config):

    is_prod = config.pop('prod')
    if not is_prod:
        run_devserver(**config)
    else:
        run_prodserver(**config)

def run_devserver(**config):

    active_config = {k: v for k, v in config.items() if v is not None}
    aiohttp_devtools.logs.setup_logging(config['verbose'])
    try:
        loop = asyncio.get_event_loop()

        config = Config(**active_config)
        config.import_app_factory()

        main_manager = AppTask(config, loop)

        try:
            loop.run_until_complete(main_manager.start())
            loop.run_forever()
        except KeyboardInterrupt:  # pragma: no branch
            pass
        finally:
            loop.run_until_complete(main_manager.close())

            rs_logger.info('shutting down server...')

            start = loop.time()
            try:
                loop.run_until_complete(main_manager._runner.cleanup())
            except (asyncio.TimeoutError, KeyboardInterrupt):
                pass
            rs_logger.debug('shutdown took %0.2fs', loop.time() - start)        

    except aiohttp_devtools.exceptions.AiohttpDevException as e:
        if config['verbose']:
            tb = click.style(traceback.format_exc().strip('\n'), fg='white', dim=True)
            main_logger.warning('AiohttpDevException traceback:\n%s', tb)
        main_logger.error('Error: %s', e)
        sys.exit(2)

def run_prodserver(**config):
    raise NotImplementedError()

if __name__ == '__main__':
    main()
