
import yaml
import logging
import logging.config
from pathlib import Path
with (Path(__file__).parent / 'logging.yaml').open() as config:
    logging.config.dictConfig(yaml.load(config))

logger = logging.getLogger('abc')

import pytest
from redbean import Application


async def test_fddd(test_client):

    app = Application()

    print(test_client)

    app.add_module('test.case1', prefix='/')

    # app.make_handler(access_log_format="%r %s %Dmsec")

    cli = await test_client(app, server_kwargs={"access_log_format":"%r"})

    resp = await cli.get('/user/124/info')
    text = await resp.text()
    assert resp.status == 200


    logger.debug(text)
