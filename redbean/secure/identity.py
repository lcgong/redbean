import logging
logger = logging.getLogger(__name__)

import json

import asyncio


class SessionIdentity:
    def __init__(self, secure_layer = None, 
        user_id = None, 
        identity: str = None, 
        client_id: str = None):
        
        self._secure_layer = secure_layer

        self._user_id = user_id
        self._identity = identity
        self._client_id = client_id

    @property
    def user_id(self) -> int :
        """ 用户ID """
        return self._user_id
    
    @property
    def identity(self) -> str :
        """ 身份标识令牌 """
        return self._identity

    @property
    def client_id(self) -> str :
        """ 客户端标识 """
        return self._client_id

    @client_id.setter
    def client_id(self, value: str):
        """ 客户端标识 """
        self._client_id = value

    def requires(self, *permissions):
        pass
    
    def __str__(self):
        return (f"SessionIdentity(user_id={self._user_id}, "
                 f"identity='{self._identity}')")


