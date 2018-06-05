import asyncio

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
