import asyncio
from dataclasses import dataclass
from redbean.reactive import Topic, PulsarChannel


from sqlblock import AsyncPostgresSQL
dbconn = AsyncPostgresSQL(dsn="postgresql://postgres@localhost/postgres")


order_topic = Topic("MyOrder")


@dataclass
class Order:
    order_id: str
    address: str

@order_topic.listen("Commit")
async def react_commit(order: Order, message_id: str):
    print(f"A: got message '{message_id}': {order}")

@order_topic.action("Commit")
@dbconn.transaction
async def commit_order(sn: int) -> Order:
    order = Order(f"2021{sn:03d}", "TJ01")
    async for r in dbconn.sql("SELECT 1 as sn"):
        print(r)
        
    return order

async def biz_action1():
    for i in range(1):
        await commit_order(i)

async def main():
    channel = PulsarChannel(domain="Demo", url="pulsar://localhost:6650")
    channel.add_topic(order_topic)

    try:
        await channel.start()

        async with dbconn:
            await biz_action1()
            await asyncio.sleep(1)

        while True:
            await asyncio.sleep(60)

    finally:
        await channel.close()

try:
    asyncio.run(main())
except KeyboardInterrupt:
    pass
