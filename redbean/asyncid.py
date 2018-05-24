import logging
import asyncio

from aioetcd3.client import client as etcd_client
from aioetcd3.help import range_all, range_prefix
from aioetcd3.kv import KV
from aioetcd3 import transaction


logger = logging.getLogger(__name__)

class AsyncID:

    """ 分布式产生一个64位唯一ID。

    64bits ID: 32bits timestamp(in seconds), 12bits shards, 20bits sequence
    
    思路：每个进程可以创建一个或多个AsyncID实例，每个AsyncID实例动态租用一个“分片”，
    在其分片(shard)内，同时间戳(timestamp)下，序号(squence)保证唯一。
    
    """

    def __init__(self, endpoint, name, *, max_sequence=None):

        self._client = etcd_client(endpoint)
        self._name = name
        self._prefix = f'/genseq/{name}'
        self._shard_ttl = 1 * 10

        self._timestamp_path = self._prefix + '/timestamp'

        if max_sequence is None:
            self._max_sequence = 2**20 - 1
        else:
            assert max_sequence <= 2**20 - 1
            self._max_sequence = max_sequence

        self._timestamp = None
        self._shard_id = None
        self._seqnum = None

        self._lock = asyncio.Lock()
        self._ready_event = asyncio.Event() # 表示后台程序是否启动完毕

        self._loop = asyncio.get_event_loop()
        self._task = self._loop.create_task(self._run())


    async def new(self):
        """得到一个新序号(整型)"""
        
        if not self._ready_event.is_set():
            await self._ready_event.wait()

        timestamp, shard_id = self._timestamp, self._shard_id
        seqnum = await self._inc_seqnum()

        buf = timestamp << 32 | shard_id << 20 | seqnum

        return buf

    def close(self):
        self._loop.call_soon(self._task.cancel())

    async def _inc_seqnum(self):
        with await self._lock:
            seqnum = self._seqnum
            self._seqnum += 1

            if self._seqnum > self._max_sequence: # 序号超过范围，使用新时间戳重新计数
                await self._check_timestamp()

        return seqnum

    async def _check_timestamp(self):
        retries = 0
        while True:
            global_timestamp = await self._get_global_timestamp()
            local_timestamp = _make_timestamp()  

            if global_timestamp <= local_timestamp:
                if self._timestamp:
                    duration = local_timestamp - self._timestamp
                    if self._seqnum < self._max_sequence and duration < 86400:
                        break

                # 只要序号达到最大范围或者时间戳使用超过一天，就更新时间戳强制重新计数
                if await self._update_timestamp(local_timestamp):
                    # 成功更新时间戳，重新计数
                    self._timestamp = local_timestamp
                    self._seqnum = 0
                    break
                else:
                    # 更新失败，或许其它分片刚同时更新成功，随机休息片刻再次重试
                    await _random_nap()
                    continue
            else:
                # 本地最新时间早于全局时间记录，一般由于时间设置问题或误差
                latency = global_timestamp - local_timestamp 
                if latency < 30: 
                    # 在30秒之内就等待一会儿再尝试，如果太长则可能存在系统时间设置问题
                    await asyncio.sleep(latency + 1)
                    continue
                else:
                    raise ValueError(f'全局时间晚于当前时间太长({latency} secs)')

            retries += 1

        
    async def _get_global_timestamp(self):
        """得到所保存的全局时间戳，如果没有则新存一个"""
        value, _ = await self._client.get(self._timestamp_path)
        if value:
            return int.from_bytes(value, byteorder='big')

        timestamp = 0 # as default value
        timestamp_bytes = timestamp.to_bytes(4, byteorder='big')

        is_success, response = await self._client.txn(compare=[
                transaction.Version( self._timestamp_path) == 0 
            ], success=[
                KV.put.txn(self._timestamp_path, timestamp_bytes)
            ], fail=[
                KV.get.txn(self._timestamp_path)
            ])
        
        if is_success:
            return timestamp
        else:
            # 创建同时刚刚由其它创建成功
            value, _ = response[0]
            assert value is not None
            return int.from_bytes(value, byteorder='big')

    async def _update_timestamp(self, timestamp):

        timestamp_bytes = timestamp.to_bytes(4, byteorder='big')

        is_success, _ = await self._client.txn(compare=[
                transaction.Value(self._timestamp_path) < timestamp_bytes,
                transaction.Value(self._shard_path) < timestamp_bytes,
            ], success=[
                KV.put.txn(self._timestamp_path, timestamp_bytes),
                KV.put.txn(self._shard_path, timestamp_bytes, lease=self._lease)
            ])

        return is_success

    async def _run(self):
        """后台任务更新时间戳和重置序号"""

        try:
            await self._lease_shard()
            await self._check_timestamp()

            self._ready_event.set()
        
            tick_gen = _task_idle_ticks(0.3*self._shard_ttl)
            while True:
                await asyncio.sleep(next(tick_gen))
                await self._keepalive_shard()
                await self._check_timestamp()
        except (KeyboardInterrupt, asyncio.CancelledError):
            pass

        except Exception:
            logger.error('Caught Exception', exc_info=True)


    async def _lease_shard(self):
        """ 申请一个新分片，从小到大[0,4095]寻找一个为占用的分片 """

        prefix = self._prefix + '/shards/'
        self._lease = await self._client.grant_lease(ttl=self._shard_ttl)

        timestamp_bytes = (0).to_bytes(4, byteorder='big')


        retries = 0
        while True:
            shard_subidx = len(prefix)
            shard_id = 0

            records = await self._client.range_keys(range_prefix(prefix))
            print(records)
            for key, _ in records:
                shard_num = int(key[shard_subidx:].decode('utf-8'))

                if shard_num > shard_id:
                    break
                shard_id += 1

            assert shard_id <= 4095 # 12bits for shard id

            shard_path = prefix + f'{shard_id}'
            is_success, _ = await self._client.txn(compare=[
                    transaction.Version(shard_path) == 0 
                ], success=[
                    KV.put.txn(shard_path, timestamp_bytes, lease=self._lease)
                ])

            if is_success:
                self._shard_id = shard_id
                self._shard_path = shard_path
                self._timestamp = None
                self._seqnum = None
                break
            else:
                await _random_nap(retries)
                retries += 1

    async def _keepalive_shard(self):
        lease = await self._client.refresh_lease(self._lease)
        self._lease = lease
        logger.debug(f'keepalive: {self._shard_path} ttl={lease.ttl}')


from datetime import datetime
from time import time as time_ticks
import random


async def _random_nap(retries=0):
    asyncio.sleep(random.uniform(0.05, 0.3))

def _make_timestamp():
    return int(datetime.utcnow().timestamp())

def _task_idle_ticks(seconds_per_cycle):
    """ 计算下次周期的沉睡时间 """ 
    t = time_ticks()
    while True:
        t += seconds_per_cycle
        yield max(t - time_ticks(), 0)


__all__ = ["AsyncID"]

# loop.run_forever()
# loop.close()
# # seqnum_user




