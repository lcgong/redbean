
import functools
from typing import ForwardRef, Any
from .specs import HandlerType
from .specs import ListenerSpec, ActionSpec, SQLBlockActionSpec

Topic = ForwardRef("Topic")


class Topic:
    def __init__(self, topic: str):
        self._topic = topic
        self._listeners = []
        self._actions = []
        self._subtopics = []

    @property
    def topic_name(self):
        return self._topic

    def add_topic(self, topic: Topic):
        self._subtopics.append(topic)

    def listen(self, topic_expr: str) -> Any:

        def _decorator(handler: HandlerType):
            listener = ListenerSpec(topic_expr, handler)
            self._listeners.append(listener)

            async def _wrapped_func(*args, **kwargs):
                raise TypeError("The listener cannot be called directly")

            functools.update_wrapper(_wrapped_func, handler)
            return _wrapped_func

        return _decorator

    def action(self, action_name: str):

        def _decorator(handler):

            sqlblock_meta = getattr(handler, "__sqlblock_meta__", None)
            if sqlblock_meta is not None:
                action = SQLBlockActionSpec(action_name,
                                            sqlblock_meta._wrapped_func,
                                            sqlblock_meta._database)
            else:
                action = ActionSpec(action_name, handler)

            self._actions.append(action)
            return action.decorate()

        return _decorator
