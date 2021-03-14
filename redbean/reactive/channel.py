
from typing import Dict, List
from abc import abstractmethod
from .topic import Topic, ListenerSpec, ActionSpec


class AbstractChannel:
    __slots__ = ("_domain", "_url", "_topics", "_actions", "_listeners")

    def __init__(self, domain: str, url: str) -> None:
        self._domain = domain
        self._url = url
        self._topics: List[Topic] = []
        self._actions: Dict[str, List[ActionSpec]] = {}
        self._listeners: Dict[str, List[ListenerSpec]] = {}

    def add_topic(self, topic: Topic):
        self._topics.append(topic)

    @abstractmethod
    async def start(self):
        traverse_topics(self._domain, self._actions, self._listeners, self._topics)

    @abstractmethod
    async def close(self):
        pass



def traverse_topics(
    topic_root: str,
    actions: Dict[str, List[ActionSpec]],
    listeners: Dict[str, List[ListenerSpec]],
    topics: List[Topic]
):

    for topic in topics:
        topic_path = f"{topic_root}.{topic.topic_name}"

        for listener in topic._listeners:
            listener_path = f"{topic_path}.{listener.topic_expr}"
            if listener_path not in listeners:
                listeners[listener_path] = [listener]
            else:
                listeners[listener_path].append(listener)

        for action in topic._actions:
            action_path = f"{topic_path}.{action.action_name}"
            if action_path not in actions:
                actions[action_path] = [action]
            else:
                actions[action_path].append(action)

        if topic._subtopics:
            traverse_topics(topic_path, actions, listeners, topic._subtopics)
