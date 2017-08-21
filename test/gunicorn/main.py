#! /usr/bin/env python3



import logging
log = logging.getLogger()


import redbean

app = redbean.Application()
app.add_module('test.case1', prefix='/app')
# app.print_routes()

def main():
    return app

# gunicorn test.main:app --bind 0.0.0.0:8080 --reload --worker-class aiohttp.GunicornUVLoopWebWorker
