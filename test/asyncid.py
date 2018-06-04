import asyncio
import pytest


from redbean.asyncid import AsyncID64

endpoint = "127.0.0.1:2379"


from random import uniform as rand_uniform


# @pytest.mark.asyncio
# async def test_some_asyncio_code(event_loop):
#     print(123, event_loop)

import threading
import logging
logger = logging.getLogger(__name__)

if __name__ == '__main__':

    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s %(levelname)s %(message)s')
    import signal

    from aiohttp.web_runner import GracefulExit
    
    async def func(id, seqno):
        while True:
            seqid = await seqno.new(encoding='base16')
            logger.info(f'new ID: {seqid}')
            await asyncio.sleep(rand_uniform(0.1, 0.2))


    loop = asyncio.get_event_loop()

    user_sn_gen1 = AsyncID64('/asyncid/user_sn', endpoint, 
                                shard_ttl=30, max_sequence=10)
    user_sn_gen2 = AsyncID64('/asyncid/user_sn', endpoint, 
                                shard_ttl=30, max_sequence=10)

    tasks = [
        loop.create_task(func(0, user_sn_gen1)),
        loop.create_task(func(1, user_sn_gen1)),
        loop.create_task(func(2, user_sn_gen2)),
        loop.create_task(func(3, user_sn_gen2)),
    ]

    def _raise_graceful_exit():
        print('Signal received')
        try:
            user_sn_gen1.stop()
            user_sn_gen2.stop()

            for t in tasks: t.cancel()

        except Exception:
            logger.error('graceful exit: ', exc_info=True)
                
        raise GracefulExit()

    loop.add_signal_handler(signal.SIGTERM, _raise_graceful_exit)
    loop.add_signal_handler(signal.SIGINT, _raise_graceful_exit)

    try:
        loop.run_forever()
    except GracefulExit:
        pass
    finally:
        logger.debug('Waiting for all of tasks are complete before exiting')
        loop.run_until_complete(asyncio.gather(
                                            user_sn_gen1.stopped(), 
                                            user_sn_gen2.stopped()))
        logger.debug('ASyncID stopped')

        loop.run_until_complete(asyncio.wait(asyncio.Task.all_tasks())) 
        logger.debug('DONE.')
        loop.close()