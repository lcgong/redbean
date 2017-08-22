#! /usr/bin/env python3

import yaml
import logging.config
from pathlib import Path
with Path('test/logging.yaml').open() as config:
    logging.config.dictConfig(yaml.load(config))


import redbean
import domainics.redbean

from redbean.run_app import run_app, autoreload_app

app = redbean.Application()
app.add_module('test.case1', prefix='/app')


work_path = str(Path(__file__).parent.resolve())

if __name__=='__main__':

    run_app(app)

    # autoreload_app(mainapp, work_path)


# if __name__=='__main__':
#     import argparse
#
#     parser = argparse.ArgumentParser(description="aiohttp server example")
#     parser.add_argument('--path')
#     parser.add_argument('--port')
#     args = parser.parse_args()
#
#     # access_log_format=None
#     access_log_format="%r [%s] %Dus"
#
#     from aiohttp.web import run_app
#     run_app(app, path=args.path, port=args.port, access_log_format=access_log_format)
