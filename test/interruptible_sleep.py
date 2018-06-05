import asyncio
import pytest

from redbean.sleep import InterruptibleSleep

@pytest.mark.asyncio
async def test_interruptible_sleep(event_loop):

    sleep = InterruptibleSleep(0.05, result=100)
    assert await sleep.wait() == 100

    with pytest.raises(asyncio.CancelledError):
        sleep = InterruptibleSleep(1, result=100)
        event_loop.call_later(0.2, sleep.cancel)        
        
        await sleep.wait()


