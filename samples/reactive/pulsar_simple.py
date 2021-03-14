import asyncio
from dataclasses import dataclass
from redbean.reactive import Topic, PulsarChannel

order_topic = Topic("MyOrder")

@dataclass
class Order:
    order_id: str
    address: str

@order_topic.listen("Commit")
async def react_commit(order: Order, message_id: str):
    print(f"A: got message '{message_id}': {order}")

@order_topic.action("Commit")
async def commit_order(sn: int) -> Order:
    order = Order(f"2021{sn:03d}", "TJ01")

    return order

async def biz_action1():
    for i in range(3):
        await commit_order(i)

async def main():
    channel = PulsarChannel(domain="Demo", url="pulsar://localhost:6650")
    channel.add_topic(order_topic)

    try:
        await channel.start()

        await asyncio.sleep(1)
        await biz_action1()

        while True:
            await asyncio.sleep(60)

    finally:
        await channel.close()

try:
    asyncio.run(main())
except KeyboardInterrupt:
    pass
