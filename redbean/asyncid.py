import logging
import asyncio

from aioetcd3.client import client as etcd_client
from aioetcd3.help import range_all, range_prefix
from aioetcd3.kv import KV
from aioetcd3 import transaction
from base64 import b16encode as _b16encode


logger = logging.getLogger(__name__)

# import threading

class StoppedException(Exception):
    pass

# TODO 确保得到中断异常后能够正常退出

class InterruptibleSleep:
    """  允许中断的sleep """

    def __init__(self, seconds, *, result=None, loop=None):
        self._seconds = seconds

        if loop is None:
            loop = asyncio.get_event_loop()

        future = loop.create_future()

        def _set_result():
            if future.done() or future.cancelled():
                return
            
            future.set_result(result)

        loop.call_later(seconds, _set_result)
        self._future = future


    def cancel(self):
        self._future.cancel()
    
    async def wait(self):
        return await self._future

class AsyncID64:

    """ 分布式产生一个64位唯一ID。

    64bits ID: 32bits timestamp(in seconds), 12bits shards, 20bits sequence
    
    思路：每个进程可以创建一个或多个AsyncID实例，每个AsyncID实例动态租用一个“分片”，
    在其分片(shard)内，同时间戳(timestamp)下，序号(squence)保证唯一。
    
    :param prefix: 作为etcd目录的路径，例如 /asyncid/user_sn 

    """

    def __init__(self, prefix, endpoint, *, shard_ttl=14400, max_sequence=None):
        """
        """
        # import inspect
        # import traceback
        # current_frame = inspect.currentframe()
        # traceback.print_stack(f=current_frame)
        # logger.error(1)

        # print('thread-id:', threading.get_ident())

        assert prefix.startswith('/')
        assert not prefix.endswith('/')
        assert len(prefix) > 1
        self._prefix = prefix
        self._timestamp_path = self._prefix + '/timestamp'
        self._shard_path = None

        self._client = etcd_client(endpoint)
        self._shard_ttl = shard_ttl

        if max_sequence is None:
            self._max_sequence = 2**20 - 1
        else:
            assert max_sequence <= 2**20 - 1
            self._max_sequence = max_sequence

        self._timestamp = None
        self._shard_id = None
        self._seqnum = None

        self._ready_event = None
        self._is_running = False
        self._sleeping = None

        self._task = None

    async def new(self, encoding=None):

        if self._ready_event is None:
            self.start() # 自动启动服务

        seqnum = None
        while await self._ready_event.wait(): # 等待序号计数进入就绪状态
            if self._seqnum >= self._max_sequence:
                self._renew()
                continue

            with await self._lock:
                seqnum = self._seqnum
                self._seqnum += 1
            break

        int_value = (self._timestamp << 32) | (self._shard_id << 20) | seqnum
        if encoding is None:
            return int_value

        buffer = int_value.to_bytes(8, byteorder='big')
        if encoding == 'base16':
            return _b16encode(buffer).decode('ascii')


    def start(self):
        self._ready_event = asyncio.Event() # 表示后台程序是否启动完毕
        
        self._lock = asyncio.Lock()

        loop = asyncio.get_event_loop()
        self._task = loop.create_task(self._run())

    def stop(self):
        """ """
        logger.debug(f'stopping shard {self._shard_id}')
        
        if self._sleeping is not None:
            self._sleeping.cancel()
        
        self._is_running = False


    def _renew(self):
        if self._sleeping is not None:
            self._sleeping.cancel()
        self._ready_event.clear()

    async def _run(self):
        """后台任务更新时间戳和重置序号"""

        tick_gen = _task_idle_ticks(0.3*self._shard_ttl)
        self._is_running = True
        try:
            await self._lease_shard()
            while self._is_running:

                self._ready_event.clear()
                await self._renew_timestamp()
                await self._keepalive_shard()
                self._ready_event.set()


                self._sleeping = InterruptibleSleep(next(tick_gen))
                try:
                    await self._sleeping.wait()
                except asyncio.CancelledError:
                    pass
                finally:
                    self._sleeping = None

        except asyncio.CancelledError:
            pass

        except Exception:
            logger.error(f'Error in {self._shard_id} shard:', exc_info=True)

        finally:
            self._ready_event.clear()
            await self._lease.revoke() # 取消租约
            logger.debug(f'revoked the lease {self._shard_id} shard')

    async def _renew_timestamp(self):
        retries = 0
        # 重新设置序号计数的时间戳
        while True:
            # print('checking')
            local_timestamp = _make_timestamp()
            latency = await self._update_timestamp(local_timestamp)
            if latency == 0:
                # 成功更新时间戳，重新计数
                self._timestamp = local_timestamp
                self._seqnum = 0
                return True
            else:
                # 更新失败，或许其它分片刚同时更新成功，随机休息片刻再次重试
                if latency < 10: 
                    # 在30秒之内就等待一会儿再尝试，如果太长则可能存在系统时间设置问题
                    logger.debug(f'latency, sleep {latency} secs')

                    try:
                        self._sleeping = InterruptibleSleep(latency)
                        await self._sleeping.wait()
                    except asyncio.CancelledError:
                        raise
                    finally:
                        self._sleeping = None
                                            
                    # await asyncio.sleep(latency)
                    continue
                else:
                    raise ValueError(f'全局时间晚于当前时间太长({latency} secs)')

            retries += 1
        
    async def _update_timestamp(self, local_timestamp):

        timestamp_bytes = local_timestamp.to_bytes(4, byteorder='big')

        is_success, responses = await self._client.txn(compare=[
                transaction.Value(self._shard_path) < timestamp_bytes,
            ], success=[
                KV.put.txn(self._shard_path, timestamp_bytes, 
                            prev_kv=True, lease=self._lease)
            ], fail=[
                KV.get.txn(self._shard_path)
            ])
        if not is_success:
            assert responses[0][0] is not None
            remote_timestamp = int.from_bytes(responses[0][0], byteorder='big')
            latency = remote_timestamp - local_timestamp
            assert latency >= 0, f'latency: {latency}'
            if latency == 0:
                latency = 1
            
            return latency
        else:
            return 0


    async def _lease_shard(self):
        """ 申请一个新分片，从小到大[0,4095]寻找一个为占用的分片 """

        prefix = self._prefix + '/shards/'
        self._lease = await self._client.grant_lease(ttl=self._shard_ttl)

        timestamp_bytes = (0).to_bytes(4, byteorder='big')

        retries = 0
        while True:
            shard_subidx = len(prefix)
            shard_id = 0

            # 找到未使用的最小分片号
            records = await self._client.range_keys(range_prefix(prefix))
            nums = sorted(int(k[shard_subidx:].decode('utf-8')) for k, _ in records)
            for i, n in enumerate(nums):
                if n > i:
                    shard_id = i
                    break
            else:
                shard_id = len(nums)
            # print(nums, shard_id)
            logger.debug(f'leasing shard_id={shard_id}, retry={retries}')


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
                logger.debug(f'failed in leasing shard: retry {retries}')
                await _random_nap(retries)
                retries += 1

                if retries > 10:
                    raise ValueError('out of retries')

    async def _keepalive_shard(self):
        lease = await self._client.refresh_lease(self._lease)
        self._lease = lease
        logger.debug(f'keepalive: {self._shard_path} ttl={lease.ttl}')


from datetime import datetime
from time import time as time_ticks
from random import uniform as _rand_uniform

def b16encode_int64(int_value):
    return _b16encode(int_value.to_bytes(8, byteorder='big')).decode('utf-8')


async def _random_nap(retries=0):
    asyncio.sleep(_rand_uniform(0.1, 0.3))

def _make_timestamp():
    return int(datetime.utcnow().timestamp())

def _task_idle_ticks(seconds_per_cycle):
    """ 计算下次周期的沉睡时间 """ 
    t = time_ticks()
    while True:
        t += seconds_per_cycle
        yield max(t - time_ticks(), 0)


__all__ = ['AsyncID64']

# loop.run_forever()
# loop.close()
# # seqnum_user




