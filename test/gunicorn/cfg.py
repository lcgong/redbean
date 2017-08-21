# import yaml
# import logging.config
# from pathlib import Path
#
# p = Path(__file__).parent / '../logging.yaml'
# print(open(p))
# with p.open() as config:
#     logging.config.dictConfig(yaml.load(config))


import multiprocessing

bind = "127.0.0.1:8080"
# workers = multiprocessing.cpu_count() * 2 + 1
workers = 1
# access_log_format = "%r"
worker_class = 'aiohttp.GunicornUVLoopWebWorker'
