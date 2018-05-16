import logging

import hashlib
from base64 import b64decode, b64encode
from aiohttp.web import Response


def verifyCRSFToken(request, force=True):

    token = request.headers['X-CSRF-Token']

    uasid = request.cookies['x-ua-sid']
    if not uasid:
        return False

    secure_key = request.app.get('secure_key')
    if not secure_key:
        raise ValueError('secure_key is required in application')

    secure_key += uasid # real key: secure_key + uasid

    try:
        hdr_salt, hdr_hashed = token.split('-', maxsplit=1)
    except ValueError:
        raise ValueError('Invalid X-CSRF-Token in HTTP headers')


    hashfunc = hashlib.sha1()
    hashfunc.update((hdr_salt + '-' + secure_key).encode('ascii'))
    hashed = b64encode(hashfunc.digest()).decode('ascii')
    # make the encoded hash string url safe
    hashed = hashed.replace('+', '-').replace('/', '_').replace('=', '')

    return hashed == hdr_hashed

