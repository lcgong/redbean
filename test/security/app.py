
import logging
logger = logging.getLogger(__name__)

from redbean.logs import setup_logging
from pathlib import Path 
setup_logging(config=Path(__file__).parent / 'logging.yaml')

from .config import rest, secure_key

def create_app():

    import aiohttp
    app = aiohttp.web.Application()

    # import domainics.redbean
    # domainics.redbean.setup(app)

    rest.setup(app)
    app['secure_key'] = secure_key

    return app

# python -m redbean.run -p 8500 test/security/app.py


