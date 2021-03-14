
import functools
from typing import Callable, Awaitable, Any

HandlerType = Callable[..., Awaitable[Any]]

class ListenerSpec:
    __slots__ = ("topic_expr", "handler", "group_id")

    def __init__(self, topic_expr: str, handler: HandlerType):
        self.topic_expr = topic_expr
        self.handler = handler
        self.group_id = f"{handler.__module__}.{handler.__qualname__}"


from .exceptions import UmountAction
async def _unmounted_action(*args):
    raise UmountAction()


class ActionSpec:
    __slots__ = (
        "action_name", "handler", "group_id",
        "_topic_path", "_send_message"
    )

    def __init__(self, action_name: str, handler: HandlerType):
        self.action_name = action_name
        self.handler = handler
        self.group_id = f"{handler.__module__}.{handler.__qualname__}"

        self._send_message = _unmounted_action

    def decorate(self):
        handler = self.handler

        async def _wrapped_executor(*args, **kwargs):
            result = await handler(*args, **kwargs)
            await self._send_message(result)
            return result

        return functools.update_wrapper(_wrapped_executor, handler)

    def mount(self, send_func):
        self._send_message = send_func


class SQLBlockActionSpec:
    __slots__ = (
        "action_name", "handler", "group_id", "_dbconn",
        "_prepare_message", "_commit_message", "_rollback_message"
    )

    def __init__(self, action_name: str, handler: HandlerType, dbconn: Any):
        group_id = f"{handler.__module__}.{handler.__qualname__}"

        self.action_name = action_name
        self.handler = handler
        self.group_id = group_id
        self._dbconn = dbconn

        self._prepare_message = _unmounted_action
        self._commit_message = _unmounted_action
        self._rollback_message = _unmounted_action

    def decorate(self):
        handler = self.handler

        async def _wrapped_action(*args, **kwargs):

            @self._dbconn.transaction
            async def _transactional_action(*args, **kwargs):

                result = await handler(*args, **kwargs)

                await self._prepare_message(result)

                return result

            result = await _transactional_action(*args, **kwargs)
            # 事务已成功提交，待确认消息也已经发送，只待确认该消息
            await self._commit_message()

            return result

        return functools.update_wrapper(_wrapped_action, handler)

    def mount(self, prepare_message, commit_message, rollback_message):
        self._prepare_message = prepare_message
        self._commit_message = commit_message
        self._rollback_message = rollback_message

