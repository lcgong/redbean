
from logging.handlers import TimedRotatingFileHandler


import os

class RotatingFileHandler(TimedRotatingFileHandler):
    pass

    def __init__(self, filename,
                 when='h', interval=1,
                 backupCount=0, encoding=None,
                 delay=False, utc=False, atTime=None):

        filename = filename % dict(PORT=os.environ.get('PORT', 'PORT'))

        super().__init__(filename=filename,
                         when=when,
                         interval=interval,
                         backupCount=backupCount,
                         encoding=encoding,
                         delay=delay,
                         utc=utc,
                         atTime=atTime)
