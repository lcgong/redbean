import logging.config

import os
import yaml
from pathlib import Path


def setup_logging(
    config='logging.yaml',
    default_level=logging.INFO,
    env_key='LOG_CFG'
):
    """Setup logging configuration
    """
    path = config
    value = os.getenv(env_key, None)
    if value:
        path = value

    if path.exists():
        with open(path, 'rt') as f:
            config = yaml.safe_load(f.read())
        logging.config.dictConfig(config)
    else:
        print('cannot read: ' + str(path))
        logging.basicConfig(level=default_level)
