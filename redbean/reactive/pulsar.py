import asyncio
from asyncio import futures
from typing import Tuple, Dict, Callable


import pulsar
from pulsar import Client as PulsarClient, Consumer, Producer, Message
from pulsar import ConsumerType

import inspect
from ..dobject.cbor import DObjectCBOREncoder
from .topic import ListenerSpec, ActionSpec, SQLBlockActionSpec
from .channel import AbstractChannel
from .exceptions import UnkownArgumentError


__all__ = ("PulsarChannel", "Message")


class PulsarChannel(AbstractChannel):

    __slots__ = ("_consumers", "_producers", "_client")

    def __init__(self, domain: str, url: str):
        super().__init__(domain, url)

        self._consumers: Dict[ListenerSpec, Consumer] = {}
        self._producers: Dict[ActionSpec, Producer] = {}
        self._client = None

    async def start(self):
        await super().start()

        client = pulsar.Client(self._url)
        self._client = client

        for topic_path, listener_specs in self._listeners.items():
            for listener in listener_specs:
                consumer = subscribe(client, topic_path, listener)
                self._consumers[listener] = consumer

        for topic_path, action_specs in self._actions.items():
            for action in action_specs:
                if isinstance(action, ActionSpec):
                    producer = mount_action(action, client, topic_path)
                elif isinstance(action, SQLBlockActionSpec):
                    producer = mount_sqlblock_action(
                        action, client, topic_path)
                else:
                    raise ValueError()

                self._producers[action] = producer

    async def close(self):
        await super().close()
        for _listener, consumer in self._consumers.items():
            consumer.unsubscribe()

        for _action, producer in self._producers.items():
            producer.flush()

        for _action, producer in self._producers.items():
            producer.close()

        self._client.close()


_run_coroutine = asyncio.run_coroutine_threadsafe


def subscribe(
        client: PulsarClient,
        topic_path: str,
        listener: ListenerSpec
) -> Consumer:

    loop = asyncio.get_running_loop()
    handler = listener.handler

    get_argvals = build_argvals_getter(handler)

    def _listener(consumer: Consumer, msg: Message):
        try:

            argvals = get_argvals(msg)
            future = _run_coroutine(handler(*argvals), loop)
            consumer.acknowledge(msg)
        except Exception as ex:
            print(ex)
            consumer.negative_acknowledge(msg)
        finally:
            ...

    consumer = client.subscribe(topic_path,
                                subscription_name=listener.group_id,
                                consumer_type=ConsumerType.Shared,
                                message_listener=_listener)

    return consumer

# https://github.com/apache/pulsar/blob/master/pulsar-client-cpp/python/src/enums.cc
async def send_message(producer, data):
    future = asyncio.Future()
    def _callback(result, msg_id):
        if result == SendingResult.Ok:
            future.set_result(msg_id)
        else:
            future.set_exception(SendingError(str(result)))

    producer.send_async(data, _callback)
    await future

from pulsar import Result as SendingResult
from .exceptions import SendingError

def mount_action(
    action: ActionSpec,
    client: PulsarClient,
    topic_path: str
) -> Producer:

    producer = client.create_producer(topic=topic_path,
                                      producer_name=action.group_id,
                                      schema=pulsar.schema.BytesSchema()
                                      )

    encoder = DObjectCBOREncoder()
    async def _send_message(data):
        await send_message(producer, encoder.encode(data))

    action.mount(_send_message)

    return producer


def mount_sqlblock_action(
    action: SQLBlockActionSpec,
    client: PulsarClient,
    topic_path: str
) -> Producer:

    producer = client.create_producer(topic=topic_path,
                                      producer_name=action.group_id,
                                      schema=pulsar.schema.BytesSchema()
                                      )

    encoder = DObjectCBOREncoder()
    async def _prepare_message(data):
        
        await send_message(producer, encoder.encode(data))
        # producer.send(encoder.encode(data))
        # TODO: the fake transactional message

    async def _commit_message():
        # TODO: the fake transactional message
        ...

    async def _rollback_message():
        # TODO: the fake transactional message
        ...

    action.mount(_prepare_message, _commit_message, _rollback_message)

    return producer



def build_argvals_getter(handler):
    arguments = [item for item in inspect.signature(
        handler).parameters.items()]

    getters = []
    data_arg_idxs = []
    for i, (arg_name, arg_spec) in enumerate(arguments):
        getter_factory = _getter_factories.get(arg_name)
        if getter_factory is not None:
            getters.append(getter_factory(arg_spec))
        else:
            getters.append(None)
            data_arg_idxs.append(i)

    # zero or one argument to access message data
    if len(data_arg_idxs) > 1:
        mod = handler.__module__
        func = handler.__qualname__
        data_arg_idxs = [arguments[i] for i in data_arg_idxs]
        args = ", ".join([f"'{spec}'" for name, spec in data_arg_idxs])
        errmsg = (f"Ambiguous message data arguments: "
                  f"{args} of '{func}' in '{mod}'. "
                  f"The message data argument should be unqiue "
                  f"and annotated type.")
        raise UnkownArgumentError(errmsg)

    if data_arg_idxs:
        arg_idx = data_arg_idxs[0]
        arg_name, arg_spec = arguments[arg_idx]
        getters[arg_idx] = getter_msg_data(arg_spec)

    def _argval_getter(msgobj):
        return (arg_getter(msgobj) for arg_getter in getters)

    return _argval_getter


def getter_msg_data(arg_spec):

    encoder = DObjectCBOREncoder()

    def _getter(msgobj):
        return encoder.decode(msgobj.data(), arg_spec.annotation)

    return _getter


def getter_msg_id(arg_spec):
    return lambda msg: msg.message_id()


def getter_msg_topic(arg_spec):
    return lambda msg: msg.topic_name()


def getter_msg_keys(arg_spec):
    return lambda msg: msg.partition_key()


def getter_msg_object(arg_spec):
    return lambda msgobj: msgobj


_getter_factories = {
    "message_id": getter_msg_id,
    "message_topic": getter_msg_topic,
    "message_key": getter_msg_keys,
    "message": getter_msg_object,
}

