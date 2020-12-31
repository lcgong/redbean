
import toml
import sys
from typing import Mapping
from pathlib import Path
import logging
import logging.config

__all__ = ['load', 'setup']

_logger = logging.getLogger('config')
_is_production_env = False
_directory = Path('conf')


def setup(directory=None, production=None):

    global _is_production_env
    global _directory

    import os
    _python_env = os.environ.get("PYTHON_ENV")
    if _python_env:
        _is_production_env = _python_env == 'production'

    if directory is not None:
        _directory = Path(directory)

    if not _directory.is_dir():
        print(f"cannot find directory: {_directory}", file=sys.stderr)
        sys.exit(1)

def setup_logging(verbose=False):
    conf_obj = load('logging')
    if conf_obj is None:
        return
    
    if verbose:
        import json
        msg = json.dumps(conf_obj, indent=4)
        print(f"=== loggging configuration ===\n{msg}\n", )

    logging.config.dictConfig(conf_obj)

def load(name):

    conf_obj = {}
    config_file = _directory / (name + '.toml')
    if config_file.is_file():
        with open(config_file) as f:
            conf_obj = toml.load(f)

    if _is_production_env:
        config_file = _directory / (name + '.production.toml')
    else:
        config_file = _directory / (name + '.development.toml')

    if config_file.is_file():
        with open(config_file) as f:
            conf = toml.load(f)
            _dict_update_deeply(conf_obj, conf)

    # import json
    # print(json.dumps(conf_obj, indent=4))

    # 加载敏感配置参数
    config_file = _directory / 'secrets' / (name + '.toml')
    if config_file.is_file():
        with open(config_file) as f:
            conf = toml.load(f)
            _dict_update_deeply(conf_obj, conf)

    return conf_obj


def _dict_update_deeply(d, u):
    for k, v in u.items():
        if isinstance(v, Mapping):
            d[k] = _dict_update_deeply(d.get(k, {}), v)
        else:
            d[k] = v
    return d
