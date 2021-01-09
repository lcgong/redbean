class ActionException(Exception):
    pass

class NotFoundError(ActionException):
    pass

class UnauthorizedError(ActionException):
    pass

class ForbidenError(ActionException):
    pass

class InvalidArgumentError(ActionException):
    pass

class BusinessRuleFailedError(ActionException):
    """ 业务逻辑无法满足继续执行 """
    pass
