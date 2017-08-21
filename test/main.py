#! /usr/bin/env python3



import yaml
import logging.config
from pathlib import Path
with (Path(__file__).parent / 'logging.yaml').open() as config:
    logging.config.dictConfig(yaml.load(config))


import logging
log = logging.getLogger()

log.warning('dbcd3dd')

import redbean
app = redbean.Application()
app.add_module('test.case1', prefix='/app')
app.print_routes()


# gunicorn test.main:app --bind 0.0.0.0:8080 --reload --worker-class aiohttp.GunicornUVLoopWebWorker
