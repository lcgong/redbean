
import logging
logger = logging.getLogger(__name__)

from redbean.logs import setup_logging 
from pathlib import Path 
setup_logging(config=Path(__file__).parent / 'logging.yaml')


import aiohttp

from .config import rest
from .config import secure_key 


def create_app():

    app = aiohttp.web.Application()

    rest.setup(app)
    rest.add_module('test.security.serv', prefix='/api')
    
    app['secure_key'] = secure_key

    return app

# python -m redbean.run -p 8500 test/security/app.py


