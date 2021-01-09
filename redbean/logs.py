import logging
import sys
import os

# from logging.handlers import TimedRotatingFileHandler


class HighlightStreamHandler(logging.StreamHandler):
    def setFormatter(self, fmt):
        self.formatter = fmt
        self.formatter.stream_is_tty = _isatty(self.stream)


class DefaultFormatter(logging.Formatter):
    """在console支持tty时，各日志级别按照不同颜色显示"""

    def __init__(self, fmt=None, datefmt=None, style='%'):
        super().__init__(fmt, datefmt, style)
        self.stream_is_tty = False

    def format(self, record):
        msg = super().format(record)
        if not self.stream_is_tty:
            return msg

        log_color = LOG_LEVEL_COLORS.get(record.levelno, _ANSI_COLOR_RED)
        return _format_ansi_color(msg, log_color)


def setup_log_config(verbose=False, is_production_mode=False):
    min_log_level = 'DEBUG' if verbose else 'INFO'

    formatter_class = ("logging.Formatter" if is_production_mode
                       else "redbean.logs.DefaultFormatter")

    handler_class = ("logging.StreamHandler" if is_production_mode else
                     "redbean.logs.HighlightStreamHandler")

    config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": r"%(asctime)s #%(process)s %(levelname)s [%(name)s] %(message)s",
                "datefmt": r"%Y-%m-%dT%H:%M:%S",
                "class": formatter_class,
            },
        },
        "handlers": {
            "default": {
                "level": min_log_level,
                "class": handler_class,
                "formatter": "default"
            },
        },
        "loggers": {
            "aiohttp.access": {
                "handlers": [
                    "default"
                ],
                "level": "INFO",
                "propagate": False
            },
            "aiohttp.server": {
                "handlers": [
                    "default"
                ],
                "level": "INFO",
                "propagate": False
            },
            "aiohttp.web": {
                "handlers": [
                    "default"
                ],
                "level": "INFO",
                "propagate": False
            },
            # "": {
            #     "level": "DEBUG",
            #     "handlers": [
            #         "default"
            #     ]
            # }
        },
        "root": {
            "level": "DEBUG",
            "handlers": [
                "default"
            ]
        }
    }

    # import json
    # print(json.dumps(config, indent= 4))

    logging.config.dictConfig(config)


_ANSI_COLOR_DIM = 2
_ANSI_COLOR_RED = 31
_ANSI_COLOR_GREEN = 32
_ANSI_COLOR_YELLOW = 33

LOG_LEVEL_COLORS = {
    logging.DEBUG: _ANSI_COLOR_DIM,
    logging.INFO: _ANSI_COLOR_GREEN,
    logging.WARN: _ANSI_COLOR_YELLOW,
}


def _format_ansi_color(text, color):
    return f"\x1b[{color}m{text}\x1b[0m"


def _isatty(stream=None):
    stream = stream or sys.stdout
    try:
        return stream.isatty()
    except Exception:
        return False


# class RotatingFileHandler(TimedRotatingFileHandler):
#     def __init__(self, filename,
#                  when='h', interval=1,
#                  backupCount=0, encoding=None,
#                  delay=False, utc=False, atTime=None):

#         filename = filename % dict(PORT=os.environ.get('PORT', 'PORT'))

#         super().__init__(filename=filename,
#                          when=when,
#                          interval=interval,
#                          backupCount=backupCount,
#                          encoding=encoding,
#                          delay=delay,
#                          utc=utc,
#                          atTime=atTime)
