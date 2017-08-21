# -*- coding: utf-8 -*-

import json
import datetime

from decimal import Decimal


def loads(s):
	"""Deserialize s to a python object"""
	return json.loads(s)


def json_dumps(obj):
	return json.dumps(obj, cls=DefaultJSONEncoder)

class DefaultJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (datetime.date, datetime.datetime)):
            return obj.isoformat()
        elif isinstance(obj, (Decimal)) :
            return float(obj)
        elif hasattr(obj, '__json_object__'):
            return obj.__json_object__()
        else:
            return super(DefaultJSONEncoder, self).default(obj)
